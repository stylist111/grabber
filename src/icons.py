"""Small toolbar icons (16/32) for the extension.

python icons.py preview <out.png>   — compare variants at real size and zoomed
python icons.py write               — write the chosen variant into extension/assets/icons
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(ROOT, 'extension', 'assets', 'icons')
BIG = os.path.join(ICONS, 'icon-512-store.png')


def from_3d(size):
    """Variant A: the designer's 3D icon, downscaled in steps and lightly sharpened."""
    im = Image.open(BIG).convert('RGBA')
    while im.width // 2 >= size * 2:
        im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    im = im.resize((size, size), Image.LANCZOS)
    return im.filter(ImageFilter.UnsharpMask(radius=0.6, percent=60, threshold=1))


def flat(size):
    """Variant B: flat redraw of the same idea — folder with three media cards (music / video / photo)."""
    S = 32 * 16  # draw on a 512 canvas (16 units per 1/32), downscale with antialiasing
    u = S / 32
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # blue rounded tile with a vertical gradient
    grad = Image.new('RGBA', (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / S
        c = tuple(int(a + (b - a) * t) for a, b in zip((120, 182, 255), (52, 104, 240)))
        gd.line([(0, y), (S, y)], fill=c + (255,))
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=8 * u, fill=255)
    im.paste(grad, (0, 0), mask)
    # three cards peeking out of the folder
    cards = [(5.2, 7.5, -10, (167, 120, 255)), (11.2, 5.2, 0, (60, 130, 255)), (17.2, 7.5, 10, (60, 196, 140))]
    for x, y, ang, col in cards:
        card = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle([x * u, y * u, (x + 9.6) * u, (y + 13) * u], radius=1.8 * u, fill=(255, 255, 255, 255))
        cd.ellipse([(x + 2.8) * u, (y + 3.2) * u, (x + 6.8) * u, (y + 7.2) * u], fill=col + (255,))
        card = card.rotate(-ang, center=((x + 4.8) * u, (y + 13) * u), resample=Image.BICUBIC)
        im.alpha_composite(card)
    # folder front
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([3.2 * u, 15.2 * u, 28.8 * u, 28.2 * u], radius=3 * u, fill=(255, 181, 46, 255))
    d.rounded_rectangle([3.2 * u, 15.2 * u, 28.8 * u, 17.2 * u], radius=1 * u, fill=(255, 205, 100, 255))
    return im.resize((size, size), Image.LANCZOS)


def preview(out):
    rows = [('A', from_3d), ('B', flat), ('now', lambda s: Image.open(os.path.join(ICONS, f'icon-{s}.png')).convert('RGBA'))]
    W, H = 900, 110 * len(rows) + 20
    c = Image.new('RGB', (W, H), (255, 255, 255))
    d = ImageDraw.Draw(c)
    for i, (name, fn) in enumerate(rows):
        y = 20 + i * 110
        d.text((10, y + 30), name, fill=(0, 0, 0))
        x = 60
        for bg in ((255, 255, 255), (223, 230, 245), (40, 40, 44)):  # light toolbar, tinted, dark toolbar
            d.rectangle([x, y, x + 60, y + 60], fill=bg)
            c.paste(fn(16), (x + 6, y + 22), fn(16))
            c.paste(fn(32), (x + 24, y + 14), fn(32))
            x += 70
        for s, z in ((16, 6), (32, 3)):
            big = fn(s).resize((s * z, s * z), Image.NEAREST)
            c.paste(big, (x, y), big)
            x += s * z + 20
    c.save(out)


def write(fn):
    for s in (16, 32):
        fn(s).save(os.path.join(ICONS, f'icon-{s}.png'))


if __name__ == '__main__':
    if sys.argv[1] == 'preview':
        preview(sys.argv[2])
    else:
        write({'A': from_3d, 'B': flat}[sys.argv[2]])
