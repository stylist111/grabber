"""Grabber native host.

    grabber_host.exe --install      download yt-dlp/ffmpeg/deno, register for browsers
    grabber_host.exe --uninstall    unregister
    grabber_host.exe --pickdir DIR  folder dialog (used internally)
    (no flags)                      native messaging host, started by the browser
"""
import base64
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import zipfile

NAME = 'com.grabber.host'
FROZEN = getattr(sys, 'frozen', False)
# Frozen: Grabber/app/grabber_host.exe. Source: Grabber/src/host.py. Either way ROOT = Grabber/.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable if FROZEN else __file__)))
BIN = os.path.join(ROOT, 'bin')
APP = os.path.join(ROOT, 'app')
DEFAULT_DIR = os.path.join(ROOT, 'downloads')
LOG = os.path.join(ROOT, 'host.log')
UPDATE_EVERY = 3 * 3600
NOWIN = subprocess.CREATE_NO_WINDOW
BROWSERS = [
    r'Software\Google\Chrome',
    r'Software\Microsoft\Edge',
    r'Software\BraveSoftware\Brave-Browser',
    r'Software\Yandex\YandexBrowser',
    r'Software\Chromium',
]
URLS = {
    'yt-dlp': 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe',
    'ffmpeg': 'https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip',
    'deno': 'https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip',
}


def self_cmd(*args):
    return [sys.executable, *args] if FROZEN else [sys.executable, os.path.abspath(__file__), *args]


def tool(name):
    p = os.path.join(BIN, name + '.exe')
    return p if os.path.isfile(p) else shutil.which(name)


# --------------------------------------------------------------------------- install

def ext_id():
    with open(os.path.join(ROOT, 'extension', 'manifest.json'), encoding='utf-8') as f:
        key = json.load(f)['key']
    h = hashlib.sha256(base64.b64decode(key)).hexdigest()[:32]
    return ''.join(chr(ord('a') + int(c, 16)) for c in h)


def fetch(url, dest, label):
    print(f'  Скачиваю {label}…', flush=True)
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


def unzip_exes(zpath, names):
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            base = os.path.basename(info.filename)
            if base in names:
                with z.open(info) as src, open(os.path.join(BIN, base), 'wb') as dst:
                    shutil.copyfileobj(src, dst)
    os.remove(zpath)


def install():
    import winreg
    os.makedirs(BIN, exist_ok=True)
    os.makedirs(DEFAULT_DIR, exist_ok=True)
    print('1/3 Компоненты')
    if not os.path.isfile(os.path.join(BIN, 'yt-dlp.exe')):
        fetch(URLS['yt-dlp'], os.path.join(BIN, 'yt-dlp.exe'), 'yt-dlp')
        # Just downloaded the latest release: the first browser start doesn't need to check again.
        with open(os.path.join(BIN, '.last_update'), 'w') as f:
            f.write(time.ctime())
    else:
        print('  yt-dlp уже есть, оставляю (обновится сам)')
    if not tool('ffmpeg'):
        z = os.path.join(BIN, 'ffmpeg.zip')
        fetch(URLS['ffmpeg'], z, 'ffmpeg (~150 МБ)')
        unzip_exes(z, {'ffmpeg.exe', 'ffprobe.exe'})
    else:
        print('  ffmpeg найден:', tool('ffmpeg'))
    if not (tool('deno') or shutil.which('node')):
        z = os.path.join(BIN, 'deno.zip')
        fetch(URLS['deno'], z, 'deno (нужен для YouTube)')
        unzip_exes(z, {'deno.exe'})
    else:
        print('  JS-движок найден:', tool('deno') or shutil.which('node'))

    print('2/3 Регистрация в браузерах')
    exe = sys.executable if FROZEN else os.path.join(APP, 'grabber_host.bat')
    if not FROZEN:  # dev run from source
        os.makedirs(APP, exist_ok=True)
        with open(exe, 'w', encoding='ascii') as f:
            f.write(f'@echo off\r\n"{sys.executable}" -u "{os.path.abspath(__file__)}" %*\r\n')
    manifest = os.path.join(APP, NAME + '.json')
    eid = ext_id()
    with open(manifest, 'w', encoding='utf-8') as f:
        json.dump({'name': NAME, 'description': 'Grabber host', 'path': exe, 'type': 'stdio',
                   'allowed_origins': [f'chrome-extension://{eid}/']}, f, indent=2)
    for b in BROWSERS:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf'{b}\NativeMessagingHosts\{NAME}') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, manifest)

    print('3/3 Проверка yt-dlp')
    out = subprocess.run([tool('yt-dlp'), '--version'], capture_output=True, text=True).stdout.strip()
    print('  yt-dlp', out)
    ext_dir = os.path.join(ROOT, 'extension')
    copy_to_clipboard(ext_dir)
    print(f'\nГотово. Путь к расширению скопирован в буфер обмена:\n  {ext_dir}')


def copy_to_clipboard(text):
    # Windows refuses clipboard writes from a process without a window, so let PowerShell do it.
    # The text goes through an env var: no quoting issues with odd user names.
    subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                    'Set-Clipboard -Value $env:GRABBER_CLIP'],
                   env=dict(os.environ, GRABBER_CLIP=text), creationflags=NOWIN,
                   stdin=subprocess.DEVNULL, capture_output=True, timeout=30)


def uninstall():
    import winreg
    ours = os.path.normcase(os.path.join(APP, NAME + '.json'))
    for b in BROWSERS:
        key = rf'{b}\NativeMessagingHosts\{NAME}'
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
                target = winreg.QueryValueEx(k, '')[0]
            # Only unregister if the browser points at THIS copy: removing a second, older
            # install must not disconnect the one the user actually runs.
            if os.path.normcase(target) == ours:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
        except FileNotFoundError:
            pass
    print('Grabber отключён от браузеров. Папку можно удалить.')


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
    e['PATH'] = BIN + os.pathsep + e.get('PATH', '')
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
        if exe and due and exe.startswith(BIN):
            _update_state['status'] = 'updating'
            send({'type': 'update', **_update_state})
            try:
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
    a = ['--no-playlist', '--no-warnings', '--remote-components', 'ejs:github']
    deno, node = tool('deno'), shutil.which('node')
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

    args = [tool('yt-dlp'), *common_args(), '--newline', '--progress', '--windows-filenames',
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
                         env=env(), creationflags=NOWIN)
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
        for f in os.listdir(out_dir):  # drop this job's partial files
            fp = os.path.join(out_dir, f)
            if ('.part' in f or f.endswith('.ytdl')) and os.path.getmtime(fp) >= started:
                try:
                    os.remove(fp)
                except OSError:
                    pass
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
            r = subprocess.run(self_cmd('--pickdir', msg.get('initial') or DEFAULT_DIR),
                               capture_output=True, creationflags=NOWIN, stdin=subprocess.DEVNULL)
            send({'type': 'pickdir', 'id': jid, 'path': r.stdout.decode('utf-8').strip() or None})
    except Exception as e:
        if not isinstance(e, RuntimeError):
            log(traceback.format_exc())
        send({'type': 'error' if msg['type'] == 'download' else msg['type'],
              'id': jid, 'ok': False, 'error': str(e)})
    finally:
        _cancelled.discard(jid)


def cancel(jid):
    p = _procs.get(jid)
    if p:
        _cancelled.add(jid)
        subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True, creationflags=NOWIN)


def open_path(p):
    if p and os.path.isfile(p):
        subprocess.Popen(['explorer', '/select,', os.path.normpath(p)])
    else:
        p = p or DEFAULT_DIR
        os.makedirs(p, exist_ok=True)
        subprocess.Popen(['explorer', os.path.normpath(p)])


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
