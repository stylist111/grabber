"""Grabber native host (Windows and macOS).

    grabber_host --install      download yt-dlp/ffmpeg/deno, register for browsers
    grabber_host --uninstall    unregister
    grabber_host --pickdir DIR  folder dialog (used internally on Windows)
    (no flags)                  native messaging host, started by the browser
"""
import base64
import hashlib
import json
import os
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import zipfile

NAME = 'com.grabber.host'
WIN = sys.platform == 'win32'
MAC = sys.platform == 'darwin'
EXE = '.exe' if WIN else ''
FROZEN = getattr(sys, 'frozen', False)
# Frozen: Grabber/app/grabber_host[.exe]. Source: Grabber/src/host.py. Either way ROOT = Grabber/.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable if FROZEN else __file__)))
BIN = os.path.join(ROOT, 'bin')
APP = os.path.join(ROOT, 'app')
DEFAULT_DIR = os.path.join(ROOT, 'downloads')
LOG = os.path.join(ROOT, 'host.log')
UPDATE_EVERY = 3 * 3600
NOWIN = subprocess.CREATE_NO_WINDOW if WIN else 0
# POSIX: every yt-dlp run gets its own process group, so "cancel" also stops the ffmpeg it started.
GROUP = {} if WIN else {'start_new_session': True}
BROWSERS = [
    r'Software\Google\Chrome',
    r'Software\Microsoft\Edge',
    r'Software\BraveSoftware\Brave-Browser',
    r'Software\Yandex\YandexBrowser',
    r'Software\Chromium',
]
# macOS: per-user manifest folders under ~/Library/Application Support (Chrome's docs + each browser's own).
MAC_BROWSERS = [
    'Google/Chrome',
    'Microsoft Edge',
    'BraveSoftware/Brave-Browser',
    'Yandex/YandexBrowser',
    'Chromium',
    'Vivaldi',
    'Arc/User Data',
]


def mac_arch():
    # Ask the hardware, not this process: under Rosetta platform.machine() would say x86_64.
    r = subprocess.run(['sysctl', '-n', 'hw.optional.arm64'], capture_output=True, text=True)
    return 'arm64' if r.stdout.strip() == '1' else 'x64'


if WIN:
    URLS = {
        'yt-dlp': 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe',
        'ffmpeg': ['https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip'],
        'deno': 'https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip',
    }
elif MAC:
    _a = mac_arch()
    _ff = 'https://ffmpeg.martin-riedl.de/redirect/latest/macos/{}/release/'.format('arm64' if _a == 'arm64' else 'amd64')
    URLS = {
        # The folder build (universal), not the one-file yt-dlp_macos: that one unpacks its Python into
        # a temp folder on every run, the unpacked files inherit Chrome's quarantine flag, and macOS
        # refuses to load them ("Python.framework is damaged").
        'yt-dlp': 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos.zip',
        'ffmpeg': [_ff + 'ffmpeg.zip', _ff + 'ffprobe.zip'],
        'deno': 'https://github.com/denoland/deno/releases/latest/download/deno-{}-apple-darwin.zip'.format(
            'aarch64' if _a == 'arm64' else 'x86_64'),
    }


def self_cmd(*args):
    return [sys.executable, *args] if FROZEN else [sys.executable, os.path.abspath(__file__), *args]


def search_path():
    p = BIN + os.pathsep + os.environ.get('PATH', '')
    if MAC:  # a browser started from the Dock gets a bare PATH without Homebrew
        p += os.pathsep + '/opt/homebrew/bin' + os.pathsep + '/usr/local/bin'
    return p


YTDLP_DIR = os.path.join(BIN, 'yt-dlp_macos')  # macOS: yt-dlp's folder build lives here


def tool(name):
    if MAC and name == 'yt-dlp':
        p = os.path.join(YTDLP_DIR, 'yt-dlp_macos')
    else:
        p = os.path.join(BIN, name + EXE)
    return p if os.path.isfile(p) else shutil.which(name, path=search_path())


def has_quarantine(path):
    r = subprocess.run(['xattr', '-lr', path], capture_output=True, text=True)
    return 'com.apple.quarantine' in r.stdout


def mac_install_ytdlp(label='yt-dlp'):
    """Download yt-dlp's folder build and swap it in. Also how it updates on macOS: `yt-dlp -U`
    doesn't support the folder build, and anything a process started by Chrome writes gets
    Chrome's quarantine flag — so the fresh copy is unflagged before anything runs it."""
    new, old = YTDLP_DIR + '.new', YTDLP_DIR + '.old'
    shutil.rmtree(new, ignore_errors=True)
    z = os.path.join(BIN, 'yt-dlp_macos.zip')
    fetch(URLS['yt-dlp'], z, label)
    try:
        subprocess.run(['ditto', '-x', '-k', z, new], check=True, capture_output=True)  # keeps exec bits
    finally:
        os.remove(z)
    subprocess.run(['xattr', '-dr', 'com.apple.quarantine', new], capture_output=True)
    if has_quarantine(new):  # never run it flagged: macOS would show the "damaged" dialog
        shutil.rmtree(new, ignore_errors=True)
        raise RuntimeError('не удалось снять карантин с новой версии yt-dlp')
    r = subprocess.run([os.path.join(new, 'yt-dlp_macos'), '--version'], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=120)
    if r.returncode or not r.stdout.strip():
        shutil.rmtree(new, ignore_errors=True)
        raise RuntimeError('новая версия yt-dlp не запускается: ' + (r.stderr or '').strip()[-300:])
    shutil.rmtree(old, ignore_errors=True)
    if os.path.isdir(YTDLP_DIR):
        os.rename(YTDLP_DIR, old)  # a running yt-dlp keeps working from the renamed folder
    os.rename(new, YTDLP_DIR)
    shutil.rmtree(old, ignore_errors=True)
    return r.stdout.strip()


def mac_latest_ytdlp():
    # The "latest" page redirects to .../releases/tag/<version>. curl: the system trust store.
    r = subprocess.run(['curl', '-fsSLI', '-o', '/dev/null', '-w', '%{url_effective}', '-A', 'Grabber',
                        'https://github.com/yt-dlp/yt-dlp/releases/latest'],
                       capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    tag = r.stdout.strip().rsplit('/', 1)[-1]
    return tag if r.returncode == 0 and tag[:1].isdigit() else None


# --------------------------------------------------------------------------- install

def ext_id():
    with open(os.path.join(ROOT, 'extension', 'manifest.json'), encoding='utf-8') as f:
        key = json.load(f)['key']
    h = hashlib.sha256(base64.b64decode(key)).hexdigest()[:32]
    return ''.join(chr(ord('a') + int(c, 16)) for c in h)


def fetch_once(url, dest, label):
    if MAC:
        # macOS: let the system curl do it. A python.org-built Python (inside the frozen helper)
        # has no CA certificates of its own, while curl uses the system trust store.
        # Progress bar only in the Terminal; when the browser runs us (update) stay quiet.
        quiet = '--progress-bar' if sys.stdout.isatty() else '-sS'
        subprocess.run(['curl', '-fL', '--retry', '3', '--connect-timeout', '30', quiet,
                        '-A', 'Grabber', '-o', dest + '.tmp', url], check=True, stdin=subprocess.DEVNULL)
    else:
        req = urllib.request.Request(url, headers={'User-Agent': 'Grabber'})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest + '.tmp', 'wb') as f:
            total = int(r.headers.get('Content-Length') or 0)
            got = 0
            while chunk := r.read(1 << 20):
                f.write(chunk)
                got += len(chunk)
                if total:
                    print(f'\r  {label}: {got * 100 // total}%  ({got >> 20} / {total >> 20} МБ)', end='', flush=True)
        print()
    os.replace(dest + '.tmp', dest)


def fetch(url, dest, label):
    print(f'  Скачиваю {label}…', flush=True)
    for attempt in range(3):
        try:
            return fetch_once(url, dest, label)
        except Exception as e:
            if attempt == 2:
                raise
            print(f'  Не получилось ({e}), пробую ещё раз…', flush=True)
            time.sleep(3)


def make_runnable(p):
    """macOS: zip and urllib drop the exec bit; Apple Silicon also refuses unsigned binaries,
    so anything without a valid signature gets a local (ad-hoc) one."""
    if not MAC:
        return
    os.chmod(p, 0o755)
    if subprocess.run(['codesign', '-v', p], capture_output=True).returncode != 0:
        subprocess.run(['codesign', '--force', '-s', '-', p], capture_output=True)


def unzip_exes(zpath, names):
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            base = os.path.basename(info.filename)
            if base in names:
                with z.open(info) as src, open(os.path.join(BIN, base), 'wb') as dst:
                    shutil.copyfileobj(src, dst)
                make_runnable(os.path.join(BIN, base))
    os.remove(zpath)


def host_exe():
    if FROZEN:
        return sys.executable
    # Dev run from source: a small launcher, because a manifest can't pass arguments.
    os.makedirs(APP, exist_ok=True)
    if WIN:
        exe = os.path.join(APP, 'grabber_host.bat')
        with open(exe, 'w', encoding='ascii') as f:
            f.write(f'@echo off\r\n"{sys.executable}" -u "{os.path.abspath(__file__)}" %*\r\n')
    else:
        exe = os.path.join(APP, 'grabber_host.sh')
        with open(exe, 'w', encoding='utf-8') as f:
            f.write(f'#!/bin/sh\nexec "{sys.executable}" -u "{os.path.abspath(__file__)}" "$@"\n')
        os.chmod(exe, 0o755)
    return exe


def mac_manifest_dirs():
    """(browser folder, its NativeMessagingHosts folder). Chrome always; the rest only if installed,
    so we don't leave empty folders of browsers the user doesn't have."""
    sup = os.path.expanduser('~/Library/Application Support')
    for b in MAC_BROWSERS:
        base = os.path.join(sup, b)
        if b == 'Google/Chrome' or os.path.isdir(base):
            yield base, os.path.join(base, 'NativeMessagingHosts')


def install():
    os.makedirs(BIN, exist_ok=True)
    os.makedirs(DEFAULT_DIR, exist_ok=True)
    print('1/3 Компоненты')
    if MAC:
        stale = os.path.join(BIN, 'yt-dlp')  # the one-file build from the first test versions
        if os.path.isfile(stale):
            os.remove(stale)
    ytdlp = tool('yt-dlp') if MAC else os.path.join(BIN, 'yt-dlp' + EXE)
    if not (ytdlp and ytdlp.startswith(BIN) and os.path.isfile(ytdlp)):
        if MAC:
            mac_install_ytdlp()
        else:
            fetch(URLS['yt-dlp'], ytdlp, 'yt-dlp')
        # Just downloaded the latest release: the first browser start doesn't need to check again.
        with open(os.path.join(BIN, '.last_update'), 'w') as f:
            f.write(time.ctime())
    else:
        print('  yt-dlp уже есть, оставляю (обновится сам)')
    if not (tool('ffmpeg') and tool('ffprobe')):
        for url in URLS['ffmpeg']:
            z = os.path.join(BIN, 'ffmpeg.zip')
            fetch(url, z, 'ffmpeg (~150 МБ)' if WIN else os.path.basename(url)[:-4])
            unzip_exes(z, {'ffmpeg' + EXE, 'ffprobe' + EXE})
    else:
        print('  ffmpeg найден:', tool('ffmpeg'))
    # Our own Deno, even if the PC has Node: yt-dlp needs Deno 2.3+ or Node 22+, and an old Node
    # someone installed years ago would silently break YouTube.
    if not os.path.isfile(os.path.join(BIN, 'deno' + EXE)):
        z = os.path.join(BIN, 'deno.zip')
        fetch(URLS['deno'], z, 'deno (нужен для YouTube)')
        unzip_exes(z, {'deno' + EXE})
    else:
        print('  deno уже есть')

    print('2/3 Регистрация в браузерах')
    exe = host_exe()
    manifest = {'name': NAME, 'description': 'Grabber host', 'path': exe, 'type': 'stdio',
                'allowed_origins': [f'chrome-extension://{ext_id()}/']}
    if WIN:
        import winreg
        path = os.path.join(APP, NAME + '.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        for b in BROWSERS:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf'{b}\NativeMessagingHosts\{NAME}') as k:
                winreg.SetValueEx(k, '', 0, winreg.REG_SZ, path)
    else:
        for base, d in mac_manifest_dirs():
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, NAME + '.json'), 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            print('  ', os.path.relpath(base, os.path.expanduser('~/Library/Application Support')))

    print('3/3 Проверка yt-dlp')
    out = subprocess.run([tool('yt-dlp'), '--version'], capture_output=True, text=True).stdout.strip()
    if not out:
        raise RuntimeError('yt-dlp не запускается')
    print('  yt-dlp', out)
    ext_dir = os.path.join(ROOT, 'extension')
    copy_to_clipboard(ext_dir)
    print(f'\nГотово. Путь к расширению скопирован в буфер обмена:\n  {ext_dir}')


def copy_to_clipboard(text):
    try:
        if MAC:
            subprocess.run(['pbcopy'], input=text.encode('utf-8'), capture_output=True, timeout=30)
            return
        # Windows refuses clipboard writes from a process without a window, so let PowerShell do it.
        # The text goes through an env var: no quoting issues with odd user names.
        subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                        'Set-Clipboard -Value $env:GRABBER_CLIP'],
                       env=dict(os.environ, GRABBER_CLIP=text), creationflags=NOWIN,
                       stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
    except Exception:
        pass  # the path is printed anyway


def uninstall():
    # Only unregister if the browser points at THIS copy: removing a second, older
    # install must not disconnect the one the user actually runs.
    if WIN:
        import winreg
        ours = os.path.normcase(os.path.join(APP, NAME + '.json'))
        for b in BROWSERS:
            key = rf'{b}\NativeMessagingHosts\{NAME}'
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
                    target = winreg.QueryValueEx(k, '')[0]
                if os.path.normcase(target) == ours:
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
            except FileNotFoundError:
                pass
    else:
        for _, d in mac_manifest_dirs():
            m = os.path.join(d, NAME + '.json')
            try:
                with open(m, encoding='utf-8') as f:
                    target = json.load(f).get('path', '')
                if os.path.dirname(target) == APP:
                    os.remove(m)
            except (OSError, ValueError):
                pass
    print('Grabber отключён от браузеров. Папку можно удалить.')


def pickdir_mac(initial):
    """Native folder picker via AppleScript. Text goes in as arguments, never into the script."""
    if not os.path.isdir(initial):
        initial = DEFAULT_DIR
        os.makedirs(initial, exist_ok=True)
    script = '''on run argv
    activate
    try
        set f to choose folder with prompt (item 1 of argv) default location (POSIX file (item 2 of argv))
        return POSIX path of f
    on error
        return ""
    end try
end run'''
    r = subprocess.run(['osascript', '-e', script, 'Куда сохранять загрузки', initial],
                       capture_output=True, stdin=subprocess.DEVNULL)
    p = r.stdout.decode('utf-8').strip()
    return os.path.normpath(p) if p else None


def pickdir(initial):
    import tkinter
    from tkinter import filedialog
    root = tkinter.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    p = filedialog.askdirectory(parent=root, initialdir=initial or DEFAULT_DIR,
                                title='Куда сохранять загрузки', mustexist=False)
    root.destroy()
    sys.stdout.buffer.write(os.path.normpath(p).encode('utf-8') if p else b'')


# --------------------------------------------------------------------------- host

_lock = threading.Lock()
_procs = {}            # job id -> Popen
_cancelled = set()
_update_state = {'status': 'idle', 'version': None}


def log(*a):
    print(time.strftime('%m-%d %H:%M:%S'), *a, flush=True)


def send(msg):
    data = json.dumps(msg, ensure_ascii=False).encode('utf-8')
    with _lock:
        try:
            _out.write(struct.pack('<I', len(data)) + data)
        except OSError:  # browser went away
            os._exit(0)


def read():
    raw = _in.read(4)
    if len(raw) < 4:
        return None
    n = struct.unpack('<I', raw)[0]
    buf = b''
    while len(buf) < n:
        chunk = _in.read(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return json.loads(buf.decode('utf-8'))


def env():
    e = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    e['PATH'] = search_path()
    return e


def ytdlp_version():
    try:
        return subprocess.run([tool('yt-dlp'), '--version'], capture_output=True, text=True,
                              env=env(), creationflags=NOWIN, timeout=30).stdout.strip()
    except Exception:
        return None


_update_lock = threading.Lock()


def do_update(force=False):
    """Pull the latest yt-dlp release from GitHub (throttled unless forced)."""
    stamp = os.path.join(BIN, '.last_update')
    with _update_lock:
        exe = tool('yt-dlp')
        due = force or not os.path.isfile(stamp) or time.time() - os.path.getmtime(stamp) > UPDATE_EVERY
        ours = (exe and exe.startswith(BIN)) or (MAC and not exe)  # Mac: also (re)installs a missing one
        if ours and due:
            _update_state['status'] = 'updating'
            send({'type': 'update', **_update_state})
            try:
                if MAC:
                    current, latest = (exe and ytdlp_version()), mac_latest_ytdlp()
                    if not latest:
                        raise RuntimeError('GitHub не ответил')
                    if latest != current:
                        mac_install_ytdlp()
                    log('update:', current, '->', latest)
                    _update_state['status'] = 'ok'
                else:
                    r = subprocess.run([exe, '-U'], capture_output=True, text=True, env=env(),
                                       creationflags=NOWIN, timeout=180, stdin=subprocess.DEVNULL)
                    log('update:', (r.stdout + r.stderr).strip().replace('\n', ' | '))
                    _update_state['status'] = 'ok' if r.returncode == 0 else 'failed'
                with open(stamp, 'w') as f:
                    f.write(time.ctime())
            except Exception as e:
                log('update failed', e)
                _update_state['status'] = 'failed'
        elif _update_state['status'] in ('idle', 'updating'):
            _update_state['status'] = 'ok'
        _update_state['version'] = ytdlp_version()
        send({'type': 'update', **_update_state})


def update_loop():
    while True:
        do_update()
        time.sleep(UPDATE_EVERY + 60)


def common_args():
    # --encoding: on Windows yt-dlp otherwise writes its messages in the console's code page
    # ("you’re" came out as "you�re" in error texts).
    a = ['--no-playlist', '--no-warnings', '--encoding', 'utf-8', '--remote-components', 'ejs:github']
    deno, node = tool('deno'), shutil.which('node', path=search_path())
    if deno:
        a += ['--js-runtimes', f'deno:{deno}']
    elif node:
        a += ['--js-runtimes', f'node:{node}']
    ff = tool('ffmpeg')
    if ff:
        a += ['--ffmpeg-location', os.path.dirname(ff)]
    return a


def clean_err(text):
    lines = [l for l in text.strip().splitlines() if l.startswith('ERROR')] or text.strip().splitlines()[-1:]
    return (lines[-1] if lines else 'Unknown error').replace('ERROR: ', '')


def page_url(msg):
    """Only plain web addresses reach yt-dlp, and always after '--', so a crafted
    'URL' can never be read as a yt-dlp option (--exec etc.)."""
    url = str(msg.get('url') or '').strip()
    if not url.lower().startswith(('http://', 'https://')) or any(c in url for c in '\r\n'):
        raise RuntimeError('Unsupported URL: ' + url[:200])
    return url


def do_info(msg):
    r = subprocess.run([tool('yt-dlp'), '-J', *common_args(), '--', page_url(msg)], capture_output=True,
                       env=env(), creationflags=NOWIN, stdin=subprocess.DEVNULL, timeout=120)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(clean_err(r.stderr.decode('utf-8', 'replace')))
    info = json.loads(r.stdout.decode('utf-8'))
    if info.get('_type') == 'playlist' and info.get('entries'):
        info = next(e for e in info['entries'] if e)
    fmts = info.get('formats') or [info]
    # Resolution = smaller side, like yt-dlp's -S res (vertical 1080x1920 counts as 1080p).
    heights = sorted({min(f['height'], f.get('width') or f['height']) for f in fmts
                      if f.get('height') and f.get('vcodec') not in (None, 'none')}, reverse=True)
    has_video = bool(heights) or any(f.get('vcodec') not in (None, 'none') for f in fmts)
    return {
        'title': info.get('title'),
        'uploader': info.get('uploader') or info.get('channel'),
        'thumbnail': info.get('thumbnail'),
        'duration': info.get('duration'),
        'site': info.get('extractor_key'),
        'domain': info.get('webpage_url_domain'),
        'pageUrl': info.get('webpage_url'),
        'heights': heights,
        'hasVideo': has_video,
        'hasAudio': any(f.get('acodec') not in (None, 'none') for f in fmts) or not has_video,
    }


def num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def do_download(msg):
    jid = msg['id']
    out_dir = msg.get('dir') or DEFAULT_DIR
    os.makedirs(out_dir, exist_ok=True)

    # Downloads keep yt-dlp's warnings: they only go to host.log, and they explain things like
    # a cover that didn't get embedded.
    args = [tool('yt-dlp'), *[a for a in common_args() if a != '--no-warnings'],
            '--newline', '--progress', '--windows-filenames',
            '-o', os.path.join(out_dir, '%(title).150B [%(id)s].%(ext)s'),
            '--progress-template', 'download:GRABDL %(progress.downloaded_bytes)s %(progress.total_bytes)s '
                                   '%(progress.total_bytes_estimate)s %(progress.speed)s %(progress.eta)s',
            '--progress-template', 'postprocess:GRABPP %(progress.postprocessor)s',
            '--print', 'after_move:GRABFILE %(filepath)s']
    if msg['mode'] == 'audio':
        codec = msg.get('audio', 'mp3')
        args += ['-f', 'ba/b', '-x', '--audio-format', codec,
                 '--audio-quality', '320K' if codec == 'mp3' else '0']
        if msg.get('meta', True) and codec != 'wav':
            args += ['--embed-metadata', '--embed-thumbnail']
    else:
        h = msg.get('height')
        sort = f'res:{h}' if h else 'res'
        if msg.get('h264', True):
            args += ['-S', sort + ',vcodec:h264,acodec:aac', '--merge-output-format', 'mp4']
        else:
            args += ['-S', sort, '--merge-output-format', 'mp4/mkv']
        args += ['-f', 'bv*+ba/b']
    args += ['--', page_url(msg)]

    started = time.time() - 1
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         env=env(), creationflags=NOWIN, **GROUP)
    _procs[jid] = p
    path, tail, last = None, [], 0.0
    for raw in p.stdout:
        line = raw.decode('utf-8', 'replace').strip()
        if line.startswith('GRABDL '):
            now = time.time()
            if now - last < 0.4:
                continue
            last = now
            done, total, est, speed, eta = (num(x) for x in line.split()[1:6])
            total = total or est
            send({'type': 'progress', 'id': jid, 'stage': 'downloading',
                  'percent': done * 100 / total if done and total else None, 'speed': speed, 'eta': eta})
        elif line.startswith('GRABPP '):
            send({'type': 'progress', 'id': jid, 'stage': 'processing'})
        elif line.startswith('GRABFILE '):
            path = line[9:]
        elif line:
            tail = (tail + [line])[-20:]
            log(jid, line)
    p.wait()
    _procs.pop(jid, None)
    if jid in _cancelled:
        # Drop this job's partial files. Windows keeps them locked for a moment after the kill.
        for _ in range(20):
            left = 0
            for f in os.listdir(out_dir):
                fp = os.path.join(out_dir, f)
                try:
                    if ('.part' in f or f.endswith('.ytdl')) and os.path.getmtime(fp) >= started:
                        left += 1
                        os.remove(fp)
                        left -= 1
                except OSError:
                    pass
            if not left:
                break
            time.sleep(0.5)
        raise RuntimeError('Отменено')
    if p.returncode != 0:
        raise RuntimeError(clean_err('\n'.join(tail)))
    size = os.path.getsize(path) if path and os.path.isfile(path) else None
    return {'file': path, 'dir': out_dir, 'size': size}


def run_job(msg):
    jid = msg.get('id')
    try:
        if msg['type'] == 'info':
            send({'type': 'info', 'id': jid, 'ok': True, **do_info(msg)})
        elif msg['type'] == 'download':
            send({'type': 'done', 'id': jid, **do_download(msg)})
        elif msg['type'] == 'pickdir':
            initial = msg.get('initial') or DEFAULT_DIR
            if MAC:
                path = pickdir_mac(initial)
            else:
                r = subprocess.run(self_cmd('--pickdir', initial),
                                   capture_output=True, creationflags=NOWIN, stdin=subprocess.DEVNULL)
                path = r.stdout.decode('utf-8').strip() or None
            send({'type': 'pickdir', 'id': jid, 'path': path})
    except Exception as e:
        log(traceback.format_exc() if not isinstance(e, RuntimeError) else f'{jid} {msg["type"]} failed: {e}')
        send({'type': 'error' if msg['type'] == 'download' else msg['type'],
              'id': jid, 'ok': False, 'error': str(e)})
    finally:
        _cancelled.discard(jid)


def cancel(jid):
    p = _procs.get(jid)
    if p:
        _cancelled.add(jid)
        if WIN:
            subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True, creationflags=NOWIN)
        else:
            try:
                os.killpg(p.pid, signal.SIGKILL)  # yt-dlp and the ffmpeg it started
            except OSError:
                pass


def open_path(p):
    if p and os.path.isfile(p):
        cmd = ['open', '-R', p] if MAC else ['explorer', '/select,', os.path.normpath(p)]
    else:
        p = p or DEFAULT_DIR
        os.makedirs(p, exist_ok=True)
        cmd = ['open', p] if MAC else ['explorer', os.path.normpath(p)]
    subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def host():
    log('host started', ROOT)
    threading.Thread(target=update_loop, daemon=True).start()
    while True:
        msg = read()
        if msg is None:
            break
        t = msg.get('type')
        if t == 'ping':
            send({'type': 'pong', 'id': msg.get('id'), 'defaultDir': DEFAULT_DIR, **_update_state})
        elif t == 'cancel':
            cancel(msg['id'])
        elif t == 'update':
            threading.Thread(target=do_update, args=(True,), daemon=True).start()
        elif t == 'open':
            open_path(msg.get('path'))
        else:
            threading.Thread(target=run_job, args=(msg,), daemon=True).start()
    for jid in list(_procs):
        cancel(jid)
    log('host exit')
    os._exit(0)


if __name__ == '__main__':
    if '--install' in sys.argv or '--uninstall' in sys.argv:
        if '--setup' in sys.argv:  # run hidden by the installer: keep the output in a log instead
            sys.stdout = sys.stderr = open(os.path.join(ROOT, 'install.log'), 'w', encoding='utf-8', buffering=1)
        else:
            sys.stdout.reconfigure(encoding='utf-8')
        try:
            install() if '--install' in sys.argv else uninstall()
        except Exception:
            traceback.print_exc()
            print('\nОшибка установки. Пришлите этот текст автору.')
            sys.exit(1)
    elif '--pickdir' in sys.argv:
        i = sys.argv.index('--pickdir')
        pickdir(sys.argv[i + 1] if len(sys.argv) > i + 1 else '')
    else:
        # Keep the browser pipe private: child processes must never touch fd 0/1.
        _in = os.fdopen(os.dup(0), 'rb', buffering=0)
        _out = os.fdopen(os.dup(1), 'wb', buffering=0)
        _null = os.open(os.devnull, os.O_RDWR)
        os.dup2(_null, 0)
        os.dup2(_null, 1)
        if os.path.isfile(LOG) and os.path.getsize(LOG) > 1 << 20:
            os.remove(LOG)
        sys.stdout = sys.stderr = open(LOG, 'a', encoding='utf-8', buffering=1)
        host()
