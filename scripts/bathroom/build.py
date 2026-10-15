"""Bathroom set + props, warm_ceramic_v1 (concept: concepts/bathroom/style-a-warm-ceramic.png).
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/bathroom/build.py
Layout = the game's greybox (locations/bathroom/bathroom.tscn); contract: coordination/interfaces.md "Bathroom".
Writes bathroom/art/bathroom_room.glb (static set at identity), bathroom/art/props/<id>.glb (root = prop pivot,
children named as the game scripts expect), bathroom/art/layout.json and manifest.json.
Godot coords throughout: +Y up, the Human stands at (0, 0, 0.2) facing the mirror (-Z).
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cockpit_v2'))
import lib  # noqa: E402
from lib import B, Frame, UPF  # noqa: E402
from sculpt import meta, ell, cap, ball, solid, adopt, godot_rot  # noqa: E402

PAL = {c['id']: c['hex'] for c in json.load(open(os.path.join(lib.ROOT, 'materials', 'warm_ceramic_v1', 'palette.json')))['colors']}
PROF = {'painted': 0.62, 'ceramic': 0.38, 'fabric': 0.9, 'rubber': 0.86, 'paste': 0.72}
WATER = '#9CCFE0'                         # deviation: water/glass tint (not a world colour), alpha 0.85
STEEL = '#A8A49B'                         # deviation: brushed nickel for the faucet (concept)
SKY = '#E4F1EF'

# Room (inner faces): back wall z -0.70, front 2.65, left x -1.55, right 1.55, floor 0, ceiling 2.6.
ZB, ZF, XL, XR, H = -0.70, 2.65, -1.55, 1.55, 2.6
TILE_TOP = 1.2
DOOR = (0.13, 0.97, 2.05)                 # front wall local x range (world x 1.42 .. 0.58), height
WINDOW = (1.75, 2.45, 1.45, 2.05)         # left wall local x range (world z 0.9 .. 0.2), y range
TOWEL_BAR = Vector((-0.72, 1.425, -0.655))
PROPS = {   # id: node position (game), base pivots for the knockables (counter top 0.87)
    'toothpaste': (-0.35, 0.889, -0.4), 'cup': (0.33, 0.87, -0.56), 'soap': (-0.2, 0.87, -0.62),
    'lotion': (0.21, 0.87, -0.64), 'smudge': (0, 1.55, -0.657), 'towel': (-0.72, 1.2, -0.67),
    'faucet': (0, 0.95, -0.64), 'tub': (-1.15, 0.5, 0.55),
}


def M(name, key, profile='painted', **kw):
    return lib.mat(name, PAL.get(key, key), PROF.get(profile, profile) if isinstance(profile, str) else profile, **kw)


# --- textures --------------------------------------------------------------------------------------

def _normal_from(h, k=2.0):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * k
    gy = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) * k
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True) * 0.5 + 0.5


def _rgb(hexc):
    return np.array([lib.linear(c) for c in lib.srgb(hexc)]) ** (1 / 2.2)


def tile_tex(name, base, grout, n=4, px=256, gw=0.05, vary=0.03, seed=1):
    """n x n tiles per texture with grout lines and soft pillowed edges (albedo + normal)."""
    y, x = np.mgrid[0:px, 0:px].astype(float) / px * n
    fx, fy = x % 1, y % 1
    d = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy))       # distance to tile edge
    inside = np.clip((d - gw / 2) / 0.04, 0, 1)
    rng = np.random.default_rng(seed)
    jit = rng.normal(0, vary, (n, n))[(y.astype(int)) % n, (x.astype(int)) % n]
    col = _rgb(base)[None, None] * (1 + jit[..., None]) * inside[..., None] + _rgb(grout)[None, None] * (1 - inside[..., None])
    hgt = np.sqrt(inside)
    return (lib.image_from_array(name, np.clip(col, 0, 1)),
            lib.image_from_array(name + 'N', _normal_from(hgt, 1.5), non_color=True))


def bobble_tex(name, base, n=12, px=192):
    y, x = np.mgrid[0:px, 0:px].astype(float) / px * n
    fx, fy = (x + 0.5 * (np.floor(y) % 2)) % 1 - 0.5, y % 1 - 0.5
    hgt = np.clip(1 - (fx ** 2 + fy ** 2) * 4.5, 0, 1) ** 0.6
    col = _rgb(base)[None, None] * (0.72 + 0.35 * hgt[..., None])
    return (lib.image_from_array(name, np.clip(col, 0, 1)),
            lib.image_from_array(name + 'N', _normal_from(hgt, 2.5), non_color=True))


def terry_tex(name, base, px=128, seed=3):
    rng = np.random.default_rng(seed)
    hgt = rng.random((px, px))
    for _ in range(2):
        hgt = (hgt + np.roll(hgt, 1, 0) + np.roll(hgt, 1, 1) + np.roll(hgt, -1, 0) + np.roll(hgt, -1, 1)) / 5
    hgt = (hgt - hgt.min()) / (hgt.max() - hgt.min())
    col = _rgb(base)[None, None] * (0.84 + 0.25 * hgt[..., None])
    return (lib.image_from_array(name, np.clip(col, 0, 1)),
            lib.image_from_array(name + 'N', _normal_from(hgt, 3.0), non_color=True))


def weave_tex(name, base, n=8, px=128):
    y, x = np.mgrid[0:px, 0:px].astype(float) / px * n
    over = ((np.floor(x) + np.floor(y)) % 2)
    a = np.abs(np.sin(np.pi * (y % 1)))
    b = np.abs(np.sin(np.pi * (x % 1)))
    hgt = np.where(over > 0, a, b) ** 0.5
    col = _rgb(base)[None, None] * (0.7 + 0.38 * hgt[..., None])
    return (lib.image_from_array(name, np.clip(col, 0, 1)),
            lib.image_from_array(name + 'N', _normal_from(hgt, 2.0), non_color=True))


def tex_mat(name, base, tex, rough):
    a, n = tex
    return lib.mat(name, base, rough, image=a, normal=n)


# --- mesh helpers ---------------------------------------------------------------------------------------

def quad_grid(name, frame, x0, x1, y0, y1, mat, parent, tile=None, nx=1, ny=1):
    """Flat rectangle in frame XY facing frame +Z; UVs in metres / tile (texture covers `tile` metres)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    vs = [[bm.verts.new(frame.at((x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, 0))) for i in range(nx + 1)]
          for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            for l, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                px, py = x0 + (x1 - x0) * ii / nx, y0 + (y1 - y0) * jj / ny
                l[uv].uv = (px / tile, py / tile) if tile else (ii / nx, jj / ny)
    return lib.from_bmesh(name, bm, mat, parent, smooth=False)


def wall_rects(w, y0, y1, holes):
    """Split the band [0,w] x [y0,y1] into rectangles around holes (x0, x1, hy0, hy1)."""
    xs = sorted({0.0, w, *[h[0] for h in holes], *[h[1] for h in holes]})
    out = []
    for a, b in zip(xs, xs[1:]):
        cuts = sorted((max(h[2], y0), min(h[3], y1)) for h in holes if h[0] <= a and h[1] >= b and h[2] < y1 and h[3] > y0)
        y = y0
        for c0, c1 in cuts:
            if c0 > y:
                out.append((a, b, y, c0))
            y = max(y, c1)
        if y < y1:
            out.append((a, b, y, y1))
    return out


def loft(name, rings, mat, parent, cap_bottom=True, inward=True):
    """Surface through closed rings (lists of Godot points, same count); optional flat bottom cap."""
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    for a, b in zip(vs, vs[1:]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    if cap_bottom:
        c = bm.verts.new(sum((v.co for v in vs[-1]), Vector()) / n)
        for k in range(n):
            bm.faces.new((vs[-1][k], vs[-1][(k + 1) % n], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    if cap_bottom:                                   # bowls: the bottom faces up (inside visible)
        up = sum((f.normal.y for f in bm.faces if c in f.verts), 0.0)
        if (up < 0) == inward:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return lib.from_bmesh(name, bm, mat, parent)


def rr_ring(w, d, r, y, cx, cz, seg=6):
    return [Vector((cx + x, y, cz - z)) for x, z in lib.rrect(w, d, r, seg)]


def lathe(name, prof, mat, frame, parent, seg=28, pivot=None):
    """Revolve [(r, y)] around frame +Y (open profile; r=0 points close it)."""
    bm = bmesh.new()
    rings = []
    for r, y in prof:
        if r < 1e-6:
            rings.append([bm.verts.new(frame.at((0, y, 0)))])
        else:
            rings.append([bm.verts.new(frame.at((math.sin(a) * r, y, math.cos(a) * r)))
                          for a in [2 * math.pi * k / seg for k in range(seg)]])
    for a, b in zip(rings, rings[1:]):
        for k in range(seg):
            if len(a) == 1:
                bm.faces.new((a[0], b[(k + 1) % seg], b[k]))
            elif len(b) == 1:
                bm.faces.new((a[k], a[(k + 1) % seg], b[0]))
            else:
                bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return lib.from_bmesh(name, bm, mat, parent, pivot if pivot is not None else frame.o)


def ribbon(name, profile, x0, x1, th, mats, parent, nx=10, wave=0.0, split=None):
    """Cloth panel: 2D profile [(y, z)] swept along X from x0 to x1, `th` thick, closed. `split(i)` -> material
    index for profile segment i (stripes)."""
    P = [Vector((0, y, z)) for y, z in profile]
    nrm = []
    for i in range(len(P)):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        nrm.append(Vector((0, -t.z, t.y)))
    bm = bmesh.new()
    layers = []
    for side in (1, -1):
        grid = []
        for j in range(nx + 1):
            x = x0 + (x1 - x0) * j / nx
            row = []
            for i, (p, n) in enumerate(zip(P, nrm)):
                w = wave * math.sin(j / nx * math.pi * 3 + i * 0.3)
                row.append(bm.verts.new(Vector((x, p.y, p.z)) + n * (side * th / 2 + w)))
            grid.append(row)
        layers.append(grid)
    out, inn = layers
    for j in range(nx):
        for i in range(len(P) - 1):
            for g, s in ((out, 1), (inn, -1)):
                q = (g[j][i], g[j + 1][i], g[j + 1][i + 1], g[j][i + 1])
                f = bm.faces.new(q if s > 0 else q[::-1])
                f.material_index = split(i) if split else 0
    for j in range(nx):                                   # rims
        for i in (0, len(P) - 1):
            f = bm.faces.new((out[j][i], inn[j][i], inn[j + 1][i], out[j + 1][i]))
            f.material_index = split(min(i, len(P) - 2)) if split else 0
    for j in (0, nx):
        for i in range(len(P) - 1):
            f = bm.faces.new((out[j][i], out[j][i + 1], inn[j][i + 1], inn[j][i]))
            f.material_index = split(i) if split else 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = lib.from_bmesh(name, bm, mats, parent)
    return o


def sweep(name, pts, radius, mat, parent, seg=12, n=40):
    """Closed tube along a Catmull-Rom curve through pts, radius(t) for t in 0..1."""
    P = [Vector(p) for p in pts]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]

    def at(u):
        i = min(int(u), len(P) - 4)
        t = u - i
        p0, p1, p2, p3 = P[i:i + 4]
        return 0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3)
    span = len(P) - 3
    C = [at(span * k / n) for k in range(n + 1)]
    bm = bmesh.new()
    rings = []
    side = Vector((1, 0, 0))
    for k, c in enumerate(C):
        d = (C[min(k + 1, n)] - C[max(k - 1, 0)]).normalized()
        a = d.cross(side).normalized()
        b = d.cross(a).normalized()
        r = radius(k / n)
        rings.append([bm.verts.new(c + (a * math.cos(t) + b * math.sin(t)) * r)
                      for t in [2 * math.pi * j / seg for j in range(seg)]])
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(seg):
            bm.faces.new((r0[j], r0[(j + 1) % seg], r1[(j + 1) % seg], r1[j]))
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        bm.faces.new(ring[::-1] if rev else ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return lib.from_bmesh(name, bm, mat, parent)


def tube(name, pts, r, mat, parent, res=6):
    return lib.tube(name, pts, r, mat, parent, res=res, bevel_res=2)


def rbox(name, size, mat, frame, parent, bevel):
    """lib.box with the bevel capped at a quarter of the smallest side (larger insets collapse the outline)."""
    return lib.box(name, size, mat, frame, parent, bevel=min(bevel, 0.25 * min(size)))


def cyl(name, r, y0, y1, mat, frame, parent, seg=24, bevel=0.003):
    """Upright cylinder (frame +Y) with a small rounded rim."""
    prof = [(0, y0), (r - bevel, y0), (r, y0 + bevel), (r, y1 - bevel), (r - bevel, y1), (0, y1)]
    return lathe(name, prof, mat, frame, parent, seg)


# --- room ---------------------------------------------------------------------------------------------------

WALLS = {   # name: (frame at the inner face's left-bottom corner, width, holes)
    'Back': (Frame((XL, 0, ZB)), XR - XL, []),
    'Left': (Frame((XL, 0, ZF), (0, 90, 0)), ZF - ZB, [(WINDOW[0], WINDOW[1], WINDOW[2], WINDOW[3])]),
    'Right': (Frame((XR, 0, ZB), (0, -90, 0)), ZF - ZB, []),
    'Front': (Frame((XR, 0, ZF), (0, 180, 0)), XR - XL, [(DOOR[0], DOOR[1], 0.0, DOOR[2])]),
}


def room(root):
    tiles = tex_mat('WallTile', PAL['sage'], tile_tex('WallTileTex', PAL['sage'], '#E7E1D2', seed=2), 0.38)
    floor = tex_mat('FloorTile', PAL['cream'], tile_tex('FloorTileTex', PAL['cream'], '#CDBFA6', n=4, gw=0.04, seed=5), 0.55)
    paint = M('WallPaint', 'cream', 0.85)
    trim = M('Trim', 'porcelain', 'ceramic')
    shell = lib.empty('Shell', (0, 0, 0), root)
    quad_grid('Floor', Frame((XL, 0, ZF), (-90, 0, 0)), 0, XR - XL, 0, ZF - ZB, floor, shell, tile=1.2, nx=4, ny=4)
    quad_grid('Ceiling', Frame((XL, H, ZB), (90, 0, 0)), 0, XR - XL, 0, ZF - ZB, paint, shell, nx=2, ny=2)
    for name, (f, w, holes) in WALLS.items():
        tf = f.child((0, 0, 0.004))                                   # tiles sit 4 mm proud of the paint
        for i, (a, b, y0, y1) in enumerate(wall_rects(w, 0, TILE_TOP, holes)):
            quad_grid('%sTile%d' % (name, i), tf, a, b, y0, y1, tiles, shell, tile=0.6)
        for i, (a, b, y0, y1) in enumerate(wall_rects(w, TILE_TOP, H, holes)):
            quad_grid('%sPaint%d' % (name, i), f, a, b, y0, y1, paint, shell)
        # Bullnose trim on the tile edge (broken by the door).
        spans = [(0.0, w)] if not holes or holes[0][2] > TILE_TOP else [(0.0, holes[0][0]), (holes[0][1], w)]
        for k, (a, b) in enumerate(spans):
            if b - a > 0.02:
                tube('%sTrim%d' % (name, k), [f.at((a, TILE_TOP, 0.006)), f.at((b, TILE_TOP, 0.006))], 0.011, trim, shell, res=2)
    door(root)
    window(root)
    wall_art(root)
    lamp(shell)
    sockets(shell)


def door(root):
    f, w, holes = WALLS['Front']
    x0, x1, h = DOOR
    p = lib.empty('Door', f.at(((x0 + x1) / 2, 0, 0)), root)
    casing = M('Casing', 'porcelain', 'painted')
    leaf_m = M('DoorLeaf', 'cream', 'painted')
    ring = lib.rrect(x1 - x0 + 0.16, h + 0.08, 0.02, 2)
    ring = [(x + (x0 + x1) / 2, y + (h + 0.08) / 2) for x, y in ring]
    hole = [(x + (x0 + x1) / 2, y + h / 2 - 0.02) for x, y in lib.rrect(x1 - x0, h + 0.04, 0.005, 1)][::-1]
    lib.slab('DoorCasing', ring, 0.022, 0.008, casing, f.child((0, 0, 0.0)), p, holes=[hole])
    lf = f.child(((x0 + x1) / 2, 0, -0.03))
    lib.slab('DoorLeaf', [(x, y + h / 2) for x, y in lib.rrect(x1 - x0 - 0.01, h - 0.01, 0.01, 2)], 0.04, 0.008,
             leaf_m, lf, p)
    for k, (cy, ph) in enumerate(((1.45, 0.72), (0.55, 0.78))):      # two shaker panels
        pw = x1 - x0 - 0.2
        outer = lib.rrect(pw, ph, 0.012, 2)
        inner = lib.rrect(pw - 0.07, ph - 0.07, 0.008, 2)[::-1]
        lib.slab('DoorPanel%d' % k, [(x, y + cy) for x, y in outer], 0.008, 0.003, leaf_m, lf.child((0, 0, 0.04)), p,
                 holes=[[(x, y + cy) for x, y in inner]])
    knob = M('Honey', 'honey', 'painted')
    kf = lf.child((-(x1 - x0) / 2 + 0.08, 1.0, 0.04))
    lib.sphere('DoorRose', 0.03, knob, kf.child((0, 0, 0.002)), p, scale=(1, 1, 0.25), seg=20, rings=8)
    lib.sphere('DoorKnob', 0.027, knob, kf.child((0, 0, 0.05)), p, scale=(1, 1, 0.8), seg=20, rings=10)
    tube('DoorKnobNeck', [kf.at((0, 0, 0.004)), kf.at((0, 0, 0.03))], 0.009, knob, p)
    # Robe hooks with a hanging peach towel (dressing seen in the mirror).
    for i, dx in enumerate((-0.1, 0.1)):
        hf = lf.child((dx, 1.72, 0.04))
        tube('Hook%d' % i, [hf.at((0, 0, 0)), hf.at((0, 0, 0.04)), hf.at((0, 0.03, 0.055))], 0.008, knob, p)
    # Bath towel hanging from both hooks (seen in the mirror behind the Human).
    peach = tex_mat('TowelPeach', PAL['peach'], terry_tex('TerryPeach', PAL['peach']), 0.95)
    stripe = tex_mat('TowelStripe', '#F6D9CB', terry_tex('TerryStripe', '#F6D9CB', seed=9), 0.95)
    face = f.at((0, 0, 0.01)).z                                       # door face (world z), towel hangs in front
    prof = [(1.765, face - 0.03), (1.74, face - 0.022)] + [(1.72 - 0.6 * k / 10, face - 0.02 - 0.006 * math.sin(k / 10 * math.pi))
                                                           for k in range(11)]
    cx_ = f.at(((x0 + x1) / 2, 0, 0)).x
    t = ribbon('DoorTowel', prof, cx_ - 0.17, cx_ + 0.17, 0.016, [peach, stripe], p, nx=10, wave=0.004,
               split=lambda i: 1 if i in (9, 10) else 0)
    _box_uv(t, 0.2)


def _box_uv(o, size):
    """Box-projected UVs (for textured blobs without their own unwrap)."""
    me = o.data
    uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            a, b = [co[i] for i in range(3) if i != ax]
            uv.data[li].uv = (a / size, b / size)


def wall_art(root):
    """Clock above the door (seen in the mirror) and a framed print over the toilet shelf."""
    p = lib.empty('WallArt', (0, 0, 0), root)
    f = WALLS['Front'][0]
    cf = f.child((0.55, 2.28, 0.0))
    teal, honey, por = M('Teal', 'teal'), M('Honey', 'honey'), M('ClockFace', 'porcelain', 'painted')
    lib.slab('ClockRim', lib.circle(0.13, 40), 0.035, 0.012, teal, cf, p, holes=[lib.circle(0.108, 40)[::-1]])
    lib.slab('ClockFace', lib.circle(0.112, 40), 0.012, 0.003, por, cf, p)
    for k in range(12):
        a = 2 * math.pi * k / 12
        r0 = 0.09 if k % 3 else 0.08
        tube('Tick%d' % k, [cf.at((math.sin(a) * r0, math.cos(a) * r0, 0.013)), cf.at((math.sin(a) * 0.098, math.cos(a) * 0.098, 0.013))],
             0.0028 if k % 3 else 0.0045, teal, p, res=1)
    tube('HourHand', [cf.at((0, 0, 0.016)), cf.at((0.035, 0.045, 0.016))], 0.0045, M('Graphite', 'graphite', 'rubber'), p, res=1)
    tube('MinuteHand', [cf.at((0, 0, 0.019)), cf.at((-0.005, 0.085, 0.019))], 0.0032, M('Graphite', 'graphite', 'rubber'), p, res=1)
    lib.sphere('ClockPin', 0.008, honey, cf.child((0, 0, 0.02)), p, scale=(1, 1, 0.5), seg=12, rings=6)
    # Print: honey frame, cream mat, soft sage hills and a peach sun.
    rf = WALLS['Right'][0].child((0.5, 1.78, 0.0))                  # world z -0.2, above the toilet
    lib.slab('PrintFrame', lib.rrect(0.34, 0.42, 0.012, 2), 0.022, 0.006, honey, rf, p,
             holes=[lib.rrect(0.28, 0.36, 0.004, 1)[::-1]])
    quad_grid('PrintMat', rf.child((0, 0, 0.006)), -0.145, 0.145, -0.185, 0.185, M('PrintMat', 'cream', 'painted'), p)
    pa = rf.child((0, 0, 0.0075))
    hills = [(-0.11, -0.13)] + [(-0.11 + 0.22 * k / 16, -0.05 + 0.03 * math.sin(k / 16 * math.pi * 1.6)) for k in range(17)] + [(0.11, -0.13)]
    bm = bmesh.new()
    vs = [bm.verts.new(pa.at((x, y, 0))) for x, y in hills]
    bm.faces.new(vs)
    lib.from_bmesh('PrintHills', bm, M('PrintSage', 'sage', 'painted'), p, smooth=False)
    bm = bmesh.new()
    vs = [bm.verts.new(pa.at((0.04 + 0.04 * math.cos(a), 0.06 + 0.04 * math.sin(a), 0.0005))) for a in
          [2 * math.pi * k / 24 for k in range(24)]]
    bm.faces.new(vs)
    lib.from_bmesh('PrintSun', bm, M('PrintPeach', 'peach', 'painted'), p, smooth=False)


def window(root):
    f, w, holes = WALLS['Left']
    x0, x1, y0, y1 = WINDOW
    p = lib.empty('Window', f.at(((x0 + x1) / 2, y0, 0)), root)
    paint = M('Casing', 'porcelain', 'painted')
    depth = 0.12
    # Reveal (the wall's thickness around the opening).
    for name, a, b in (('L', (x0, y0), (x0, y1)), ('R', (x1, y1), (x1, y0)), ('T', (x0, y1), (x1, y1)), ('B', (x1, y0), (x0, y0))):
        bm = bmesh.new()
        q = [f.at((a[0], a[1], 0)), f.at((b[0], b[1], 0)), f.at((b[0], b[1], -depth)), f.at((a[0], a[1], -depth))]
        vs = [bm.verts.new(v) for v in q]
        bm.faces.new(vs)
        bm.normal_update()
        bm.faces.ensure_lookup_table()
        cen = f.at(((x0 + x1) / 2, (y0 + y1) / 2, -depth / 2))
        if bm.faces[0].normal.dot(cen - bm.faces[0].calc_center_median()) < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
        lib.from_bmesh('Reveal' + name, bm, paint, p, smooth=False)
    sky = lib.mat('Sky', SKY, 0.5, emit=SKY, strength=0.9)
    quad_grid('Glass', f.child((0, 0, -0.09)), x0, x1, y0, y1, sky, p)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ring = [(x + cx, y + cy) for x, y in lib.rrect(x1 - x0 + 0.1, y1 - y0 + 0.1, 0.015, 2)]
    hole = [(x + cx, y + cy) for x, y in lib.rrect(x1 - x0 - 0.04, y1 - y0 - 0.04, 0.004, 1)][::-1]
    lib.slab('WindowCasing', ring, 0.02, 0.007, paint, f.child((0, 0, 0)), p, holes=[hole])
    ff = f.child((0, 0, -0.1))
    rbox('MullionV', (0.035, y1 - y0, 0.03), paint, ff.child((cx, cy, 0.015)), p, 0.006)
    rbox('MullionH', (x1 - x0, 0.035, 0.03), paint, ff.child((cx, cy, 0.015)), p, 0.006)
    sill = [(x + cx, y) for x, y in lib.rrect(x1 - x0 + 0.16, 0.16, 0.02, 3)]
    lib.slab('Sill', lib.rrect(0.18, x1 - x0 + 0.16, 0.02, 3), 0.03, 0.01, M('SillCeramic', 'cream', 'ceramic'),
             Frame((XL - 0.03, y0 - 0.03, ZF - cx), UPF), p)
    plant(f.at((cx - 0.15, y0, 0.03)), p, small=True)


def lamp(parent):
    glow = lib.mat('LampGlow', '#FFF3DC', 0.4, emit='#FFF3DC', strength=1.6)
    lib.sphere('LampDome', 0.17, glow, Frame((0, H, 0.4)), parent, scale=(1, 0.45, 1), seg=32, rings=12)
    tube('LampRing', [(math.cos(a) * 0.168, H - 0.004, 0.4 + math.sin(a) * 0.168) for a in
                      [2 * math.pi * k / 24 for k in range(25)]], 0.009, M('Honey', 'honey'), parent, res=1)


def sockets(parent):
    plate = M('Plate', 'porcelain', 'painted')
    f = WALLS['Front'][0]
    sw = f.child((1.15, 1.12, 0.004))
    rbox('SwitchPlate', (0.08, 0.12, 0.012), plate, sw.child((0, 0, 0.006)), parent, 0.004)
    rbox('Switch', (0.022, 0.04, 0.012), M('Honey', 'honey'), sw.child((0, 0, 0.015)), parent, 0.004)
    ob = WALLS['Back'][0].child((XR - XL - 2.0, 1.05, 0.004))       # by the vanity's right
    rbox('OutletPlate', (0.08, 0.08, 0.012), plate, ob.child((0, 0, 0.006)), parent, 0.004)
    for dx in (-0.012, 0.012):
        lib.sphere('OutletHole%d' % (dx > 0), 0.004, M('Graphite', 'graphite', 'rubber'), ob.child((dx, 0, 0.012)),
                   parent, scale=(1, 1, 0.3), seg=8, rings=4)


# --- furniture ------------------------------------------------------------------------------------------------

def vanity(parent):
    p = lib.empty('Vanity', (0, 0, -0.47), parent)
    sage = M('Sage', 'sage', 'painted')
    honey = M('Honey', 'honey', 'painted')
    lib.box('Plinth', (0.84, 0.08, 0.4), M('Teal', 'teal', 'painted'), Frame((0, 0.04, -0.49)), p)
    rbox('Carcass', (0.9, 0.745, 0.45), sage, Frame((0, 0.08 + 0.745 / 2, -0.47)), p, 0.012)
    front = Frame((0, 0, -0.245))
    fronts = [('Drawer', 0.0, 0.735, 0.86, 0.15), ('DoorL', -0.215, 0.37, 0.42, 0.52), ('DoorR', 0.215, 0.37, 0.42, 0.52)]
    for name, cx, cy, w, h in fronts:
        ff = front.child((cx, cy, 0))
        lib.slab(name, lib.rrect(w, h, 0.012, 2), 0.018, 0.006, sage, ff, p)
        if name != 'Drawer':
            lib.slab(name + 'Frame', lib.rrect(w - 0.04, h - 0.04, 0.01, 2), 0.007, 0.0025, sage, ff.child((0, 0, 0.018)),
                     p, holes=[lib.rrect(w - 0.12, h - 0.12, 0.008, 2)[::-1]])
            kx = -0.15 if cx > 0 else 0.15
            lib.sphere(name + 'Knob', 0.019, honey, ff.child((kx, 0.17, 0.035)), p, scale=(1, 1, 0.85), seg=16, rings=8)
            tube(name + 'KnobStem', [ff.at((kx, 0.17, 0.018)), ff.at((kx, 0.17, 0.03))], 0.007, honey, p)
    hf = front.child((0, 0.735, 0.018))
    tube('DrawerPull', [hf.at((-0.12, 0, 0)), hf.at((-0.12, 0, 0.03)), hf.at((0.12, 0, 0.03)), hf.at((0.12, 0, 0))],
         0.0085, honey, p, res=6)
    # Countertop with the basin hole, and the bowl.
    ceramic = M('CounterCeramic', 'cream', 'ceramic')
    lib.slab('Countertop', lib.rrect(0.96, 0.5, 0.03, 4), 0.05, 0.016, ceramic, Frame((0, 0.82, -0.45), UPF), p,
             holes=[lib.rrect(0.48, 0.32, 0.09, 6)[::-1]])
    rings = []
    for t in (0.0, 0.12, 0.35, 0.65, 0.9, 1.0):
        s = 1 - 0.22 * t ** 1.5
        y = 0.866 - 0.124 * math.sin(t * math.pi / 2)
        rings.append(rr_ring(0.48 * s - 0.004, 0.32 * s - 0.004, 0.09 * s, y, 0, -0.45))
    loft('Basin', rings, M('BasinCeramic', 'porcelain', 'ceramic'), p)
    lathe('Drain', [(0, 0.743), (0.022, 0.743), (0.024, 0.745), (0, 0.746)], M('Steel', STEEL, 0.4, metal=0.75),
          Frame((0, 0, -0.45)), p)
    # Counter dressing: plant in a honey pot, folded hand towel.
    plant(Vector((-0.38, 0.87, -0.6)), p)


def plant(base, parent, small=False):
    """Honey ceramic pot + leaves (Kenney Furniture Kit plant, CC0, recoloured)."""
    s = 0.7 if small else 1.0
    pot = lathe('Pot', [(0, 0), (0.045 * s, 0), (0.05 * s, 0.006), (0.058 * s, 0.075 * s), (0.064 * s, 0.08 * s),
                        (0.064 * s, 0.092 * s), (0.056 * s, 0.092 * s), (0.054 * s, 0.075 * s), (0, 0.075 * s)],
                M('Honey', 'honey', 'ceramic'), Frame(base), parent)
    pot.name = 'PlantPot'
    path = os.path.join(lib.ROOT, '.local', 'downloads', 'kenney', 'furniture-kit', 'Models', 'OBJ format',
                        'plantSmall2.obj' if small else 'plantSmall1.obj')
    leaf = lib.mat('Leaf', '#6E8F5E', 0.7)                        # deviation: plant green (concept plant)
    soil = M('Soil', '#5B4636', 'rubber')
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis='NEGATIVE_Z', up_axis='Y')
    new = [o for o in bpy.data.objects if o not in before]
    for o in [o for o in new if o.type != 'MESH']:
        bpy.data.objects.remove(o, do_unlink=True)
    for o in [o for o in new if o.name in bpy.data.objects and bpy.data.objects[o.name] == o]:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        wood = [i for i, m in enumerate(o.data.materials) if m and m.name.startswith('wood')]
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in wood], context='FACES')   # Kenney's pot: ours instead
        lo = min(v.co.z for v in bm.verts)
        for v in bm.verts:                                         # Blender coords -> Godot, scaled into the pot
            g = lib.G(o.matrix_world @ v.co)
            v.co = base + Vector((g.x * 0.55 * s, (g.y - lib.G((0, 0, lo)).y) * 0.55 * s + 0.03 * s, g.z * 0.55 * s))
        mats = [soil if m and m.name.startswith('wood') else leaf for m in o.data.materials]
        o2 = lib.from_bmesh('Plant', bm, mats or [leaf], parent, smooth=False)
        bpy.data.objects.remove(o, do_unlink=True)
        o2.name = 'PlantLeaves'


def mirror_frame(parent):
    """Honey frame around the game's glass (0.74 x 0.6 at z -0.665): whole frame behind z -0.67."""
    parent = lib.empty('Mirror', (0, 1.58, ZB), parent)
    ring = lib.rrect(0.85, 0.7, 0.045, 6)                     # bottom edge 1.23, clear of the tile trim (1.211)
    hole = lib.rrect(0.74, 0.6, 0.015, 3)[::-1]
    lib.slab('MirrorFrame', ring, 0.03, 0.01, M('Honey', 'honey', 'painted'), Frame((0, 1.58, ZB)), parent, holes=[hole])
    lib.box('MirrorBacking', (0.76, 0.62, 0.004), M('Graphite', 'graphite', 'rubber'), Frame((0, 1.58, ZB + 0.002)), parent)


def tub(parent):
    p = lib.empty('Tub', (-1.15, 0, 0.55), parent)
    por = M('TubCeramic', 'porcelain', 'ceramic')
    lib.slab('TubShell', lib.rrect(0.8, 1.7, 0.1, 6), 0.55, 0.035, por, Frame((-1.15, 0, 0.55), UPF), p,
             holes=[lib.rrect(0.62, 1.52, 0.2, 6)[::-1]])
    rings = []
    for t in (0.0, 0.08, 0.3, 0.6, 0.85, 1.0):
        s = 1 - 0.12 * t ** 1.4
        y = 0.545 - 0.42 * math.sin(t * math.pi / 2)
        rings.append(rr_ring(0.62 * s - 0.004, 1.52 * (1 - 0.06 * t ** 1.4) - 0.004, 0.2 * s, y, -1.15, 0.55))
    loft('TubBasin', rings, por, p)
    lathe('TubDrain', [(0, 0.124), (0.026, 0.124), (0.028, 0.126), (0, 0.127)], M('Steel', STEEL, 0.4, metal=0.75),
          Frame((-1.15, 0, -0.08)), p)
    # Teal spout and valve on the left wall at the head end (concept).
    teal = M('Teal', 'teal', 'painted')
    zs_ = -0.12
    tube('TubSpout', [(XL, 0.72, zs_), (XL + 0.1, 0.72, zs_), (XL + 0.15, 0.69, zs_)], 0.02, teal, p)
    lib.sphere('TubValveRose', 0.06, teal, Frame((XL + 0.004, 1.0, zs_), (0, 90, 0)), p, scale=(1, 1, 0.18), seg=24, rings=8)
    tube('TubValveLever', [(XL + 0.01, 1.0, zs_), (XL + 0.05, 1.0, zs_), (XL + 0.06, 1.03, zs_ + 0.07)], 0.012, teal, p)
    # Shower rod (teal, hung from the ceiling) and gathered curtain (cream, sage band) at the head end.
    tube('CurtainRod', [(-0.79, 2.02, -0.32), (-0.79, 2.02, 1.42)], 0.012, teal, p, res=2)
    for i, z in enumerate((-0.32, 1.42)):
        tube('RodDrop%d' % i, [(-0.79, 2.02, z), (-0.79, H, z)], 0.009, teal, p, res=2)
    cream = M('Curtain', 'porcelain', 'fabric')
    band = M('CurtainBand', 'sage', 'fabric')
    prof, nseg = [], 26
    zs = [-0.3 + 0.55 * k / nseg for k in range(nseg + 1)]
    honey = M('Honey', 'honey')
    for k, z in enumerate(zs):
        if k % 3 == 0:
            tube('CurtainRing%d' % k, [(-0.79, 2.035, z - 0.012), (-0.79, 2.0, z), (-0.79, 2.035, z + 0.012)], 0.004, honey, p, res=3)
    bm = bmesh.new()
    ys = [1.99 - (1.99 - 0.6) * j / 16 for j in range(17)]
    grid = [[bm.verts.new((-0.79 + 0.03 * math.sin(k * math.pi / 1.5) * (1 + 0.3 * j / 16), y, z)) for k, z in enumerate(zs)]
            for j, y in enumerate(ys)]
    for j in range(16):
        for k in range(nseg):
            f = bm.faces.new((grid[j][k], grid[j][k + 1], grid[j + 1][k + 1], grid[j + 1][k]))
            f.material_index = 1 if ys[j] < 0.95 else 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cur = lib.from_bmesh('Curtain', bm, [cream, band], p)
    sol = cur.modifiers.new('Th', 'SOLIDIFY')
    sol.thickness = 0.006
    for x in bpy.data.objects:
        x.select_set(x == cur)
    bpy.context.view_layer.objects.active = cur
    bpy.ops.object.modifier_apply(modifier='Th')
    # Bath things: rubber duck at the foot, bottles at the head end.
    duck(Vector((-1.0, 0.551, 1.355)), p)
    for i, (x, col, h, r) in enumerate(((-1.47, 'sage', 0.17, 0.028), (-1.40, 'peach', 0.13, 0.026))):
        b = Frame((x, 0.549, -0.255))
        lathe('Bottle%d' % i, [(0, 0), (r - 0.004, 0), (r, 0.006), (r, h - 0.03), (r * 0.5, h - 0.012), (r * 0.42, h),
                               (0, h)], M('Bottle' + col, col, 'painted'), b, p, seg=20)
        cyl('BottleCap%d' % i, r * 0.48, h, h + 0.022, M('Teal', 'teal'), b, p, seg=16)


def duck(base, parent):
    mb = meta('Duck', 0.003)
    ell(mb, base + Vector((0, 0.03, 0)), (0.04, 0.03, 0.05))
    ball(mb, base + Vector((0, 0.072, -0.026)), 0.026)
    ell(mb, base + Vector((0, 0.045, 0.045)), (0.016, 0.02, 0.016))      # tail
    d = adopt(solid('Duck', [mb], 0.003, 1200, M('DuckYellow', '#E8B84C', 'painted')), parent, base)
    lib.sphere('DuckBeak', 0.014, M('Clay', 'clay'), Frame(base + Vector((0, 0.068, -0.05))), parent, scale=(1, 0.5, 1.1),
               seg=12, rings=6)
    for s in (-1, 1):
        lib.sphere('DuckEye%d' % (s > 0), 0.0045, M('Graphite', 'graphite', 'rubber'),
                   Frame(base + Vector((s * 0.014, 0.082, -0.042))), parent, seg=8, rings=4)
    return d


def toilet(parent):
    p = lib.empty('Toilet', (1.2, 0, -0.35), parent)
    por = M('ToiletCeramic', 'porcelain', 'ceramic')
    mb = meta('Toilet', 0.007)
    ell(mb, (1.2, 0.143, -0.38), (0.12, 0.14, 0.15))                    # pedestal (base on the floor)
    ell(mb, (1.2, 0.32, -0.29), (0.18, 0.075, 0.24))                    # bowl
    ell(mb, (1.2, 0.25, -0.44), (0.13, 0.1, 0.12))                      # back of the bowl
    adopt(solid('ToiletBowl', [mb], 0.006, 2400, por), p, (1.2, 0.2, -0.35))
    seat_o = [(x * 0.36 / 0.36, y) for x, y in lib.rrect(0.36, 0.45, 0.17, 8)]
    cream = M('Seat', 'cream', 'painted')
    lib.slab('Seat', seat_o, 0.025, 0.01, cream, Frame((1.2, 0.395, -0.29), UPF), p, holes=[lib.rrect(0.22, 0.28, 0.1, 8)[::-1]])
    lib.slab('Lid', seat_o, 0.022, 0.01, M('Teal', 'teal'), Frame((1.2, 0.422, -0.29), UPF), p)
    rbox('Tank', (0.42, 0.36, 0.17), por, Frame((1.2, 0.6, -0.6)), p, 0.03)
    lib.slab('TankLid', lib.rrect(0.45, 0.2, 0.03, 4), 0.03, 0.012, por, Frame((1.2, 0.78, -0.6), UPF), p)
    cyl('Flush', 0.022, 0.808, 0.818, M('Honey', 'honey'), Frame((1.2, 0, -0.6)), p)
    # Paper holder on the right wall, shelf with folded towels and a plant above.
    teal = M('Teal', 'teal')
    tube('PaperArm', [(XR, 0.72, -0.06), (XR - 0.07, 0.72, -0.06), (XR - 0.07, 0.72, 0.07)], 0.008, teal, p)
    paper = lathe('PaperRoll', [(0.018, -0.05), (0.055, -0.05), (0.058, -0.047), (0.058, 0.047), (0.055, 0.05),
                                (0.018, 0.05), (0.018, -0.05)], M('Paper', 'porcelain', 'fabric'),
                  Frame((XR - 0.07, 0.72, 0.01), (90, 0, 0)), p)
    paper.name = 'PaperRoll'
    lib.slab('Shelf', lib.rrect(0.52, 0.16, 0.02, 3), 0.025, 0.008, M('Honey', 'honey'), Frame((1.2, 1.34, ZB + 0.08), UPF), p)
    for x in (1.0, 1.4):
        rbox('ShelfBracket%d' % (x > 1.2), (0.02, 0.06, 0.1), teal, Frame((x, 1.31, ZB + 0.05)), p, 0.006)
    stack = [('peach', 0.0), ('sage', 0.0295), ('porcelain', 0.059)]
    for i, (col, dy) in enumerate(stack):
        m = tex_mat('Terry' + col, PAL[col], terry_tex('Terry' + col + 'Tex', PAL[col], seed=7 + i), 0.95)
        rbox('Folded%d' % i, (0.2, 0.03, 0.12), m, Frame((1.33, 1.381 + dy, ZB + 0.08), (0, 4 - 3 * i, 0)), p, 0.012)
    plant(Vector((1.07, 1.365, ZB + 0.08)), p, small=True)
    # Pedal bin.
    cyl('Bin', 0.11, 0.0, 0.27, teal, Frame((1.36, 0, 0.3)), p, seg=28, bevel=0.01)
    lib.sphere('BinLid', 0.112, M('Graphite', 'graphite', 'rubber'), Frame((1.36, 0.27, 0.3)), p, scale=(1, 0.18, 1), seg=28, rings=8)
    rbox('BinPedal', (0.07, 0.015, 0.05), M('Honey', 'honey'), Frame((1.36, 0.02, 0.18)), p, 0.005)


def bath_mat(parent):
    m = tex_mat('BathMat', PAL['honey'], bobble_tex('BobbleHoney', PAL['honey']), 0.95)
    o = lib.slab('BathMat', lib.rrect(0.7, 0.45, 0.06, 4), 0.014, 0.006, m, Frame((0, 0.0, 0.2), UPF), parent)
    _box_uv(o, 0.12)


def basket(parent):
    base = Vector((-1.27, 0, 2.3))
    parent = lib.empty('LaundryBasket', base, parent)
    m = tex_mat('Wicker', PAL['honey'], weave_tex('WeaveHoney', PAL['honey']), 0.8)
    b = lathe('Basket', [(0, 0.0), (0.15, 0.0), (0.16, 0.01), (0.19, 0.42), (0.2, 0.44), (0.185, 0.44), (0.175, 0.42),
                         (0.145, 0.03), (0, 0.03)], m, Frame(base), parent, seg=32)
    _box_uv(b, 0.12)
    tube('BasketRim', [(base.x + math.cos(a) * 0.195, 0.44, base.z + math.sin(a) * 0.195)
                       for a in [2 * math.pi * k / 24 for k in range(25)]], 0.012, M('Honey', 'honey'), parent, res=1)
    peach = tex_mat('TowelPeach', PAL['peach'], terry_tex('TerryPeach', PAL['peach']), 0.95)
    mb = meta('Laundry', 0.009)
    for c, semi in (((0, 0.42, 0), (0.16, 0.06, 0.16)), ((0.08, 0.46, -0.05), (0.09, 0.07, 0.08)),
                    ((-0.07, 0.47, 0.06), (0.08, 0.06, 0.09)), ((0.19, 0.36, -0.1), (0.035, 0.12, 0.07))):
        ell(mb, base + Vector(c), semi)
    l = adopt(solid('Laundry', [mb], 0.008, 1600, peach), parent, base + Vector((0, 0.42, 0)))
    _box_uv(l, 0.25)


def etagere(parent):
    """Honey shelf unit in the gap between the tub's head end and the back wall: towels, jars, a basket."""
    p = lib.empty('Etagere', (-1.28, 0, -0.55), parent)
    wood = M('Honey', 'honey', 'painted')
    x0, x1, z0, z1 = -1.53, -1.03, ZB + 0.005, -0.40
    for x in (x0 + 0.015, x1 - 0.015):
        for z in (z0 + 0.015, z1 - 0.015):
            rbox('Leg%d%d' % (x > -1.3, z > -0.55), (0.03, 1.4, 0.03), wood, Frame((x, 0.7, z)), p, 0.008)
    levels = (0.12, 0.52, 0.92, 1.32)
    for i, y in enumerate(levels):
        lib.slab('Board%d' % i, lib.rrect(x1 - x0, z1 - z0, 0.015, 2), 0.022, 0.007, wood,
                 Frame(((x0 + x1) / 2, y, (z0 + z1) / 2), UPF), p)
    cz = (z0 + z1) / 2
    for i, col in enumerate(('sage', 'porcelain', 'peach')):         # rolled towels on the second board
        m = tex_mat('Terry' + col, PAL[col], terry_tex('Terry' + col + 'Tex', PAL[col], seed=7 + i), 0.95)
        roll = lathe('Roll%d' % i, [(0, -0.12), (0.045, -0.12), (0.052, -0.113), (0.052, 0.113), (0.045, 0.12), (0, 0.12)],
                     m, Frame((x0 + 0.08 + i * 0.165, 0.542 + 0.052, cz), (90, 0, 0)), p, seg=20)
        _box_uv(roll, 0.15)
    m = tex_mat('Wicker', PAL['honey'], weave_tex('WeaveHoney', PAL['honey']), 0.8)
    bk = rbox('ShelfBasket', (0.4, 0.16, 0.24), m, Frame(((x0 + x1) / 2, 0.142 + 0.08, cz)), p, 0.015)
    _box_uv(bk, 0.12)
    for i, (dx, col, h) in enumerate(((-0.15, 'clay', 0.12), (-0.04, 'cream', 0.09), (0.08, 'teal', 0.14))):
        b = Frame(((x0 + x1) / 2 + dx, 0.942, cz))
        lathe('Jar%d' % i, [(0, 0), (0.035, 0), (0.038, 0.006), (0.038, h - 0.01), (0.03, h), (0, h)],
              M('Jar' + col, col, 'ceramic'), b, p, seg=20)
    plant(Vector(((x0 + x1) / 2, 1.342, cz)), p)


def towel_bar(parent):
    parent = lib.empty('TowelBar', TOWEL_BAR, parent)
    teal = M('Teal', 'teal')
    b = TOWEL_BAR
    tube('Rail', [(b.x - 0.24, b.y, b.z), (b.x + 0.24, b.y, b.z)], 0.011, teal, parent, res=2)
    for x in (b.x - 0.24, b.x + 0.24):
        tube('TowelPost%d' % (x > b.x), [(x, b.y, ZB), (x, b.y, b.z)], 0.012, teal, parent, res=2)
        lib.sphere('TowelRose%d' % (x > b.x), 0.024, teal, Frame((x, b.y, ZB + 0.002)), parent, scale=(1, 1, 0.25), seg=16, rings=6)


# --- props ---------------------------------------------------------------------------------------------------

def prop_root(pid):
    return lib.empty(pid, PROPS[pid], None)


def p_cup():
    r = prop_root('cup')
    m = M('CupTeal', 'teal', 'ceramic')
    lathe('Cup', [(0, 0), (0.031, 0), (0.034, 0.004), (0.038, 0.105), (0.036, 0.108), (0.032, 0.106), (0.029, 0.012),
                  (0, 0.012)], m, Frame(PROPS['cup']), r, seg=28)
    return r, {'lying_half_thickness': 0.038, 'height': 0.108}


def p_lotion():
    r = prop_root('lotion')
    base = Vector(PROPS['lotion'])
    rbox('Bottle', (0.062, 0.11, 0.062), M('Honey', 'honey', 'ceramic'), Frame(base + Vector((0, 0.055, 0))), r, 0.016)
    teal = M('Teal', 'teal')
    cyl('Collar', 0.016, 0.106, 0.122, teal, Frame(base), r, seg=16)
    cyl('Stem', 0.006, 0.12, 0.15, teal, Frame(base), r, seg=10)
    rbox('Pump', (0.03, 0.016, 0.03), teal, Frame(base + Vector((0, 0.155, 0))), r, 0.006)
    tube('Nozzle', [base + Vector((0, 0.158, -0.01)), base + Vector((0, 0.158, -0.04)), base + Vector((0, 0.15, -0.048))],
         0.0045, teal, r, res=4)
    return r, {'lying_half_thickness': 0.031, 'height': 0.166}


def p_soap():
    r = prop_root('soap')
    base = Vector(PROPS['soap'])
    lib.slab('Dish', lib.rrect(0.12, 0.085, 0.03, 4), 0.012, 0.005, M('DishCeramic', 'cream', 'ceramic'), Frame(base, UPF), r)
    rbox('Bar', (0.08, 0.028, 0.055), M('SoapClay', 'clay', 'paste'), Frame(base + Vector((0, 0.026, 0))), r, 0.012)
    return r, {'lying_half_thickness': 0.02, 'height': 0.04}


def p_toothpaste():
    r = prop_root('toothpaste')
    base = Vector(PROPS['toothpaste'])
    tube_n = lib.empty('Tube', base, r)
    por = M('TubeWhite', 'porcelain', 'painted')
    teal = M('Teal', 'teal')
    rings = []
    xs = [-0.08 + 0.16 * k / 12 for k in range(13)]
    for x in xs:
        t = (x + 0.08) / 0.16                                       # 0 crimp .. 1 shoulder
        wz = 0.028 - 0.009 * t
        hy = 0.004 + 0.015 * min(1, t * 1.6) ** 0.7
        rings.append([base + Vector((x, math.sin(a) * hy, math.cos(a) * wz)) for a in [2 * math.pi * k / 20 for k in range(20)]])
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in rg] for rg in rings]
    for k, (a, b) in enumerate(zip(vs, vs[1:])):
        for i in range(20):
            f = bm.faces.new((a[i], a[(i + 1) % 20], b[(i + 1) % 20], b[i]))
            f.material_index = 1 if 4 <= k <= 8 else 0
    for ring_, flip in ((vs[0], True), (vs[-1], False)):
        f = bm.faces.new(ring_[::-1] if flip else ring_)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    lib.from_bmesh('TubeBody', bm, [por, teal], tube_n, base)
    rbox('Crimp', (0.012, 0.01, 0.058), por, Frame(base + Vector((-0.083, 0, 0))), tube_n, 0.003)
    cap_n = lib.empty('Cap', base + Vector((0.09, 0, 0)), tube_n)
    lathe('CapMesh', [(0, -0.012), (0.015, -0.012), (0.016, -0.01), (0.016, 0.011), (0.014, 0.013), (0, 0.013)], teal,
          Frame(base + Vector((0.09, 0, 0)), (0, 0, -90)), cap_n, seg=18)
    paste = M('Paste', 'porcelain', 'paste')
    glob = lib.empty('Glob', base + Vector((0.11, 0.01, 0)), r)
    mb = meta('Glob', 0.002)
    g = base + Vector((0.11, 0.01, 0))
    ball(mb, g, 0.016)
    ball(mb, g + Vector((0.006, 0.009, 0.002)), 0.011)
    ball(mb, g + Vector((0.009, 0.016, -0.001)), 0.006)
    adopt(solid('GlobMesh', [mb], 0.002, 500, paste), glob, g)
    splats = lib.empty('Splats', base, r)
    for i, (off, sc) in enumerate((((0.45, 0.76, -0.258), (1, 0.8)), ((0.18, 0.6, -0.258), (1.3, 1.0)),
                                   ((0.35, 0.88, -0.258), (0.8, 1.2)))):
        c = base + Vector(off)
        sp = lib.empty('Splat%d' % (i + 1), c, splats)
        mb = meta('Splat%d' % i, 0.003)
        rng = np.random.default_rng(10 + i)
        ell(mb, c + Vector((0, 0, 0.002)), (0.03 * sc[0], 0.026 * sc[1], 0.004))
        for k in range(5):
            a = rng.random() * 2 * math.pi
            d = 0.025 + rng.random() * 0.012
            ell(mb, c + Vector((math.cos(a) * d * sc[0], math.sin(a) * d * sc[1], 0.002)), (0.009, 0.009, 0.003))
        adopt(solid('SplatMesh%d' % (i + 1), [mb], 0.0025, 500, paste), sp, c)
    return r, {}


def p_smudge():
    r = prop_root('smudge')
    m = lib.mat('Smudge', '#CBB8A8', 0.9)
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Alpha'].default_value = 0.35
    m.surface_render_method = 'BLENDED'
    c = Vector(PROPS['smudge'])
    rng = np.random.default_rng(4)
    outline = []
    for k in range(28):
        a = 2 * math.pi * k / 28
        rr = 1 + 0.18 * math.sin(3 * a + 1) + 0.1 * rng.random()
        outline.append((math.cos(a) * 0.1 * rr, math.sin(a) * 0.115 * rr))
    bm = bmesh.new()
    cv = bm.verts.new(c)
    vs = [bm.verts.new(c + Vector((x, y, 0))) for x, y in outline]
    for k in range(28):
        bm.faces.new((cv, vs[k], vs[(k + 1) % 28]))
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    if bm.faces[0].normal.z < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    lib.from_bmesh('Smear', bm, m, r, c, smooth=False)
    return r, {}


def water_mat():
    m = lib.mat('Water', WATER, 0.1)
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Alpha'].default_value = 0.85
    m.surface_render_method = 'BLENDED'
    return m


def p_faucet():
    r = prop_root('faucet')
    o = Vector(PROPS['faucet'])
    steel = M('Steel', STEEL, 0.4, metal=0.75)
    base = lib.empty('Base', o, r)
    cyl('Deck', 0.04, -0.08, -0.07, steel, Frame(o), base, seg=24)
    cyl('Column', 0.022, -0.075, 0.075, steel, Frame(o), base, seg=20)
    for s in (-1, 1):
        hf = Frame(o + Vector((s * 0.085, 0, 0)))
        cyl('HandleBase%d' % (s > 0), 0.019, -0.08, -0.045, steel, hf, base, seg=16)
        tube('Lever%d' % (s > 0), [hf.at((0, -0.05, 0.0)), hf.at((0, -0.036, -0.03)), hf.at((0, -0.028, -0.05))],
             0.0065, steel, base, res=4)
        lib.sphere('LeverTip%d' % (s > 0), 0.009, steel, hf.child((0, -0.028, -0.05)), base, seg=12, rings=6)
    sp = lib.empty('Spout', o + Vector((0, 0.07, 0.05)), r)
    q = o + Vector((0, 0.07, 0.05))
    tube('SpoutArc', [q + Vector((0, -0.005, -0.05)), q + Vector((0, 0.035, -0.04)), q + Vector((0, 0.04, 0.04)),
                      q + Vector((0, 0.005, 0.1))], 0.014, steel, sp, res=10)
    water = water_mat()
    st = lib.empty('Stream', o + Vector((0, -0.32, 0.42)), r)
    godot_rot(st, (-38.5, 0, 0))                                     # the game's node; the arc is in world space
    arc = [o + Vector(v) for v in ((0, 0.07, 0.10), (0, 0.11, 0.24), (0, 0.05, 0.42), (0.02, -0.25, 0.66), (0.08, -0.9, 0.86))]
    sweep('StreamMesh', arc, lambda t: 0.011 + 0.014 * t + 0.003 * math.sin(t * 30), water, st)
    pu = lib.empty('Puddle', o + Vector((0.1, -0.94, 0.9)), r)
    pc = o + Vector((0.1, -0.94, 0.9))
    rng = np.random.default_rng(8)
    outline = [(math.cos(a) * 0.45 * (1 + 0.12 * math.sin(4 * a) + 0.06 * rng.random()),
                math.sin(a) * 0.4 * (1 + 0.1 * math.cos(3 * a))) for a in [2 * math.pi * k / 40 for k in range(40)]]
    bm = bmesh.new()                                               # drapes over the bath mat (MAT_RECT)
    rings_ = []
    for k in range(7):
        t = k / 6
        rings_.append([bm.verts.new(_drape(pc + Vector((x * t, 0, -y * t)))) for x, y in outline] if k else
                      [bm.verts.new(_drape(pc))])
    n = len(outline)
    for i in range(n):
        bm.faces.new((rings_[0][0], rings_[1][(i + 1) % n], rings_[1][i]))
    for k in range(1, 6):
        for i in range(n):
            bm.faces.new((rings_[k][i], rings_[k][(i + 1) % n], rings_[k + 1][(i + 1) % n], rings_[k + 1][i]))
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    lib.from_bmesh('PuddleMesh', bm, water, pu, pc)
    return r, {}


MAT_RECT = [-0.35, 0.35, -0.025, 0.425]          # bath mat x0, x1, z0, z1 (top at y 0.014)


def _drape(p):
    """Puddle height: a film on the floor, lifted onto the mat with a soft edge."""
    x0, x1, z0, z1 = MAT_RECT
    e = min(p.x - x0, x1 - p.x, p.z - z0, z1 - p.z)
    lift = 0.0155 * max(0.0, min(1.0, (e + 0.06) / 0.04))          # full height 2 cm before the mat edge
    return Vector((p.x, 0.0018 + lift, p.z))


def p_tub():
    r = prop_root('tub')
    o = Vector(PROPS['tub'])
    water = water_mat()
    w = lib.empty('Water', o, r)
    lib.slab('WaterMesh', lib.rrect(0.6, 1.47, 0.19, 6), 0.01, 0.004, water, Frame(o + Vector((0, -0.01, 0)), UPF), w)
    drops = lib.empty('Drops', o, r)
    for i, off in enumerate(((-0.2, 0.05, -0.4), (-0.1, 0.05, -0.2), (0, 0.05, 0), (0.1, 0.05, 0.2), (0.2, 0.05, 0.4),
                             (-0.2, 0.05, 0.6))):
        c = o + Vector(off)
        d = lib.empty('Drop%d' % i, c, drops)
        lathe('DropMesh%d' % i, [(0, 0.05), (0.008, 0.035), (0.022, 0.012), (0.026, -0.004), (0.02, -0.02), (0, -0.026)],
              water, Frame(c), d, seg=14)
    return r, {}


def p_towel():
    """Peach terry towel folded over the bar; pivot = node position (about its centre)."""
    r = prop_root('towel')
    b = TOWEL_BAR
    m = tex_mat('TowelPeach', PAL['peach'], terry_tex('TerryPeach', PAL['peach']), 0.95)
    stripe = tex_mat('TowelStripe', '#F6D9CB', terry_tex('TerryStripe', '#F6D9CB', seed=9), 0.95)
    rb = 0.011 + 0.008
    prof = [(1.0, b.z - 0.022)]
    prof += [(b.y - 0.02 - (b.y - 0.02 - 1.0) * (1 - k / 6), b.z - 0.022 + 0.002 * k / 6) for k in range(1, 7)]
    for k in range(9):                                               # over the bar
        a = math.pi * k / 8
        prof.append((b.y + math.sin(a) * rb, b.z - math.cos(a) * rb))
    prof += [(b.y - (b.y - 0.96) * k / 8, b.z + rb + 0.004 * k / 8) for k in range(1, 9)]
    prof = [(y, z) for y, z in prof]
    n = len(prof)

    def band(i):                                                      # stripes near the bottom of the front panel
        y = prof[i][0]
        return 1 if (i > n - 9 and 1.03 < y < 1.07) or (i > n - 9 and 1.09 < y < 1.105) else 0
    o = ribbon('Towel', prof, b.x - 0.2, b.x + 0.2, 0.014, [m, stripe], r, nx=12, wave=0.003, split=band)
    _box_uv(o, 0.2)
    return r, {'lying_half_thickness': 0.015, 'bar': list(b), 'hangs_from': 'TowelBar (room)'}


PROP_BUILDERS = [p_cup, p_lotion, p_soap, p_toothpaste, p_smudge, p_faucet, p_tub, p_towel]


# --- export ---------------------------------------------------------------------------------------------------

def tris(root):
    t = 0
    for o in [root, *root.children_recursive]:
        if o.type == 'MESH':
            o.data.calc_loop_triangles()
            t += len(o.data.loop_triangles)
    return t


def export(root, path, at_origin):
    if at_origin:
        root.matrix_world = Matrix.Identity(4)                      # prop root = its pivot
    bpy.context.view_layer.update()
    for o in bpy.data.objects:                                      # props: children only, so the named parts are
        o.select_set((o == root and not at_origin) or o in root.children_recursive)    # direct children of the scene root
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, use_selection=True,
                              export_cameras=False, export_lights=False, export_image_format='AUTO')


def scene_file(path, glb_name, node_name):
    with open(path, 'w') as f:
        f.write('[gd_scene format=3]\n\n[ext_resource type="PackedScene" path="res://bathroom/art/%s" id="1"]\n\n'
                '[node name="%s" instance=ExtResource("1")]\n' % (glb_name, node_name))


def main():
    out = os.path.join(lib.ROOT, 'bathroom', 'art')
    os.makedirs(os.path.join(out, 'props'), exist_ok=True)
    lib.reset()
    root = lib.empty('Human_Room', (0, 0, 0))
    room(root)
    vanity(root)
    mirror_frame(root)
    tub(root)
    toilet(root)
    bath_mat(root)
    basket(root)
    etagere(root)
    towel_bar(root)
    root.name = 'BathroomRoom'
    manifest = {'asset_id': 'bathroom_v1', 'style_id': 'warm_ceramic_v1', 'date': '2026-10-15',
                'style_deviations': ['water %s alpha 0.85' % WATER, 'faucet brushed nickel %s' % STEEL,
                                     'plant leaves #6E8F5E (Kenney Furniture Kit plantSmall1/2, CC0)',
                                     'window sky %s emissive' % SKY, 'rubber duck #E8B84C'],
                'room': {'tris': tris(root), 'file': 'bathroom_room.glb'}, 'props': {}}
    room_objs = {root, *root.children_recursive}
    for build in PROP_BUILDERS:
        r, info = build()
        info.update(node_position=list(PROPS[r.name]), tris=tris(r), file='props/%s.glb' % r.name)
        manifest['props'][r.name] = info
    layout = {'props': {k: list(v) for k, v in PROPS.items()}, 'towel_bar': list(TOWEL_BAR),
              'lamp': [0, H, 0.4], 'mirror_glass': {'center': [0, 1.58, -0.665], 'size': [0.74, 0.6]}}
    os.makedirs(os.path.join(lib.ROOT, 'source', 'bathroom'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(lib.ROOT, 'source', 'bathroom', 'bathroom.blend'))
    export(root, os.path.join(out, 'bathroom_room.glb'), False)
    scene_file(os.path.join(out, 'bathroom_room.tscn'), 'bathroom_room.glb', 'BathroomRoom')
    for pid in PROPS:
        r = bpy.data.objects[pid]
        export(r, os.path.join(out, 'props', pid + '.glb'), True)
        scene_file(os.path.join(out, 'props', pid + '.tscn'), 'props/%s.glb' % pid, pid.title() + 'Art')
    with open(os.path.join(out, 'layout.json'), 'w') as f:
        json.dump(layout, f, indent=1)
    with open(os.path.join(out, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)
    print('BATHROOM_BUILT room tris=%d props=%s' % (manifest['room']['tris'],
                                                    {k: v['tris'] for k, v in manifest['props'].items()}))


main()
