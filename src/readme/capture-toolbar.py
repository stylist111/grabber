"""Capture the real Chrome Extensions (puzzle) menu for the guide, in a given UI language.

python capture-toolbar.py <ru|en> <out.png>   → prints ring positions JSON (in % of the image)

Runs a throwaway Chrome profile in a visible 820x500 window at 2x scale (the window appears
for a few seconds), loads Grabber through DevTools, finds the puzzle button by template
matching (its position shifts with the toolbar layout), clicks it with a posted message and
captures only Chrome's own windows (toolbar-shot.py), so nothing else on screen gets in.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

def free_port():
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


PORT = free_port()
URL = 'https://www.youtube.com/watch?v=aqz-KE-bpKQ'
lang, out = sys.argv[1], sys.argv[2]


def dark(img):
    return 255.0 - np.asarray(img.convert('L'), dtype=np.float32)


def find(img, tpl_path, region):
    """Best match of a dark-on-light template inside region (l, t, r, b). Returns its box."""
    tpl = dark(Image.open(tpl_path))
    th, tw = tpl.shape
    l, t, r, b = region
    area = dark(img.crop(region))
    tn = (tpl - tpl.mean()) / (tpl.std() + 1e-6)
    best, pos = -1e9, None
    for y in range(0, area.shape[0] - th + 1, 2):
        for x in range(0, area.shape[1] - tw + 1, 2):
            win = area[y:y + th, x:x + tw]
            score = float(((win - win.mean()) / (win.std() + 1e-6) * tn).mean())
            if score > best:
                best, pos = score, (x, y)
    x, y = pos
    return (l + x, t + y, l + x + tw, t + y + th), best


def shot(path, click=None):
    args = [sys.executable, os.path.join(HERE, 'toolbar-shot.py'), ' - Google Chrome', path]
    args += [str(click[0]), str(click[1])] if click else ['-1', '-1']
    subprocess.run(args + ['2'], check=True, capture_output=True)
    return Image.open(path).convert('RGB')


prof = tempfile.mkdtemp(prefix='grabber-shot-')
os.makedirs(os.path.join(prof, 'Default'))
with open(os.path.join(prof, 'Default', 'Preferences'), 'w') as f:
    json.dump({'browser': {'theme': {'color_scheme2': 1, 'color_scheme': 1}}}, f)  # light theme

chrome = subprocess.Popen([CHROME, f'--lang={lang}', '--mute-audio', '--autoplay-policy=user-gesture-required',
                           '--force-device-scale-factor=2', f'--remote-debugging-port={PORT}',
                           '--enable-unsafe-extension-debugging', f'--user-data-dir={prof}', '--no-first-run',
                           '--no-default-browser-check', '--hide-crash-restore-bubble',
                           '--window-position=0,0', '--window-size=820,500', 'about:blank'])
try:
    subprocess.run(['node', os.path.join(HERE, 'cdp-prep.mjs'), str(PORT), os.path.join(ROOT, 'extension'), URL],
                   check=True, capture_output=True)
    tmp = os.path.join(prof, 'a.png')
    before = shot(tmp)
    (pl, pt, pr, pb), s1 = find(before, os.path.join(HERE, 'real', 'tpl-puzzle.png'), (800, 90, 1640, 165))
    cx, cy = (pl + pr) // 2, (pt + pb) // 2
    after = shot(tmp, (cx, cy))
    # The toolbar can re-flow once the menu opens: locate the puzzle again on the final frame.
    (pl, pt, pr, pb), s1 = find(after, os.path.join(HERE, 'real', 'tpl-puzzle.png'), (800, 90, 1640, 165))
    cx, cy = (pl + pr) // 2, (pt + pb) // 2
    (nl, nt, nr, nb), s2 = find(after, os.path.join(HERE, 'real', 'tpl-pin.png'), (cx - 700, 300, min(1640, cx + 120), 700))
    print(f'match scores: puzzle {s1:.2f}, pin {s2:.2f}', file=sys.stderr)

    # crop: the address bar end, the toolbar buttons and the open menu
    L, R, T, B = max(0, cx - 910), min(after.width, cx + 310), 0, 700
    crop = after.crop((L, T, R, B))
    crop.save(out)
    W, H = R - L, B - T
    pad = 6

    def pct(box):
        l, t, r, b = box
        return {'left': round((l - pad - L) / W * 100, 2), 'top': round((t - pad - T) / H * 100, 2),
                'width': round((r - l + 2 * pad) / W * 100, 2), 'height': round((b - t + 2 * pad) / H * 100, 2)}

    puzzle_box = (cx - 32, cy - 32, cx + 32, cy + 32)  # the round hover area around the icon
    print(json.dumps({'puzzle': pct(puzzle_box), 'pin': pct((nl, nt, nr, nb))}))
finally:
    chrome.kill()
    subprocess.run(['taskkill', '/F', '/T', '/PID', str(chrome.pid)], capture_output=True)
    time.sleep(1)
    shutil.rmtree(prof, ignore_errors=True)
