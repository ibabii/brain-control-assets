"""2D text kit (contract: interfaces.md, "Intercom, answering machine, text kit"). Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/text_kit/build.py
Writes ui/text_kit/*.png (bubble 9-slice, tail, scribble glyphs, organ icons, lower-third bar) and preview_sheet.png.
Lettering uses Patrick Hand (OFL, cockpit/art/notes/fonts), the same hand as the notes and the TODAY list.
"""
import math
import os
import random
import struct
import sys
import zlib

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cockpit_v2'))
import ink  # noqa: E402
import lib  # noqa: E402

OUT = lib.ROOT + '/ui/text_kit/'
PAPER, INK = '#F4ECDC', '#3A3532'
SS = 3


def save(c, name):
    """Canvas -> straight-alpha RGBA PNG."""
    img = c.image()
    a = img[..., 3:4]
    rgb = np.where(a > 0, img[..., :3], 0)
    px = (np.concatenate([rgb, a], -1) * 255 + 0.5).astype(np.uint8)
    raw = b''.join(b'\x00' + row.tobytes() for row in px)

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(OUT + name, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', c.w, c.h, 8, 6, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    print('TEXT_KIT', name, c.w, c.h)


def blank(w, h):
    return ink.Canvas(w, h, '#FFFFFF', alpha=0.0)


def fill(c, pts, color, opacity=1.0):
    """Anti-aliased polygon fill; pts in canvas pixels (x right, y down)."""
    p = np.array(pts, float) * SS
    H, W = c.h * SS, c.w * SS
    X, Y = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
    inside = np.zeros((H, W), bool)
    for (x0, y0), (x1, y1) in zip(p, np.roll(p, -1, 0)):
        if y0 == y1:
            continue
        cross = ((y0 > Y) != (y1 > Y)) & (X < (x1 - x0) * (Y - y0) / (y1 - y0) + x0)
        inside ^= cross
    c.paint(inside.reshape(c.h, SS, c.w, SS).mean((1, 3)), color, opacity)


def stroke(c, pts, width, color, closed=False, opacity=1.0):
    pts = list(pts) + ([pts[0]] if closed else [])
    c.stroke([(x / c.w, 1 - y / c.h) for x, y in pts], width, color, opacity)


def wobble(pts, amp, seed, closed=True):
    """Hand-drawn jitter: smooth low-frequency offsets along the normal."""
    rnd = random.Random(seed)
    n = len(pts)
    ph = [rnd.uniform(0, 6.28) for _ in range(3)]
    out = []
    for i, (x, y) in enumerate(pts):
        a, b = pts[i - 1], pts[(i + 1) % n]
        tx, ty = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, ty) or 1
        t = i / n * 6.283
        d = amp * (math.sin(2 * t + ph[0]) * 0.6 + math.sin(5 * t + ph[1]) * 0.3 + math.sin(9 * t + ph[2]) * 0.1)
        out.append((x - ty / ln * d, y + tx / ln * d))
    return out


def rrect_px(x0, y0, x1, y1, r, seg=10):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def sketch(c, pts, width, seed):
    """Graphite outline drawn twice, slightly off, like a pencil line gone over."""
    stroke(c, wobble(pts, 1.2, seed), width, INK, True)
    stroke(c, wobble(pts, 1.6, seed + 1), width * 0.45, INK, True, 0.55)


# --- bubble -------------------------------------------------------------------------------------------

BUBBLE = 128          # 9-slice margins 44 px on every side
TAIL = (64, 72)


def bubble():
    c = blank(BUBBLE, BUBBLE)
    pts = rrect_px(4, 4, BUBBLE - 4, BUBBLE - 4, 38)
    fill(c, pts, PAPER)
    sketch(c, pts, 5, 3)
    save(c, 'bubble_9slice.png')


def tail():
    """Tail pointing down-left. Its top 14 px are paper only: overlap the bubble's bottom edge by 10 px so the
    tail's fill covers that stretch of outline."""
    w, h = TAIL
    c = blank(w, h)
    left = [(10, 0), (13, 22), (10, 42), (4, h - 4)]
    right = [(4, h - 4), (28, 44), (46, 22), (56, 0)]
    fill(c, left + right, PAPER)
    stroke(c, wobble(left[1:], 0.8, 5, False) + [(4, h - 4)], 5, INK)
    stroke(c, [(4, h - 4)] + wobble(right[1:-1], 0.8, 6, False) + [(54, 12)], 5, INK)
    save(c, 'bubble_tail.png')


# --- scribble gibberish -----------------------------------------------------------------------------

GLYPH = (56, 72)      # cell; scribbles sit on a baseline at y 58 with cap height ~44 (like caps at 64 px)


def scribbles(n=12):
    """Cursive gibberish: runs of joined loops of mixed height (like e / l loops), so nothing reads as a letter."""
    w, h = GLYPH
    c = blank(w * n, h)
    base = 58
    for k in range(n):
        rnd = random.Random(100 + k)
        ox = k * w
        loops = rnd.choice((2, 3, 3, 4))
        dx = (w - 14) / loops
        pts = [(ox + 4, base - 4)]
        for j in range(loops):
            tall = rnd.random() < 0.35
            hh = rnd.uniform(34, 44) if tall else rnd.uniform(14, 22)
            rx = dx * rnd.uniform(0.35, 0.5)
            x0 = ox + 7 + j * dx
            for i in range(1, 21):
                t = i / 20
                pts.append((x0 + t * dx - rx * math.sin(2 * math.pi * t), base - hh * (1 - math.cos(2 * math.pi * t)) / 2))
        pts.append((ox + w - 3, base - 6))
        stroke(c, wobble(pts, 0.6, k, False), 4.5, INK)
    save(c, 'scribble_glyphs.png')


# --- organ icons (same shapes as the intercom lamps) -------------------------------------------------

ICON = 128
COL = {'heart': '#C98778', 'stomach': '#A9B89F', 'gary': '#D9A04C', 'brain': '#E8A9A0'}


def shape_px(outline, size, cx=64, cy=66):
    return [(cx + x / size * 96, cy - y / size * 96) for x, y in outline]


def icon(name, outline, extra=None, size=1.0):
    c = blank(ICON, ICON)
    pts = shape_px(outline, size)
    fill(c, pts, COL[name])
    if extra:
        extra(c)
    # soft highlight, top-left
    hl = blank(ICON, ICON)
    fill(hl, [(x * 0.55 + 20, y * 0.55 + 18) for x, y in pts], '#FFFFFF')
    c.rgb = c.rgb * (1 - hl.a[..., None] * 0.18 * c.a[..., None]) + hl.a[..., None] * 0.18 * c.a[..., None]
    sketch(c, pts, 6, len(name))
    save(c, 'icon_%s.png' % name)


def build_icons():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cockpit_v2'))
    import intercom
    icon('heart', intercom.heart(1.0))
    icon('stomach', intercom.bean(1.0))
    body, holes = intercom.cassette(0.9)

    def reels(c):
        for hole in holes:
            fill(c, shape_px(hole, 1.0), INK)
        fill(c, rrect_px(36, 46, 92, 60, 4), '#F4ECDC')      # label strip
    icon('gary', body, reels)
    # Brain: lumpy blob with two fold squiggles.
    pts = []
    for i in range(72):
        t = 2 * math.pi * i / 72
        r = 1 + 0.07 * math.sin(7 * t) + 0.03 * math.sin(13 * t)
        pts.append((0.5 * r * math.cos(t), 0.38 * r * math.sin(t) + 0.02))

    def folds(c):
        stroke(c, [(64, 34), (60, 52), (66, 70), (62, 92)], 5, INK)
        stroke(c, [(34, 60), (46, 56), (52, 66)], 4.5, INK)
        stroke(c, [(78, 50), (90, 56), (86, 72), (96, 80)], 4.5, INK)
    icon('brain', pts, folds)


# --- lower-third ---------------------------------------------------------------------------------------

LT = (512, 112)       # 9-slice: left 120 (portrait slot), right 40, top/bottom 0 (stretch horizontally only)


def lower_third():
    w, h = LT
    c = blank(w, h)
    bar = [(64, 26), (w - 30, 26), (w - 6, 50), (w - 30, 104), (64, 104)]
    fill(c, bar, '#2D5C5B')
    fill(c, [(64, 26), (w - 30, 26), (w - 22, 34), (64, 34)], '#D9A04C')          # honey stripe
    stroke(c, bar, 4, '#1F3F3E', True)
    # portrait slot: cream disc, the organ icon goes on top (centre (58, 62), up to 88 px)
    disc = [(58 + 50 * math.cos(t), 62 + 50 * math.sin(t)) for t in np.linspace(0, 6.283, 64, endpoint=False)]
    fill(c, disc, PAPER)
    sketch(c, disc, 5, 9)
    save(c, 'lower_third_bar.png')


# --- preview sheet (for review only) -------------------------------------------------------------------

def paste(dst, src, x, y, sx=1.0, sy=1.0):
    """Nearest-neighbour scaled alpha paste."""
    w, h = int(src.w * sx), int(src.h * sy)
    ys = (np.arange(h) / sy).astype(int)
    xs = (np.arange(w) / sx).astype(int)
    rgb, a = src.rgb[ys][:, xs], src.a[ys][:, xs]
    sl = (slice(y, y + h), slice(x, x + w))
    dst.rgb[sl] = dst.rgb[sl] * (1 - a[..., None]) + rgb * a[..., None]


def nine(src, w, h, m):
    """Stretch a 9-slice canvas to w x h with margins m."""
    c = blank(w, h)
    S = src.w
    xs = np.concatenate([np.arange(m), np.linspace(m, S - m - 1, w - 2 * m).astype(int), np.arange(S - m, S)])
    ys = np.concatenate([np.arange(m), np.linspace(m, S - m - 1, h - 2 * m).astype(int), np.arange(S - m, S)])
    c.rgb, c.a = src.rgb[ys][:, xs], src.a[ys][:, xs]
    return c


def load(name):
    import bpy
    im = bpy.data.images.load(OUT + name)
    px = np.array(im.pixels[:]).reshape(im.size[1], im.size[0], 4)[::-1]
    c = blank(im.size[0], im.size[1])
    c.rgb, c.a = px[..., :3], px[..., 3]
    return c


def preview():
    sheet = ink.Canvas(1200, 560, '#DCCFB8')
    b = nine(load('bubble_9slice.png'), 560, 200, 44)
    paste(sheet, b, 40, 30)
    paste(sheet, load('bubble_tail.png'), 120, 220)
    glyphs = load('scribble_glyphs.png')
    gw = GLYPH[0]
    x = 80
    for k in (0, 5, 2, 9, 3):
        g = blank(gw, GLYPH[1])
        g.rgb, g.a = glyphs.rgb[:, k * gw:(k + 1) * gw], glyphs.a[:, k * gw:(k + 1) * gw]
        paste(sheet, g, x, 70, 0.8, 0.8)
        x += 46
    ink.text(sheet, 'MOP', ((x + 70) / 1200, 1 - 100 / 560), 64 / 560, INK, weight=1.5)
    x2 = 420
    for k in (7, 1, 4):
        g = blank(gw, GLYPH[1])
        g.rgb, g.a = glyphs.rgb[:, k * gw:(k + 1) * gw], glyphs.a[:, k * gw:(k + 1) * gw]
        paste(sheet, g, x2, 70, 0.8, 0.8)
        x2 += 46
    ink.text(sheet, '...THE FLOOR?', (300 / 1200, 1 - 170 / 560), 44 / 560, INK, weight=1.0)
    lt = load('lower_third_bar.png')
    paste(sheet, lt, 640, 60)
    paste(sheet, load('icon_heart.png'), 640 + 18, 60 + 22, 0.66, 0.66)
    ink.text(sheet, 'HEART', (900 / 1200, 1 - 128 / 560), 46 / 560, '#F4ECDC', weight=1.0)
    paste(sheet, lt, 640, 200)
    paste(sheet, load('icon_stomach.png'), 640 + 18, 200 + 22, 0.66, 0.66)
    ink.text(sheet, 'STOMACH', (920 / 1200, 1 - 268 / 560), 46 / 560, '#F4ECDC', weight=1.0)
    for i, n in enumerate(('heart', 'stomach', 'brain', 'gary')):
        ic = load('icon_%s.png' % n)
        paste(sheet, ic, 40 + i * 290, 380)
        paste(sheet, ic, 40 + i * 290 + 150, 380 + 32, 0.5, 0.5)       # 64 px check
    sheet.a[:] = 1
    save(sheet, 'preview_sheet.png')


os.makedirs(OUT, exist_ok=True)
bubble()
tail()
scribbles()
build_icons()
lower_third()
preview()
