"""Grab the real Chrome toolbar with the Extensions (puzzle) menu open.

python toolbar-shot.py <window-title-part> <out.png> <click_x> <click_y>
click_x/click_y — puzzle button position relative to the window's top-left (physical px), -1 to skip.
The click is posted to the window (the user's mouse doesn't move), and every Chrome window is
captured with PrintWindow, so other apps lying on top never get into the picture.
"""
import ctypes
import sys
import time
from ctypes import wintypes

from PIL import Image

u32, g32 = ctypes.windll.user32, ctypes.windll.gdi32
u32.SetProcessDPIAware()
title_part, out, cx, cy = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
scale = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0  # Chrome's --force-device-scale-factor
EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def windows():
    res = []

    def cb(hwnd, _):
        if u32.IsWindowVisible(hwnd):
            n = u32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            u32.GetWindowTextW(hwnd, buf, n + 1)
            pid = wintypes.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            r = wintypes.RECT()
            u32.GetWindowRect(hwnd, ctypes.byref(r))
            res.append((hwnd, buf.value, pid.value, (r.left, r.top, r.right, r.bottom)))
        return True

    u32.EnumWindows(EnumProc(cb), 0)
    return res  # top of z-order first


def capture(hwnd, w, h):
    hdc = u32.GetWindowDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    u32.PrintWindow(hwnd, mdc, 2)  # PW_RENDERFULLCONTENT
    bmi = (ctypes.c_byte * 40)()
    ctypes.memmove(bmi, struct_bih(w, h), 40)
    buf = (ctypes.c_byte * (w * h * 4))()
    g32.GetDIBits(mdc, bmp, 0, h, buf, bmi, 0)
    g32.DeleteObject(bmp)
    g32.DeleteDC(mdc)
    u32.ReleaseDC(hwnd, hdc)
    return Image.frombuffer('RGBA', (w, h), bytes(buf), 'raw', 'BGRA', 0, 1).convert('RGB')


def struct_bih(w, h):
    import struct
    return struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 32, 0, 0, 0, 0, 0, 0)


main = next((x for x in windows() if title_part in x[1]), None)
if not main:
    sys.exit('window not found')
hwnd, _, pid, (L, T, R, B) = main

if cx >= 0:
    pt = wintypes.POINT(L + cx, T + cy)
    u32.ScreenToClient(hwnd, ctypes.byref(pt))
    lp = (pt.y << 16) | (pt.x & 0xFFFF)
    u32.PostMessageW(hwnd, 0x0200, 0, lp)   # WM_MOUSEMOVE
    u32.PostMessageW(hwnd, 0x0201, 1, lp)   # WM_LBUTTONDOWN
    u32.PostMessageW(hwnd, 0x0202, 0, lp)   # WM_LBUTTONUP
    time.sleep(1.5)

canvas = Image.new('RGB', (R - L, B - T), 'white')
# Paint bottom-most first: the main window, then Chrome popups (menus/bubbles) above it.
same = [x for x in windows() if x[2] == pid]
for h_, title, _, (l, t, r, b) in reversed(same):
    if r - l < 20 or b - t < 20 or r <= L or l >= R or b <= T or t >= B:
        continue
    img = capture(h_, r - l, b - t)
    if h_ == hwnd:
        canvas.paste(img, (l - L, t - T))
        continue
    # Popups have a transparent shadow margin that PrintWindow renders black: cut it out
    # and draw a soft shadow of our own instead.
    from PIL import ImageDraw, ImageFilter
    light = img.convert('L').point(lambda v: 255 if v > 200 else 0)
    box = light.getbbox()
    mask = Image.new('L', img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=int(12 * scale), fill=255)
    shadow = Image.new('RGB', canvas.size, (0, 0, 0))
    smask = Image.new('L', canvas.size, 0)
    smask.paste(mask, (l - L, t - T + 4))
    smask = smask.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.22))
    canvas.paste(shadow, (0, 0), smask)
    canvas.paste(img, (l - L, t - T), mask)
canvas.save(out)
print('saved', out, [(x[1][:20], x[3]) for x in same])
