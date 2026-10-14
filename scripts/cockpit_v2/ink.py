"""Tiny anti-aliased 2D painter (numpy) for paper textures: fills, pen strokes and stock doodles.

Coordinates are (u, v) in 0..1 with v up, like mesh UVs. Pixels are square, so give the canvas the paper's aspect.
Colours are sRGB hex strings.
"""
import math

import numpy as np

import lib


def rgb(h):
    return np.array(lib.srgb(h))


def blur(a, r):
    """Box blur (3 passes ~ gaussian) along both axes, wrap-free."""
    for _ in range(3):
        for ax in (0, 1):
            k = 2 * r + 1
            pad = [(0, 0)] * a.ndim
            pad[ax] = (r + 1, r)
            c = np.cumsum(np.pad(a, pad, mode='edge'), axis=ax)
            a = (np.take(c, range(k, c.shape[ax]), axis=ax) - np.take(c, range(0, c.shape[ax] - k), axis=ax)) / k
    return a


class Canvas:
    def __init__(self, w, h, color='#ffffff', alpha=1.0):
        self.w, self.h = w, h
        self.rgb = np.ones((h, w, 3)) * rgb(color)
        self.a = np.full((h, w), alpha)
        self.x, self.y = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)

    def px(self, u, v):
        return u * self.w, (1 - v) * self.h

    def paint(self, mask, color, opacity=1.0):
        m = np.clip(mask, 0, 1)[..., None] * opacity
        self.rgb = self.rgb * (1 - m) + rgb(color) * m
        self.a = np.maximum(self.a, m[..., 0])

    def multiply(self, factor):
        self.rgb *= factor[..., None]

    # --- shapes (masks) ---

    def ellipse(self, c, rx, ry, color, rot=0.0, opacity=1.0, soft=1.0):
        """rx, ry as fractions of canvas height."""
        cx, cy = self.px(*c)
        rx, ry = rx * self.h, ry * self.h
        ca, sa = math.cos(rot), math.sin(rot)
        dx, dy = self.x - cx, -(self.y - cy)
        lx, ly = dx * ca + dy * sa, -dx * sa + dy * ca
        d = np.sqrt((lx / rx) ** 2 + (ly / ry) ** 2)
        self.paint((1 - d) * min(rx, ry) / soft + 0.5, color, opacity)

    def stroke(self, pts, width, color, opacity=1.0):
        """Polyline through (u, v) points; width in pixels."""
        p = np.array([self.px(u, v) for u, v in pts])
        r = width / 2
        x0, y0 = int(max(p[:, 0].min() - r - 2, 0)), int(max(p[:, 1].min() - r - 2, 0))
        x1, y1 = int(min(p[:, 0].max() + r + 2, self.w)), int(min(p[:, 1].max() + r + 2, self.h))
        if x1 <= x0 or y1 <= y0:
            return
        X, Y = self.x[y0:y1, x0:x1], self.y[y0:y1, x0:x1]
        d = np.full(X.shape, 1e9)
        for a, b in zip(p, p[1:] if len(p) > 1 else p):
            ab = b - a
            t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / max(ab @ ab, 1e-9), 0, 1)
            d = np.minimum(d, np.hypot(X - a[0] - t * ab[0], Y - a[1] - t * ab[1]))
        mask = np.zeros((self.h, self.w))
        mask[y0:y1, x0:x1] = r - d + 0.5
        self.paint(mask, color, opacity)

    def image(self):
        return np.concatenate([np.clip(self.rgb, 0, 1), self.a[..., None]], -1)


# --- paper -------------------------------------------------------------------------------------------

def paper(w, h, color, seed=0, grain=0.035, vignette=0.06):
    """Paper base: fibre grain, soft edge darkening."""
    c = Canvas(w, h, color)
    rng = np.random.default_rng(seed)
    fine = blur(rng.random((h, w)), 1)
    coarse = blur(rng.random((h, w)), max(w // 24, 2))
    n = (fine - fine.mean()) / (fine.std() + 1e-6) * 0.4 + (coarse - coarse.mean()) / (coarse.std() + 1e-6)
    f = 1 + grain * n / 2
    u = (c.x / w - 0.5) * 2
    v = (c.y / h - 0.5) * 2
    f *= 1 - vignette * np.clip(np.maximum(abs(u), abs(v)) - 0.75, 0, 1) / 0.25
    c.multiply(f)
    return c


def ruled(c, spacing, color='#9DB4C8', top=0.88, bottom=0.04, margin=None):
    v = top
    while v > bottom:
        c.stroke([(0.0, v), (1.0, v)], 1.2, color, 0.55)
        v -= spacing
    if margin is not None:
        c.stroke([(margin, 0), (margin, 1)], 1.4, '#E08A8A', 0.6)


def stain(c, centre, r, color='#8A5A3A', seed=1):
    """Faint coffee ring."""
    rng = np.random.default_rng(seed)
    pts = []
    for i in range(41):
        a = 2 * math.pi * i / 40
        k = 1 + 0.05 * math.sin(3 * a + rng.random())
        pts.append((centre[0] + r * k * math.cos(a) * c.h / c.w, centre[1] + r * k * math.sin(a)))
    c.stroke(pts, max(c.h * 0.012, 2), color, 0.18)


# --- doodles: centre (u, v), size s = fraction of canvas height ----------------------------------------

def _pts(c, centre, s, shape):
    k = c.h / c.w
    return [(centre[0] + x * s * k, centre[1] + y * s) for x, y in shape]


def _arc(cx, cy, r, a0, a1, n=20, ry=None):
    ry = r if ry is None else ry
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def smiley(c, centre, s, ink, w=None, ring=True):
    w = w or max(c.h * 0.014, 1.6)
    if ring:
        c.stroke(_pts(c, centre, s, _arc(0, 0, 0.5, 0, 2 * math.pi, 36)), w, ink)
    for ex in (-0.17, 0.17):
        c.stroke(_pts(c, centre, s, [(ex, 0.14), (ex, 0.06)]), w * 1.2, ink)
    c.stroke(_pts(c, centre, s, _arc(0, 0.02, 0.27, math.radians(200), math.radians(340), 14)), w, ink)


def heart(c, centre, s, ink, w=None, fill=None):
    w = w or max(c.h * 0.014, 1.6)
    shape = []
    for i in range(49):
        t = 2 * math.pi * i / 48
        shape.append((16 * math.sin(t) ** 3 / 34, (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t)
                                                   - math.cos(4 * t)) / 34))
    pts = _pts(c, centre, s, shape)
    if fill:
        for k in np.linspace(0.15, 0.95, 6):
            c.stroke(_pts(c, centre, s * k, shape), w * 2.2, fill)
    c.stroke(pts, w, ink)


def star(c, centre, s, ink, w=None):
    w = w or max(c.h * 0.012, 1.4)
    pts = []
    for i in range(11):
        a = math.pi / 2 + i * math.pi / 5
        r = 0.5 if i % 2 == 0 else 0.21
        pts.append((r * math.cos(a), r * math.sin(a)))
    c.stroke(_pts(c, centre, s, pts), w, ink)


def cat(c, centre, s, ink, w=None):
    w = w or max(c.h * 0.012, 1.4)
    head = [(-0.42, 0.1), (-0.38, 0.5), (-0.17, 0.3), (0.17, 0.3), (0.38, 0.5), (0.42, 0.1)] + \
        _arc(0, 0.06, 0.42, 0, -math.pi, 18, 0.34)[1:]
    c.stroke(_pts(c, centre, s, head), w, ink)
    for ex in (-0.16, 0.16):
        c.stroke(_pts(c, centre, s, _arc(ex, 0.07, 0.06, 0.2, math.pi - 0.2, 6)), w, ink)
    c.stroke(_pts(c, centre, s, [(-0.08, -0.06), (0, -0.12), (0.08, -0.06)]), w, ink)
    for side in (-1, 1):
        for dy in (-0.03, -0.11):
            c.stroke(_pts(c, centre, s, [(side * 0.28, dy), (side * 0.62, dy + 0.05 * (1 if dy > -0.05 else -1))]),
                     w * 0.8, ink)


def bulb(c, centre, s, ink, w=None):
    w = w or max(c.h * 0.012, 1.4)
    c.stroke(_pts(c, centre, s, _arc(0, 0.08, 0.24, math.radians(-50), math.radians(230), 24)), w, ink)
    for y in (-0.16, -0.23, -0.3):
        c.stroke(_pts(c, centre, s, [(-0.12, y), (0.12, y)]), w, ink)
    c.stroke(_pts(c, centre, s, [(-0.06, -0.02), (-0.02, 0.12), (0.02, 0.0), (0.06, 0.12)]), w * 0.8, ink)
    for a in (150, 115, 90, 65, 30):
        r = math.radians(a)
        c.stroke(_pts(c, centre, s, [(0.33 * math.cos(r), 0.08 + 0.33 * math.sin(r)),
                                     (0.45 * math.cos(r), 0.08 + 0.45 * math.sin(r))]), w * 0.8, ink)


def rainbow(c, centre, s, w=None):
    w = w or max(c.h * 0.02, 2)
    for i, col in enumerate(['#E8615A', '#F2A332', '#F2D35A', '#7CC46A', '#5AA2E0', '#9A7BD0']):
        c.stroke(_pts(c, centre, s, _arc(0, 0, 0.5 - i * 0.055, 0, math.pi, 30)), w, col, 0.85)


def tick(c, centre, s, ink, w=None):
    w = w or max(c.h * 0.03, 2)
    c.stroke(_pts(c, centre, s, [(-0.35, 0.02), (-0.08, -0.3), (0.42, 0.42)]), w, ink)


def box(c, centre, s, ink, w=None, seed=0):
    w = w or max(c.h * 0.03, 2)
    rng = np.random.default_rng(seed)
    j = lambda: rng.uniform(-0.025, 0.025)  # noqa: E731
    c.stroke(_pts(c, centre, s, [(-0.4 + j(), 0.4 + j()), (0.4 + j(), 0.42 + j()), (0.41 + j(), -0.4 + j()),
                                 (-0.4 + j(), -0.41 + j()), (-0.41 + j(), 0.44)]), w, ink)


def brain(c, centre, s, ink_col, fill):
    """Little pink brain doodle: lobed blob plus squiggly folds."""
    k = c.h / c.w
    c.ellipse(centre, s * 0.55 * 0.5 / 1, s * 0.36, fill)
    for dx, dy in ((-0.3, 0.08), (0.28, 0.1), (0, 0.18), (-0.15, -0.12), (0.18, -0.12)):
        c.ellipse((centre[0] + dx * s * k, centre[1] + dy * s), s * 0.24, s * 0.2, fill)
    w = max(c.h * 0.01, 1.6)
    rng = np.random.default_rng(2)
    for _ in range(7):
        x0, y0 = rng.uniform(-0.4, 0.3), rng.uniform(-0.2, 0.25)
        pts = [(x0 + 0.05 * i, y0 + 0.05 * math.sin(i * 1.7 + x0 * 9)) for i in range(4)]
        c.stroke(_pts(c, centre, s, pts), w, ink_col)
    c.stroke(_pts(c, centre, s, [(0, -0.3), (0.02, -0.42), (0.08, -0.5)]), w * 1.5, ink_col)


# --- photo for the polaroid: a cartoon golden retriever ----------------------------------------------

def dog_photo(w, h):
    c = Canvas(w, h, '#5E7F5A')
    yy = c.y / h
    sky = np.stack([np.interp(yy, [0, 0.6, 1], [a, b, d]) for a, b, d in
                    zip(rgb('#8DB3A8'), rgb('#6F8F62'), rgb('#4F6B45'))], -1)
    c.rgb = sky
    rng = np.random.default_rng(5)
    for _ in range(14):          # out-of-focus garden
        c.ellipse((rng.random(), rng.uniform(0.45, 1.0)), rng.uniform(0.04, 0.1), rng.uniform(0.04, 0.1),
                  ['#B9C98A', '#E6D9A2', '#8FAF74', '#F1E4CF'][rng.integers(4)], opacity=0.35, soft=6)
    gold, dark, light = '#D9A04C', '#B5752F', '#F1CF94'
    c.ellipse((0.5, 0.12), 0.42, 0.22, gold)                      # chest
    c.ellipse((0.24, 0.5), 0.12, 0.25, dark, rot=-0.35)           # ears
    c.ellipse((0.76, 0.5), 0.12, 0.25, dark, rot=0.35)
    c.ellipse((0.5, 0.52), 0.3, 0.3, gold)                        # head
    c.ellipse((0.5, 0.62), 0.2, 0.12, '#E2B060', opacity=0.6, soft=8)
    c.ellipse((0.5, 0.36), 0.17, 0.14, light)                     # muzzle
    c.ellipse((0.5, 0.22), 0.07, 0.1, '#E36E86')                  # tongue
    c.stroke([(0.5, 0.3), (0.5, 0.18)], max(h * 0.01, 1.5), '#C24F68')
    c.ellipse((0.5, 0.42), 0.065, 0.045, '#2B2220')               # nose
    c.ellipse((0.485, 0.435), 0.018, 0.01, '#8A7A72')
    c.stroke([(0.5, 0.38), (0.5, 0.34)], max(h * 0.008, 1.5), '#2B2220')
    c.stroke([(0.38, 0.34), (0.44, 0.31), (0.5, 0.34), (0.56, 0.31), (0.62, 0.34)], max(h * 0.008, 1.5), '#2B2220')
    for ex in (0.39, 0.61):
        c.ellipse((ex, 0.56), 0.04, 0.045, '#2B2220')
        c.ellipse((ex + 0.012, 0.575), 0.012, 0.012, '#FFFFFF')
    shade = 1 - 0.18 * np.clip((c.x / w - 0.5) ** 2 * 4 + (c.y / h - 0.5) ** 2 * 4 - 0.5, 0, 1)
    c.multiply(shade)
    return c


# --- text: Blender lays out the glyphs, numpy rasterises the triangles -------------------------------

FONT = lib.ROOT + '/cockpit/art/notes/fonts/PatrickHand-Regular.ttf'
_font = None


def _glyph_tris(body, align):
    import bmesh
    import bpy
    global _font
    if _font is None:
        _font = bpy.data.fonts.load(FONT)
    cu = bpy.data.curves.new('tmp_text', 'FONT')
    cu.body, cu.font, cu.align_x, cu.size = body, _font, align.upper(), 1.0
    cu.space_line = 1.0
    ob = bpy.data.objects.new('tmp_text', cu)
    bpy.context.scene.collection.objects.link(ob)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    tris = np.array([[(v.co.x, v.co.y) for v in f.verts] for f in bm.faces]) if bm.faces else np.zeros((0, 3, 2))
    bm.free()
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    return tris


def text(c, body, centre, height, color, align='center', opacity=1.0, rot=0.0, weight=0):
    """Paint `body` with its glyph em = `height` (fraction of canvas height), block centred on `centre`.
    `weight` thickens strokes by that many pixels (marker lettering)."""
    tris = _glyph_tris(body, align)
    if not len(tris):
        return
    lo, hi = tris.reshape(-1, 2).min(0), tris.reshape(-1, 2).max(0)
    mid = (lo + hi) / 2
    ss = 3                                     # supersampling
    k = height * c.h * ss
    ca, sa = math.cos(rot), math.sin(rot)
    cx, cy = c.px(*centre)
    p = (tris - mid) * k
    p = np.stack([p[..., 0] * ca - p[..., 1] * sa, p[..., 0] * sa + p[..., 1] * ca], -1)
    p[..., 0] += cx * ss
    p[..., 1] = cy * ss - p[..., 1]
    mask = np.zeros((c.h * ss, c.w * ss))
    for t in p:
        x0, y0 = np.floor(t.min(0)).astype(int)
        x1, y1 = np.ceil(t.max(0)).astype(int) + 1
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, c.w * ss), min(y1, c.h * ss)
        if x1 <= x0 or y1 <= y0:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        (ax, ay), (bx, by), (qx, qy) = t
        d = (bx - ax) * (qy - ay) - (by - ay) * (qx - ax)
        if abs(d) < 1e-12:
            continue
        w0 = ((bx - X) * (qy - Y) - (by - Y) * (qx - X)) / d
        w1 = ((qx - X) * (ay - Y) - (qy - Y) * (ax - X)) / d
        inside = (w0 >= 0) & (w1 >= 0) & (w0 + w1 <= 1)
        mask[y0:y1, x0:x1] = np.maximum(mask[y0:y1, x0:x1], inside)
    if weight:
        r = int(round(weight * ss))
        grown = mask.copy()
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    grown = np.maximum(grown, np.roll(np.roll(mask, dy, 0), dx, 1))
        mask = grown
    mask = mask.reshape(c.h, ss, c.w, ss).mean((1, 3))
    c.paint(mask, color, opacity)
