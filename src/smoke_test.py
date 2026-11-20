"""End-to-end check of an installed helper, talking to it exactly like the browser does
(native messaging: 4-byte length + JSON over stdin/stdout).

    python src/smoke_test.py HOST_CMD... [--url URL] [--out DIR]

    python src/smoke_test.py ~/Grabber/app/grabber_host
    python src/smoke_test.py python src/host.py --url https://vimeo.com/76979871

Checks: ping, media info, audio download (mp3 via ffmpeg), video download (video+audio merged
by ffmpeg), cancel of a running download. Exit code 0 = all good.
"""
import json
import os
import queue
import struct
import subprocess
import sys
import tempfile
import threading
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # CI consoles on Windows are cp1252

DEFAULT_URL ='https://www.youtube.com/watch?v=jNQXAC9IVRw'  # "Me at the zoo", 19 s
LONG_URL = 'https://www.youtube.com/watch?v=aqz-KE-bpKQ'     # Big Buck Bunny, for the cancel test
FALLBACK_AUDIO = 'https://soundcloud.com/forss/flickermood'
FALLBACK_VIDEO = 'https://archive.org/details/BigBuckBunny_124'

args = sys.argv[1:]
url, out, long_url = os.environ.get('GRABBER_TEST_URL') or DEFAULT_URL, None, None
for flag in ('--url', '--out', '--long-url'):
    if flag in args:
        i = args.index(flag)
        val = args[i + 1]
        del args[i:i + 2]
        if flag == '--url':
            url = val
        elif flag == '--out':
            out = val
        else:
            long_url = val
long_url = long_url or (LONG_URL if url == DEFAULT_URL else url)
if not args:
    sys.exit(__doc__)
out = out or tempfile.mkdtemp(prefix='grabber-smoke-')
os.makedirs(out, exist_ok=True)

p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
inbox = queue.Queue()


def reader():
    while True:
        raw = p.stdout.read(4)
        if len(raw) < 4:
            inbox.put(None)
            return
        n = struct.unpack('<I', raw)[0]
        inbox.put(json.loads(p.stdout.read(n).decode('utf-8')))


threading.Thread(target=reader, daemon=True).start()


def send(msg):
    data = json.dumps(msg).encode('utf-8')
    p.stdin.write(struct.pack('<I', len(data)) + data)
    p.stdin.flush()


def wait_for(pred, timeout, what):
    end = time.time() + timeout
    while time.time() < end:
        try:
            m = inbox.get(timeout=1)
        except queue.Empty:
            continue
        if m is None:
            raise SystemExit(f'FAIL {what}: helper exited')
        if m.get('type') == 'progress':
            continue
        print('   <-', json.dumps(m, ensure_ascii=False)[:300])
        if pred(m):
            return m
    raise SystemExit(f'FAIL {what}: no answer in {timeout} s')


failed = []


def check(name, ok, detail=''):
    print(('OK   ' if ok else 'FAIL ') + name, detail)
    if not ok:
        failed.append(name)


t0 = time.time()
send({'type': 'ping', 'id': 'p1'})
m = wait_for(lambda m: m.get('type') == 'pong', 60, 'ping')
check('ping', bool(m.get('defaultDir')), f"{time.time() - t0:.1f} s, defaultDir={m.get('defaultDir')}")

send({'type': 'info', 'id': 'i1', 'url': url})
m = wait_for(lambda m: m.get('id') == 'i1', 180, 'info')
audio_url = video_url = url
if not m.get('ok') and 'not a bot' in str(m.get('error')) and url == DEFAULT_URL:
    # YouTube asks datacenter IPs (GitHub's runners) to sign in. Not our bug: check the same
    # code paths on sites that don't do that. On a home connection YouTube works.
    print("SKIP YouTube: this server's IP is asked to sign in; testing on SoundCloud + archive.org")
    audio_url, video_url = FALLBACK_AUDIO, FALLBACK_VIDEO
    long_url = FALLBACK_VIDEO
    send({'type': 'info', 'id': 'i1b', 'url': video_url})
    m = wait_for(lambda m: m.get('id') == 'i1b', 180, 'info')
check('info', m.get('ok') and bool(m.get('title')), f"{m.get('title')!r} heights={m.get('heights')}")

send({'type': 'info', 'id': 'i2', 'url': '--exec=evil'})
m = wait_for(lambda m: m.get('id') == 'i2', 30, 'bad url')
check('rejects non-http url', m.get('ok') is False)


def download(jid, url, **opts):
    send({'type': 'download', 'id': jid, 'dir': out, 'url': url, **opts})
    m = wait_for(lambda m: m.get('id') == jid and m.get('type') in ('done', 'error'), 600, jid)
    f = m.get('file')
    good = m.get('type') == 'done' and f and os.path.isfile(f) and os.path.getsize(f) > 10_000
    return good, f'{f} ({m.get("size")} bytes)' if good else m.get('error')


ok, d = download('a1', audio_url, mode='audio', audio='mp3', meta=True)
check('audio mp3 (ffmpeg + cover)', ok, d)
ok, d = download('v1', video_url, mode='video', height=360, h264=True)
check('video 360p mp4' + (' (ffmpeg merge)' if video_url == url else ''), ok, d)

send({'type': 'download', 'id': 'c1', 'dir': out, 'url': long_url, 'mode': 'video', 'height': 1080, 'h264': False})
time.sleep(8)
send({'type': 'cancel', 'id': 'c1'})
m = wait_for(lambda m: m.get('id') == 'c1' and m.get('type') in ('done', 'error'), 60, 'cancel')
check('cancel', m.get('type') == 'error' and m.get('error') == 'Отменено', m.get('error'))
time.sleep(2)
left = [f for f in os.listdir(out) if '.part' in f or f.endswith('.ytdl')]
check('cancel cleans partial files', not left, left)

p.stdin.close()  # like closing the browser: the helper must exit by itself
try:
    p.wait(timeout=20)
    check('exits when the browser goes away', True)
except subprocess.TimeoutExpired:
    p.kill()
    check('exits when the browser goes away', False)

print('\nfiles in', out, ':', sorted(os.listdir(out)))
sys.exit(f'\n{len(failed)} check(s) failed: {failed}' if failed else 0)
