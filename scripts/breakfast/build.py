"""E01 kitchen ("Breakfast Call") set + props, warm_ceramic_v1 (art_direction.md "E01 kitchen + props").
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/breakfast/build.py
Layout = the gated mock (previews/kitchen/kitchen_mock.gd) on mechanics' footprint (game locations/breakfast).
Writes breakfast/art/breakfast_room.glb (static set at identity), breakfast/art/props/<id>.glb (root = prop pivot,
children named as the game scripts expect), layout.json and manifest.json. Contract: interfaces.md "Breakfast".
Godot coords: +Y up, Bernard at the origin facing the counter (-Z). Every material is matte (roughness >= 0.6).
"""
import importlib.util
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'cockpit_v2'))
import lib  # noqa: E402
import ink  # noqa: E402
from lib import Frame, UPF  # noqa: E402
from sculpt import meta, ell, ball, solid  # noqa: E402

_spec = importlib.util.spec_from_file_location('bathroom_build', os.path.join(HERE, '..', 'bathroom', 'build.py'))
BH = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BH)                    # helpers only (its main() is guarded)
quad_grid, wall_rects, lathe, rbox, cyl, tube, sweep, tile_tex, weave_tex, tex_mat, _rgb, _normal_from = (
    BH.quad_grid, BH.wall_rects, BH.lathe, BH.rbox, BH.cyl, BH.tube, BH.sweep, BH.tile_tex, BH.weave_tex,
    BH.tex_mat, BH._rgb, BH._normal_from)

PAL = BH.PAL
PROF = {'painted': 0.7, 'ceramic': 0.62, 'fabric': 0.9, 'wood': 0.75, 'rubber': 0.86, 'paper': 0.92}
TERRACOTTA = '#D08A66'        # deviation: floor checker terracotta (AD "warm terracotta/cream checker")
CARD = '#C49A6C'              # deviation: parcel cardboard tan
FRAGILE_RED = '#C0583F'       # deviation: clay-red FRAGILE tape
COFFEE = '#5A3218'            # deviation: coffee
TOASTY = '#E2B062'            # deviation: toast face (golden); crust is honey
LEAF = '#6E8F5E'              # deviation: plant green (as the bathroom)
COAT = '#6E86A6'              # deviation: slate coat in the hall
WOOD = '#B98A62'              # deviation: hall floor planks (honey-brown, away from the hoodie's yellow)
HONEY_WOOD = '#C9925A'        # deviation: furniture honey wood, warmer/darker than palette honey (AD: no big yellow areas)

# Room inner faces (mechanics' walls are 10 cm thick, centred on x +-2.05, z -1.15 / 2.55).
XL, XR, ZB, ZF, H = -2.0, 2.0, -1.10, 2.50, 2.6
DOORWAY = (0.35, 1.25, 2.1)                    # left-wall opening to the hall: z range, height
WINDOW = (1.0, 2.0, 1.0, 2.0)                  # right wall: z range, y range
HALL = (-5.0, -2.0, 0.30, 1.30, 2.5)           # x0, x1, z0, z1, ceiling
DADO = 0.9
COUNTER = (-1.45, 0.75, 0.92)                  # cabinet run x range (back wall), worktop height
UPPER = (1.45, 2.15)
SEAT = Vector((1.79, 0.0, -0.92))              # roommate's Hips (sit_table), yaw 130: faces Bernard
SEAT_YAW = 130.0
TABLE = Vector((1.41, 0.0, -0.60))             # round table centre; top r 0.38 at 0.755
TABLE_R, TABLE_TOP = 0.38, 0.755
NOOK_Y = 0.47                                  # seat cushion top
CLOCK = (7, 30)                                # wall clock time (hours, minutes)
HINGE = (-4.975, 0.0, 1.25)                    # front door: hinge on the hall-side face of the end wall
PROPS = {   # id: node position (game); base pivots on the worktop (0.92) unless noted
    'coffee_machine': (-0.3, 0.92, -0.85), 'mug': (-0.3, 0.92, -0.66), 'phone': (0.08, 0.9245, -0.64),
    'toaster': (0.42, 0.92, -0.82), 'toast': (0.42, 1.05, -0.855), 'toast_2': (0.42, 1.05, -0.785),
    'parcel': (1.86, NOOK_Y, -0.36), 'front_door': HINGE,      # parcel on the nook seat at his left
}
PROP_YAW = {'parcel': -80.0}                   # long FRAGILE side toward Bernard


def M(name, key, profile='painted', **kw):
    r = PROF.get(profile, profile) if isinstance(profile, str) else profile
    return lib.mat(name, PAL.get(key, key), max(r, 0.6), **kw)


def facing():
    a = math.radians(SEAT_YAW)
    f = Vector((-math.sin(a), 0, -math.cos(a)))
    return f, Vector((f.z, 0, -f.x))             # forward, his left


# --- textures --------------------------------------------------------------------------------------------

def checker_tex(name, a, b, px=256, gw=0.03):
    y, x = np.mgrid[0:px, 0:px].astype(float) / px * 2
    fx, fy = x % 1, y % 1
    d = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy))
    inside = np.clip((d - gw / 2) / 0.03, 0, 1)
    which = ((np.floor(x) + np.floor(y)) % 2)[..., None]
    rng = np.random.default_rng(4)
    n = 1 + ink.blur(rng.normal(0, 0.03, (px, px)), 3)[..., None]
    col = (_rgb(a) * (1 - which) + _rgb(b) * which) * n
    col = col * inside[..., None] + _rgb('#CDBFA6') * (1 - inside[..., None])
    return (lib.image_from_array(name, np.clip(col, 0, 1)),
            lib.image_from_array(name + 'N', _normal_from(np.sqrt(inside), 1.2), non_color=True))


def plank_tex(name, base, n=4, px=256, seed=7):
    """n planks across, grain streaks along X, dark seams."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:px, 0:px].astype(float) / px
    row = np.floor(y * n)
    shade = rng.normal(0, 0.05, n)[row.astype(int)]
    grain = ink.blur(rng.normal(0, 1, (px, px)), 1)
    grain = np.roll(ink.blur(np.repeat(grain[:, :1], px, 1), 2), 0, 1) * 0.04 + np.sin(x * 40 + row * 3) * 0.015
    seam = np.clip(np.abs((y * n) % 1 - 0.5) * 2 - 0.94, 0, 1) / 0.06
    col = _rgb(base)[None, None] * (1 + shade[..., None] + grain[..., None]) * (1 - 0.35 * seam[..., None])
    return (lib.image_from_array(name, np.clip(col, 0, 1)),
            lib.image_from_array(name + 'N', _normal_from(1 - seam, 1.0), non_color=True))


def rug_tex(name, px=256):
    """Cream field, peach/terracotta bands, weave bumps."""
    y, x = np.mgrid[0:px, 0:px].astype(float) / px
    col = np.ones((px, px, 3)) * _rgb(PAL['cream'])
    for v0, v1, c in ((0.0, 0.08, TERRACOTTA), (0.92, 1.0, TERRACOTTA), (0.16, 0.2, PAL['peach']),
                      (0.8, 0.84, PAL['peach']), (0.47, 0.53, PAL['clay'])):
        m = ((y >= v0) & (y < v1))[..., None]
        col = np.where(m, _rgb(c), col)
    yy, xx = y * 48, x * 48
    over = ((np.floor(xx) + np.floor(yy)) % 2)
    hgt = np.where(over > 0, np.abs(np.sin(np.pi * (yy % 1))), np.abs(np.sin(np.pi * (xx % 1)))) ** 0.5
    col = col * (0.82 + 0.22 * hgt[..., None])
    return (lib.image_from_array(name, np.clip(col, 0, 1)),
            lib.image_from_array(name + 'N', _normal_from(hgt, 1.5), non_color=True))


def window_glow(px=256):
    """Warm morning glow, brighter at the top, soft frost mottling (no blown white)."""
    c = ink.Canvas(px, px, '#E3C79A')
    rng = np.random.default_rng(12)
    mott = ink.blur(rng.normal(0, 1, (px, px)), 6)
    v = np.linspace(1.04, 0.9, px)[:, None]
    c.multiply(v * (1 + 0.035 * mott / (mott.std() + 1e-6)))
    for k in range(5):                                       # faint tree-shadow blobs through the frost
        c.ellipse((rng.uniform(0.1, 0.9), rng.uniform(0.55, 0.9)), rng.uniform(0.08, 0.14), rng.uniform(0.06, 0.1),
                  '#C9AE84', opacity=0.35, soft=20)
    return c


def amber_pane(px=128):
    """Front-door pane: amber frosted glass (~70% value) with a diamond lattice."""
    c = ink.Canvas(px, int(px * 0.42 / 0.36), '#B98D52')
    rng = np.random.default_rng(13)
    c.multiply(1 + 0.05 * ink.blur(rng.normal(0, 1, (c.h, c.w)), 3))
    for k in range(-4, 9):
        u = k / 4
        c.stroke([(u, 0), (u + 1, 1)], 3, '#D9B477', 0.8)
        c.stroke([(u, 1), (u + 1, 0)], 3, '#D9B477', 0.8)
    return c


def canvas_mat(name, c, rough=0.9, emit=0.0):
    img = lib.image_from_array(name + 'Tex', c.image())
    if emit:
        return lib.mat(name, '#ffffff', rough, image=img, emit_image=img, strength=emit)
    return lib.mat(name, '#ffffff', rough, image=img)


def uv_quad(name, frame, w, h, mat, parent, u=(0, 1), v=(0, 1)):
    """Centred w x h quad in frame XY facing +Z, UV 0..1 (u right, v up)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    vs = [bm.verts.new(frame.at((x * w / 2, y * h / 2, 0))) for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs)
    for l, (uu, vv) in zip(f.loops, ((u[0], v[0]), (u[1], v[0]), (u[1], v[1]), (u[0], v[1]))):
        l[uvl].uv = (uu, vv)
    return lib.from_bmesh(name, bm, mat, parent, smooth=False)


def uv_disc(name, frame, r, mat, parent, n=48):
    """Round face in frame XY facing +Z, UV mapped from the unit square (a round canvas shows whole)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    c = bm.verts.new(frame.at((0, 0, 0)))
    ring = [bm.verts.new(frame.at((math.cos(2 * math.pi * k / n) * r, math.sin(2 * math.pi * k / n) * r, 0)))
            for k in range(n)]
    for k in range(n):
        f = bm.faces.new((c, ring[k], ring[(k + 1) % n]))
        for l, v in zip(f.loops, (None, k, (k + 1) % n)):
            a = 2 * math.pi * v / n if v is not None else 0
            l[uvl].uv = (0.5, 0.5) if v is None else (0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a))
    return lib.from_bmesh(name, bm, mat, parent, smooth=False)


# --- room shell ---------------------------------------------------------------------------------------------

WALLS = {   # name: (frame at the inner face's left-bottom corner, width, holes (x0, x1, y0, y1))
    'Back': (Frame((XL, 0, ZB)), XR - XL, []),
    'Left': (Frame((XL, 0, ZF), (0, 90, 0)), ZF - ZB, [(ZF - DOORWAY[1], ZF - DOORWAY[0], 0.0, DOORWAY[2])]),
    'Right': (Frame((XR, 0, ZB), (0, -90, 0)), ZF - ZB, [(WINDOW[0] - ZB, WINDOW[1] - ZB, WINDOW[2], WINDOW[3])]),
    'Front': (Frame((XR, 0, ZF), (0, 180, 0)), XR - XL, []),
}


def shell(root):
    p = lib.empty('Shell', (0, 0, 0), root)
    floor = tex_mat('FloorChecker', PAL['cream'], checker_tex('FloorCheckerTex', PAL['cream'], TERRACOTTA), 0.7)
    paint = M('WallPaint', 'cream', 0.85)
    skirt = M('Skirting', 'porcelain', 'painted')
    quad_grid('Floor', Frame((XL, 0, ZF), (-90, 0, 0)), 0, XR - XL, 0, ZF - ZB, floor, p, tile=0.8, nx=5, ny=5)
    quad_grid('Ceiling', Frame((XL, H, ZB), (90, 0, 0)), 0, XR - XL, 0, ZF - ZB, paint, p, nx=2, ny=2)
    for name, (f, w, holes) in WALLS.items():
        for i, (a, b, y0, y1) in enumerate(wall_rects(w, 0, H, holes)):
            quad_grid('%sPaint%d' % (name, i), f, a, b, y0, y1, paint, p)
        spans = [(0.0, w)]
        if name == 'Left':
            spans = [(0.0, holes[0][0]), (holes[0][1], w)]
        for k, (a, b) in enumerate(spans):
            rbox('%sSkirt%d' % (name, k), (b - a, 0.08, 0.016), skirt, f.child(((a + b) / 2, 0.04, 0.008)), p, 0.004)
    # backsplash: square peach tiles between the worktop and the uppers
    tiles = tex_mat('Splash', PAL['peach'], tile_tex('SplashTex', PAL['peach'], '#F3E2D2', n=4, gw=0.06, seed=3), 0.7)
    x0, x1, top = COUNTER
    quad_grid('Backsplash', Frame((x0, top, ZB + 0.004)), 0, x1 - x0, 0, UPPER[0] - top, tiles, p, tile=0.6)
    doorway(p)
    window(p)
    lamps(p)


def doorway(p):
    """Casing around the hall opening (both faces) and its lining."""
    casing = M('Casing', 'porcelain', 'painted')
    z0, z1, h = DOORWAY
    for side, x in (('Kitchen', XL + 0.001), ('Hall', XL - 0.1 - 0.001)):
        f = Frame((x, 0, (z0 + z1) / 2), (0, 90 if side == 'Kitchen' else -90, 0))
        ring = [(xx, yy + (h + 0.07) / 2) for xx, yy in lib.rrect(z1 - z0 + 0.14, h + 0.07, 0.02, 2)]
        hole = [(xx, yy + h / 2 - 0.02) for xx, yy in lib.rrect(z1 - z0, h + 0.04, 0.005, 1)][::-1]
        lib.slab('DoorCasing' + side, ring, 0.02, 0.007, casing, f, p, holes=[hole])
    for name, a, b in (('L', (XL, 0, z0), (XL - 0.1, h, z0)), ('R', (XL, 0, z1), (XL - 0.1, h, z1))):
        rbox('Lining' + name, (0.1, h, 0.012), casing, Frame(((a[0] + b[0]) / 2, h / 2, a[2])), p, 0.003)
    rbox('LiningTop', (0.1, 0.012, z1 - z0), casing, Frame((XL - 0.05, h, (z0 + z1) / 2)), p, 0.003)


def window(p):
    f, w, holes = WALLS['Right']
    x0, x1, y0, y1 = holes[0]
    paint = M('Casing', 'porcelain', 'painted')
    depth = 0.12
    for name, a, b in (('L', (x0, y0), (x0, y1)), ('R', (x1, y1), (x1, y0)), ('T', (x0, y1), (x1, y1)),
                       ('B', (x1, y0), (x0, y0))):
        bm = bmesh.new()
        vs = [bm.verts.new(v) for v in (f.at((a[0], a[1], 0)), f.at((b[0], b[1], 0)), f.at((b[0], b[1], -depth)),
                                         f.at((a[0], a[1], -depth)))]
        bm.faces.new(vs)
        bm.normal_update()
        bm.faces.ensure_lookup_table()
        cen = f.at(((x0 + x1) / 2, (y0 + y1) / 2, -depth / 2))
        if bm.faces[0].normal.dot(cen - bm.faces[0].calc_center_median()) < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
        lib.from_bmesh('Reveal' + name, bm, paint, p, smooth=False)
    sky = canvas_mat('WindowGlow', window_glow(), rough=0.9, emit=0.75)         # warm frosted pane, ~85% value
    uv_quad('WindowSky', f.child(((x0 + x1) / 2, (y0 + y1) / 2, -0.09)), x1 - x0, y1 - y0, sky, p)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ring = [(x + cx, y + cy) for x, y in lib.rrect(x1 - x0 + 0.1, y1 - y0 + 0.1, 0.015, 2)]
    hole = [(x + cx, y + cy) for x, y in lib.rrect(x1 - x0 - 0.04, y1 - y0 - 0.04, 0.004, 1)][::-1]
    lib.slab('WindowCasing', ring, 0.02, 0.007, paint, f.child((0, 0, 0)), p, holes=[hole])
    ff = f.child((0, 0, -0.1))
    rbox('MullionV', (0.035, y1 - y0, 0.03), paint, ff.child((cx, cy, 0.015)), p, 0.006)
    rbox('MullionH', (x1 - x0, 0.035, 0.03), paint, ff.child((cx, cy, 0.015)), p, 0.006)
    lib.slab('Sill', lib.rrect(0.16, x1 - x0 + 0.16, 0.02, 3), 0.03, 0.01, M('SillCeramic', 'cream', 'ceramic'),
             Frame((XR - 0.04, y0 - 0.03, ZB + cx), UPF), p)
    BH.plant(Vector((XR - 0.06, y0, ZB + cx - 0.2)), p, small=True)
    # cafe curtain on a rod across the lower half (frosted look, no glass)
    rod = M('Rod', HONEY_WOOD, 'wood')
    tube('CurtainRod', [f.at((x0 - 0.04, cy, 0.03)), f.at((x1 + 0.04, cy, 0.03))], 0.008, rod, p, res=2)
    curtain = M('Curtain', 'porcelain', 'fabric')
    prof = [(cy - 0.01 - i * (cy - y0 - 0.03) / 8, 0.035 + 0.008 * math.sin(i)) for i in range(9)]
    for k, (a, b) in enumerate(((x0 + 0.02, cx - 0.04), (cx + 0.04, x1 - 0.02))):
        o = BH.ribbon('Curtain%d' % k, prof, a, b, 0.004, [curtain], p, nx=16, wave=0.012)
        bm = bmesh.new()
        bm.from_mesh(o.data)
        mw = o.matrix_world
        for v in bm.verts:                             # ribbon is built in world XY: map onto the wall frame
            g = lib.G(mw @ v.co)
            v.co = (mw.inverted() @ lib.B(f.at((g.x, g.y, g.z))))
        bm.to_mesh(o.data)
        bm.free()


def lamps(p):
    """Lamp meshes only (gameplay adds the lights at layout.json `lights`)."""
    glow = lib.mat('LampGlow', '#FFF3DC', 0.6, emit='#FFF3DC', strength=1.6)
    lib.sphere('LampDome', 0.2, glow, Frame((0, H, 0.6)), p, scale=(1, 0.45, 1), seg=32, rings=12)
    tube('LampRing', [(math.cos(a) * 0.198, H - 0.004, 0.6 + math.sin(a) * 0.198) for a in
                      [2 * math.pi * k / 24 for k in range(25)]], 0.009, M('Clay', 'clay'), p, res=1)
    # pendant over the table: cord + clay shade, warm bulb glow inside
    top, bottom = H, 1.82
    tube('PendantCord', [(TABLE.x, top, TABLE.z), (TABLE.x, bottom + 0.12, TABLE.z)], 0.004, M('Cord', 'graphite'), p,
         res=1)
    shade = lathe('PendantShade', [(0.02, 0.13), (0.035, 0.125), (0.09, 0.05), (0.13, 0.0), (0.125, -0.005),
                                   (0.085, 0.045), (0.03, 0.115), (0.0, 0.12)],
                  M('ClayShade', 'clay', 'ceramic'), Frame((TABLE.x, bottom, TABLE.z)), p, seg=32)
    lib.sphere('PendantBulb', 0.035, glow, Frame((TABLE.x, bottom + 0.03, TABLE.z)), p)


# --- kitchen furniture -------------------------------------------------------------------------------------------

def counter(root):
    p = lib.empty('Counter', (0, 0, 0), root)
    x0, x1, top = COUNTER
    teal = M('CabinetTeal', 'teal', 'painted')
    dark = M('Plinth', '#244A49', 'painted')
    knob = M('Knob', 'clay', 'ceramic')
    rbox('Carcass', (x1 - x0, top - 0.04 - 0.1, 0.56), teal, Frame(((x0 + x1) / 2, 0.1 + (top - 0.14) / 2, ZB + 0.28)),
         p, 0.01)
    rbox('PlinthKick', (x1 - x0 - 0.02, 0.1, 0.5), dark, Frame(((x0 + x1) / 2, 0.05, ZB + 0.25)), p, 0.004)
    n = 4
    w = (x1 - x0) / n
    for i in range(n):                                    # doors: slightly proud panels with a recessed field
        cx = x0 + w * (i + 0.5)
        fr = Frame((cx, 0.1 + (top - 0.14) / 2, ZB + 0.56))
        rbox('Door%d' % i, (w - 0.012, top - 0.16, 0.02), teal, fr.child((0, 0, 0.01)), p, 0.006)
        rbox('DoorField%d' % i, (w - 0.11, top - 0.3, 0.006), dark, fr.child((0, 0, 0.021)), p, 0.003)
        kx = cx + (w / 2 - 0.05) * (1 if i % 2 else -1)
        lib.sphere('Knob%d' % i, 0.016, knob, Frame((kx, top - 0.2, ZB + 0.6)), p, scale=(1, 1, 0.8), seg=16, rings=8)
    lib.slab('Worktop', lib.rrect(x1 - x0 + 0.04, 0.62, 0.012, 3), 0.04, 0.012, M('Worktop', '#F3E7D0', 0.7),
             Frame(((x0 + x1) / 2, top - 0.04, ZB + 0.3), UPF), p)
    cream = M('UpperCream', 'cream', 'painted')
    u0, u1 = UPPER
    rbox('Uppers', (x1 - x0, u1 - u0, 0.33), cream, Frame(((x0 + x1) / 2, (u0 + u1) / 2, ZB + 0.165)), p, 0.01)
    for i in range(n):
        cx = x0 + w * (i + 0.5)
        fr = Frame((cx, (u0 + u1) / 2, ZB + 0.33))
        rbox('UpperDoor%d' % i, (w - 0.012, u1 - u0 - 0.02, 0.02), cream, fr.child((0, 0, 0.01)), p, 0.006)
        kx = cx + (w / 2 - 0.05) * (1 if i % 2 else -1)
        lib.sphere('UpperKnob%d' % i, 0.014, knob, Frame((kx, u0 + 0.07, ZB + 0.365)), p, scale=(1, 1, 0.8), seg=16,
                   rings=8)
    rbox('UpperCrown', (x1 - x0 + 0.03, 0.03, 0.36), cream, Frame(((x0 + x1) / 2, u1 + 0.015, ZB + 0.18)), p, 0.008)
    # tea towel over door 1: peach with two clay stripes
    towel = M('TeaTowel', 'peach', 'fabric')
    stripe = M('TeaStripe', 'clay', 'fabric')
    prof = [(0.66 - k * 0.04, ZB + 0.574 + 0.004 * math.sin(k)) for k in range(10)]
    BH.ribbon('TeaTowel', prof, -0.98, -0.76, 0.004, [towel, stripe], p, nx=8, wave=0.003,
              split=lambda i: 1 if i in (6, 7) else 0)
    fridge(p)
    clutter(p)


def fridge(p):
    x0, x1, z0, z1, h = -1.99, -1.47, -1.08, -0.42, 1.85
    body = M('Fridge', 'cream', 'painted')
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    rbox('FridgeBody', (x1 - x0, h, z1 - z0 - 0.03), body, Frame((cx, h / 2, cz - 0.015)), p, 0.04)
    for name, y0, y1 in (('Freezer', 1.27, h - 0.01), ('Main', 0.03, 1.25)):
        rbox('FridgeDoor' + name, (x1 - x0 - 0.01, y1 - y0, 0.035), body, Frame((cx, (y0 + y1) / 2, z1 - 0.018)), p,
             0.02)
    hand = M('FridgeHandle', 'graphite', 'rubber')
    for y0, y1 in ((1.33, 1.55), (0.85, 1.2)):
        rbox('FridgeHandle%.0f' % (y0 * 100), (0.025, y1 - y0, 0.03), hand, Frame((x1 - 0.05, (y0 + y1) / 2, z1 + 0.02)),
             p, 0.01)
    for i, (x, y, c) in enumerate(((-1.9, 1.62, 'clay'), (-1.66, 1.7, 'teal'), (-1.82, 1.06, 'peach'),
                                   (-1.6, 0.95, 'honey'))):
        lib.sphere('Magnet%d' % i, 0.022, M('Magnet' + c, c, 'ceramic'), Frame((x, y, z1 + 0.003)), p,
                   scale=(1, 1, 0.45), seg=16, rings=8)
    c = ink.paper(120, 168, PAL['porcelain'], seed=11)
    ink.text(c, 'TODAY', (0.5, 0.86), 0.12, '#3A4A5A', weight=1)
    ink.ruled(c, 0.12, top=0.72, bottom=0.08)
    ink.text(c, 'milk', (0.32, 0.62), 0.1, '#3A4A5A')
    ink.text(c, 'call mom', (0.46, 0.5), 0.1, '#3A4A5A')
    ink.tick(c, (0.8, 0.62), 0.07, '#3A4A5A')
    uv_quad('Notepad', Frame((-1.76, 1.3, z1 + 0.004)), 0.12, 0.168, canvas_mat('Notepad', c), p)


def clutter(p):
    top = COUNTER[2]
    clay = M('KettleClay', 'clay', 'ceramic')
    lathe('Kettle', [(0, 0), (0.075, 0), (0.085, 0.02), (0.088, 0.1), (0.07, 0.17), (0.035, 0.19), (0.0, 0.19)],
          clay, Frame((-1.15, top, -0.86)), p)
    lib.sphere('KettleKnob', 0.016, M('Knob', 'clay', 'ceramic'), Frame((-1.15, top + 0.2, -0.86)), p)
    sweep('KettleHandle', [(-1.15, top + 0.2, -0.93), (-1.15, top + 0.24, -0.86), (-1.15, top + 0.2, -0.79)],
          lambda t: 0.011, M('Cord', 'graphite'), p)
    sweep('KettleSpout', [(-1.07, top + 0.08, -0.86), (-1.04, top + 0.13, -0.86), (-1.02, top + 0.16, -0.86)],
          lambda t: 0.016 - 0.007 * t, clay, p)
    bowl = M('BowlCream', 'cream', 'ceramic')
    lathe('FruitBowl', [(0, top), (0.06, top), (0.1, top + 0.03), (0.13, top + 0.07), (0.125, top + 0.072),
                        (0.095, top + 0.03), (0.0, top + 0.02)], bowl, Frame((-0.78, 0, -0.84)), p)
    for i, (dx, dz, c, r) in enumerate(((-0.04, 0.0, '#E9965A', 0.04), (0.035, -0.02, '#E9965A', 0.04),
                                        (0.0, 0.04, '#C9564A', 0.038), (0.01, -0.01, '#E9965A', 0.036))):
        lib.sphere('Fruit%d' % i, r, M('Fruit%d' % i, c, 'ceramic'),
                   Frame((-0.78 + dx, top + 0.055 + (0.035 if i == 3 else 0), -0.84 + dz)), p)
    crock = lathe('Crock', [(0, 0), (0.05, 0), (0.055, 0.14), (0.05, 0.145), (0.0, 0.13)], M('Crock', 'teal', 'ceramic'),
                  Frame((-1.36, top, -0.98)), p)
    wood = M('Spoon', 'honey', 'wood')
    for i, (dx, dz, tilt) in enumerate(((-0.015, 0.0, 8), (0.015, 0.01, -10), (0.0, -0.015, 3))):
        a = math.radians(tilt)
        b0 = Vector((-1.36 + dx, top + 0.08, -0.98 + dz))
        b1 = b0 + Vector((math.sin(a) * 0.2, 0.2, 0))
        tube('SpoonStem%d' % i, [b0, b1], 0.006, wood, p, res=1)
        lib.sphere('SpoonBowl%d' % i, 0.022, wood, Frame(tuple(b1 + Vector((0, 0.02, 0)))), p, scale=(1, 1.3, 0.5))


def nook(root):
    """L breakfast-nook bench in the right-back corner: honey frame with a seat lip, peach cushions, backrests
    along both walls. The corner seat is the roommate's (his Hips at SEAT); the wall run stays clear of his knees."""
    p = lib.empty('Nook', (0, 0, 0), root)
    wood = M('NookWood', HONEY_WOOD, 'wood')
    panel = M('NookPanel', '#B98352', 'wood')
    cush = M('Cushion', 'peach', 'fabric')
    pil = M('Pillow', 'teal', 'fabric')
    seats = [('Corner', 1.58, XR, ZB, -0.68), ('Run', 1.70, XR, -0.68, 0.10)]
    for name, x0, x1, z0, z1 in seats:
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        rbox('Box' + name, (x1 - x0 - 0.04, 0.39, z1 - z0), panel, Frame((cx + 0.02, 0.195, cz)), p, 0.006)
        rbox('Board' + name, (x1 - x0, 0.03, z1 - z0), wood, Frame((cx, 0.405, cz)), p, 0.008)      # the seat lip
        rbox('Cushion' + name, (x1 - x0 - 0.03, 0.05, z1 - z0 - 0.02), cush, Frame((cx + 0.005, NOOK_Y - 0.025, cz)),
             p, 0.02)
    # backrests: tilted cushions on a honey rail along both walls
    rbox('BackBack', (XR - 1.56, 0.36, 0.06), cush, Frame(((1.56 + XR) / 2, 0.69, ZB + 0.045), (-8, 0, 0)), p, 0.025)
    rbox('BackRight', (0.06, 0.36, 0.10 - ZB), cush, Frame((XR - 0.045, 0.69, (ZB + 0.10) / 2), (0, 0, -8)), p, 0.025)
    rbox('RailBack', (XR - 1.55, 0.03, 0.05), wood, Frame(((1.55 + XR) / 2, 0.9, ZB + 0.025)), p, 0.008)
    rbox('RailRight', (0.05, 0.03, 0.11 - ZB), wood, Frame((XR - 0.025, 0.9, (ZB + 0.11) / 2)), p, 0.008)
    rbox('RunEnd', (0.3, 0.9, 0.03), wood, Frame((XR - 0.15, 0.45, 0.115)), p, 0.008)
    rbox('PillowRun', (0.09, 0.26, 0.28), pil, Frame((XR - 0.11, NOOK_Y + 0.13, -0.02), (0, 0, -12)), p, 0.06)


def table(root):
    p = lib.empty('Table', (0, 0, 0), root)
    wood = M('TableWood', HONEY_WOOD, 'wood')
    t = TABLE_TOP
    lathe('TableTop', [(0, t), (TABLE_R - 0.012, t), (TABLE_R, t - 0.012), (TABLE_R - 0.004, t - 0.03),
                       (TABLE_R - 0.03, t - 0.036), (0, t - 0.036)], wood, Frame(tuple(TABLE)), p, seg=48)
    lathe('Pedestal', [(0, 0), (0.17, 0), (0.17, 0.015), (0.12, 0.03), (0.05, 0.07), (0.035, 0.2), (0.032, 0.6),
                       (0.05, t - 0.05), (0.09, t - 0.036), (0, t - 0.036)], wood, Frame(tuple(TABLE)), p, seg=32)
    f, l = facing()
    plate = SEAT + f * 0.42 + l * 0.12
    porcelain = M('Plate', 'porcelain', 'ceramic')
    lathe('Plate', [(0, 0), (0.07, 0), (0.1, 0.012), (0.11, 0.016), (0.105, 0.017), (0.07, 0.004), (0, 0.004)],
          porcelain, Frame((plate.x, t, plate.z)), p)
    toast_slab('PlateToast', Frame((plate.x, t + 0.012, plate.z), (-90, 25, 0)), p, bite=True)
    mug = SEAT + f * 0.4 - l * 0.2
    mug_body('RoommateMug', Frame((mug.x, t, mug.z), (0, 160, 0)), p, M('RmMug', 'clay', 'ceramic'), None)
    lathe('RoommateCoffee', [(0, 0.075), (0.038, 0.075)], M('Coffee', COFFEE, 0.6), Frame((mug.x, t, mug.z)), p)
    napkin = M('Napkin', 'cream', 'fabric')
    nap = SEAT + f * 0.36 + l * 0.27
    rbox('Napkin', (0.12, 0.004, 0.12), napkin, Frame((nap.x, t + 0.002, nap.z), (0, 20, 0)), p, 0.002)


def rug(root):
    p = lib.empty('Rug', (0, 0, 0), root)
    x0, x1, z0, z1 = 0.85, 1.98, -1.08, 0.2
    border = M('RugBorder', TERRACOTTA, 'fabric')
    lib.slab('RugBase', lib.rrect(x1 - x0, z1 - z0, 0.06, 4), 0.006, 0.002, border,
             Frame(((x0 + x1) / 2, 0.0, (z0 + z1) / 2), UPF), p)
    top = tex_mat('RugWeave', PAL['cream'], rug_tex('RugTex'), 0.95)
    quad_grid('RugField', Frame((x0 + 0.04, 0.0065, z1 - 0.04), (-90, 0, 0)), 0, x1 - x0 - 0.08, 0, z1 - z0 - 0.08,
              top, p)


def snake_plant(base, parent, height=0.95):
    """Floor plant: clay pot, chunky upright pointed leaves (sansevieria)."""
    pot = lathe('FloorPot', [(0, 0), (0.12, 0), (0.13, 0.01), (0.15, 0.28), (0.16, 0.29), (0.16, 0.31), (0.145, 0.31),
                             (0.14, 0.28), (0, 0.28)], M('PotClay', 'clay', 'ceramic'), Frame(base), parent, seg=32)
    leaf = lib.mat('Leaf', LEAF, 0.7)
    rng = np.random.default_rng(5)
    for i in range(9):
        a = 2 * math.pi * i / 9 + rng.random() * 0.4
        r = 0.03 + 0.05 * rng.random()
        h = height * (0.55 + 0.45 * rng.random())
        lean = 0.08 + 0.1 * rng.random()
        b = Vector(base) + Vector((math.cos(a) * r, 0.28, math.sin(a) * r))
        outline = [(-0.035, 0.0), (0.035, 0.0), (0.03, h * 0.6), (0.0, h), (-0.03, h * 0.6)]
        fr = Frame(tuple(b), (lean * 57 * math.sin(a), math.degrees(-a) + 90, lean * 57 * math.cos(a)))
        lib.slab('Leaf%d' % i, outline, 0.012, 0.005, leaf, fr.child((0, 0, -0.006)), parent)


def wall_bits(root):
    p = lib.empty('WallBits', (0, 0, 0), root)
    # clock on the right wall between the nook and the window (reads 7:40)
    fc = Frame((XR - 0.002, 1.85, 0.45), (0, -90, 0))
    lib.slab('ClockRim', [(x, y) for x, y in lib.circle(0.15, 40)], 0.04, 0.012, M('ClockRim', 'clay', 'ceramic'), fc,
             p)
    c = ink.Canvas(256, 256, PAL['porcelain'])
    for k in range(12):
        a = 2 * math.pi * k / 12
        u, v = 0.5 + 0.4 * math.sin(a), 0.5 + 0.4 * math.cos(a)
        c.ellipse((u, v), 0.025 if k % 3 == 0 else 0.013, 0.025 if k % 3 == 0 else 0.013, PAL['graphite'])
    uv_disc('ClockFace', fc.child((0, 0, 0.0405)), 0.128, canvas_mat('ClockFace', c), p)
    hands = M('ClockHands', 'graphite', 'rubber')
    for name, ang, ln, w, dz in (('ClockHour', CLOCK[0] * 30 + CLOCK[1] * 0.5, 0.07, 0.013, 0.046),
                                 ('ClockMinute', CLOCK[1] * 6, 0.105, 0.008, 0.05)):
        # built pointing at 12, pivot on the clock centre; node rotation.x = clockwise angle (gameplay can drive it)
        o = lib.box(name, (w, ln + 0.02, 0.003), hands, fc.child((0, ln / 2 - 0.01, dz)), p, bevel=0.001,
                    pivot=fc.at((0, 0, dz)))
        o.rotation_euler = (math.radians(ang), 0, 0)
    lib.sphere('ClockPin', 0.01, M('Knob', 'clay', 'ceramic'), fc.child((0, 0, 0.047)), p)
    # framed print above the nook (sunny-side-up egg on peach)
    fp = Frame((1.05, 1.5, ZB + 0.002))
    ring = lib.rrect(0.36, 0.28, 0.01, 2)
    hole = lib.rrect(0.3, 0.22, 0.004, 1)[::-1]
    lib.slab('PrintFrame', ring, 0.025, 0.006, M('FrameWood', HONEY_WOOD, 'wood'), fp, p, holes=[hole])
    c = ink.Canvas(300, 220, PAL['peach'])
    c.ellipse((0.5, 0.5), 0.36, 0.3, PAL['porcelain'], rot=0.3)
    c.ellipse((0.53, 0.53), 0.13, 0.13, '#F2B33D')
    uv_quad('PrintArt', fp.child((0, 0, 0.004)), 0.3, 0.22, canvas_mat('PrintArt', c), p)


# --- hallway ---------------------------------------------------------------------------------------------------

def hall(root):
    p = lib.empty('Hall', (0, 0, 0), root)
    x0, x1, z0, z1, hh = HALL
    planks = tex_mat('HallPlanks', WOOD, plank_tex('HallPlankTex', WOOD), 0.75)
    quad_grid('HallFloor', Frame((x0, 0, z1), (-90, 0, 0)), 0, x1 - x0, 0, z1 - z0, planks, p, tile=0.8, nx=4)
    paint = M('WallPaint', 'cream', 0.85)
    dado = M('Dado', 'peach', 'painted')
    rail = M('Casing', 'porcelain', 'painted')
    quad_grid('HallCeiling', Frame((x0, hh, z0), (90, 0, 0)), 0, x1 - x0, 0, z1 - z0, paint, p)
    walls = {'North': (Frame((x0, 0, z0)), x1 - x0, []),                          # faces +Z
             'South': (Frame((x1, 0, z1), (0, 180, 0)), x1 - x0, []),             # faces -Z
             'End': (Frame((x0, 0, z1), (0, 90, 0)), z1 - z0, [(z1 - 1.25, z1 - 0.35, 0.0, 2.05)])}
    for name, (f, w, holes) in walls.items():
        for i, (a, b, y0, y1) in enumerate(wall_rects(w, 0, DADO, holes)):
            quad_grid('Hall%sDado%d' % (name, i), f, a, b, y0, y1, dado, p)
        for i, (a, b, y0, y1) in enumerate(wall_rects(w, DADO, hh, holes)):
            quad_grid('Hall%sPaint%d' % (name, i), f, a, b, y0, y1, paint, p)
        if name != 'End':
            rbox('Hall%sRail' % name, (w, 0.035, 0.02), rail, f.child((w / 2, DADO, 0.01)), p, 0.006)
            rbox('Hall%sSkirt' % name, (w, 0.08, 0.016), rail, f.child((w / 2, 0.04, 0.008)), p, 0.004)
    # front door casing, outside dark (porch shadow) behind the open leaf
    fe = Frame((x0 + 0.001, 0, (z0 + z1) / 2), (0, 90, 0))
    ring = [(xx, yy + 1.06) for xx, yy in lib.rrect(1.04, 2.12, 0.02, 2)]
    hole = [(xx, yy + 1.02) for xx, yy in lib.rrect(0.9, 2.08, 0.005, 1)][::-1]
    lib.slab('FrontDoorCasing', ring, 0.022, 0.007, rail, fe, p, holes=[hole])
    porch = lib.mat('Porch', '#E9D9BE', 0.9, emit='#F6E7CB', strength=0.6)
    quad_grid('PorchLight', Frame((x0 - 0.3, 0, 1.25), (0, 90, 0)), 0, 0.9, 0, 2.05, porch, p)
    lamp_glow = lib.mat('LampGlow', '#FFF3DC', 0.6, emit='#FFF3DC', strength=1.6)
    lib.sphere('HallLamp', 0.14, lamp_glow, Frame((-3.5, hh, 0.8)), p, scale=(1, 0.45, 1), seg=24, rings=10)
    coat_hooks(p)
    shoe_rack(p)
    lib.slab('Doormat', lib.rrect(0.55, 0.8, 0.03, 3), 0.012, 0.004, tex_mat('Coir', '#C9A26A',
             weave_tex('CoirTex', '#C9A26A', n=14), 0.95), Frame((x0 + 0.38, 0.0, 0.8), UPF), p)


def coat_hooks(p):
    """Hook rail on the north wall near the door, one slate coat and a peach scarf."""
    z = HALL[2]
    wood = M('HookWood', HONEY_WOOD, 'wood')
    rbox('HookRail', (0.6, 0.08, 0.02), wood, Frame((-4.45, 1.7, z + 0.01)), p, 0.006)
    knob = M('Knob', 'clay', 'ceramic')
    for i, x in enumerate((-4.65, -4.45, -4.25)):
        tube('Hook%d' % i, [(x, 1.69, z + 0.02), (x, 1.69, z + 0.07), (x, 1.73, z + 0.09)], 0.008, knob, p, res=1)
    coat = M('Coat', COAT, 'fabric')
    mb = meta('CoatMeta', 0.012)
    ell(mb, (-4.65, 1.58, z + 0.11), (0.17, 0.09, 0.08))                     # shoulders on the hook
    ell(mb, (-4.65, 1.25, z + 0.12), (0.19, 0.32, 0.09))                     # body
    ell(mb, (-4.65, 0.95, z + 0.12), (0.21, 0.14, 0.085))                    # hem flare
    ell(mb, (-4.65, 1.66, z + 0.1), (0.08, 0.05, 0.06))                      # collar
    for s in (-1, 1):
        ell(mb, (-4.65 + s * 0.17, 1.3, z + 0.14), (0.06, 0.26, 0.06))       # sleeves
    lib.set_parent(solid('Coat', [mb], 0.008, 4000, coat), p)
    scarf = M('Scarf', 'peach', 'fabric')
    sweep('Scarf', [(-4.25, 1.72, z + 0.09), (-4.27, 1.5, z + 0.1), (-4.24, 1.25, z + 0.09)], lambda t: 0.035, scarf, p)


SHOES = {   # kind: upper, sole, lace (None = loafer, no laces), accent
    'sneaker': ('#F4EFE4', '#FFFFFF', '#454C48', '#C98778'),
    'trainer': ('#2D7A73', '#FFFFFF', '#F8F4EA', '#F8F4EA'),
    'loafer': ('#7A4A2E', '#D9C3A0', None, '#5C3520'),
}


def shoe(name, frame, kind, parent):
    """Chunky shoe, toe toward frame -Z (out of the rack): sole slab, rounded upper, criss-cross laces or a loafer
    strap. Big enough to read from the hallway camera."""
    upper_c, sole_c, lace_c, acc_c = SHOES[kind]
    sole = M('Sole' + kind, sole_c, 'rubber')
    low = kind == 'loafer'
    lib.slab(name + 'Sole', lib.rrect(0.105, 0.28, 0.045, 4), 0.026, 0.01, sole, frame.child((0, 0, 0), UPF), parent)
    mb = meta(name + 'Meta', 0.005)
    ell(mb, frame.at((0, 0.045, -0.06)), (0.048, 0.034 if low else 0.042, 0.085))      # toe box
    ell(mb, frame.at((0, 0.05 if low else 0.065, 0.06)), (0.046, 0.04 if low else 0.055, 0.065))   # heel + collar
    lib.set_parent(solid(name + 'Upper', [mb], 0.0045, 1800, M('Upper' + kind, upper_c, 'fabric')), parent)
    acc = M('Accent' + kind, acc_c, 'fabric')
    if lace_c is None:
        rbox(name + 'Strap', (0.075, 0.012, 0.022), acc, frame.child((0, 0.072, -0.03), (-12, 0, 0)), parent, 0.005)
        return
    lace = M('Lace' + kind, lace_c, 'fabric')
    for k in range(4):                                     # criss-cross laces over the tongue
        z = -0.075 + k * 0.024
        y = 0.075 + k * 0.009
        for sgn in (-1, 1):
            tube(name + 'Lace%d%d' % (k, sgn > 0), [frame.at((-0.026 * sgn, y - 0.004, z - 0.008)),
                                                     frame.at((0.026 * sgn, y + 0.004, z + 0.008))], 0.0045, lace,
                 parent, res=1)
    rbox(name + 'Stripe', (0.004, 0.022, 0.09), acc, frame.child((0.047, 0.04, 0.0)), parent, 0.002)
    rbox(name + 'Stripe2', (0.004, 0.022, 0.09), acc, frame.child((-0.047, 0.04, 0.0)), parent, 0.002)


def shoe_rack(p):
    """Two-tier honey rack against the north wall: white sneakers + teal trainers on top, brown loafers below
    (no slippers: the punchline plant)."""
    z = HALL[2]
    wood = M('RackWood', HONEY_WOOD, 'wood')
    x0, x1 = -4.25, -3.5
    for y in (0.05, 0.32):
        rbox('RackShelf%.0f' % (y * 100), (x1 - x0, 0.02, 0.32), wood, Frame(((x0 + x1) / 2, y, z + 0.17)), p, 0.005)
    for x in (x0, x1):
        rbox('RackSide%.0f' % (-x * 100), (0.02, 0.52, 0.32), wood, Frame((x, 0.26, z + 0.17)), p, 0.005)
    pairs = [(0.33, -4.06, 'sneaker'), (0.33, -3.7, 'trainer'), (0.06, -3.88, 'loafer')]
    for i, (y, x, kind) in enumerate(pairs):
        for s_ in (-1, 1):
            shoe('Shoe%d%s' % (i, 'LR'[s_ > 0]), Frame((x + s_ * 0.06, y + 0.012, z + 0.17), (0, 180, 0)), kind, p)


# --- props -----------------------------------------------------------------------------------------------------

def prop_root(pid):
    return lib.empty(pid, (0, 0, 0))


def coffee_machine():
    r = prop_root('coffee_machine')
    teal = M('MachineTeal', 'teal', 'painted')
    cream = M('MachineCream', 'cream', 'painted')
    dark = M('MachineDark', 'graphite', 'rubber')
    rbox('Body', (0.24, 0.3, 0.24), teal, Frame((0, 0.15, -0.02)), r, 0.035)
    rbox('Panel', (0.19, 0.17, 0.012), cream, Frame((0, 0.125, 0.104)), r, 0.02)
    rbox('Head', (0.16, 0.06, 0.14), teal, Frame((0, 0.27, 0.13)), r, 0.022)
    cyl('Spout', 0.016, 0.22, 0.245, dark, Frame((0, 0, 0.19)), r)
    for i, (x, c) in enumerate(((-0.055, 'clay'), (0.0, 'peach'), (0.055, 'porcelain'))):
        lib.sphere('Button%d' % i, 0.019, M('Btn' + c, c, 'ceramic'), Frame((x, 0.17, 0.112)), r, scale=(1, 1, 0.5),
                   seg=20, rings=10)
    rbox('Grille', (0.15, 0.008, 0.07), dark, Frame((0, 0.004, 0.125)), r, 0.003)
    # hopper: frosted matte walls, bean bumps inside, a teal lid node
    frost = lib.mat('HopperFrost', '#EFE8DA', 0.9)
    bsdf = next(n for n in frost.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Alpha'].default_value = 0.55
    frost.surface_render_method = 'BLENDED'
    rbox('Hopper', (0.13, 0.09, 0.13), frost, Frame((0, 0.345, -0.04)), r, 0.02)
    mb = meta('Beans', 0.006)
    rng = np.random.default_rng(2)
    for _ in range(40):
        ell(mb, (rng.uniform(-0.05, 0.05), 0.31 + rng.uniform(0, 0.045), -0.04 + rng.uniform(-0.05, 0.05)),
            (0.011, 0.008, 0.007))
    lib.set_parent(solid('BeanFill', [mb], 0.004, 3000, M('Beans', '#6B4128', 'ceramic')), r)
    lid = lib.empty('HopperLid', (0, 0.39, -0.105), r)               # hinge at the back edge; rotate about +X
    rbox('LidShell', (0.14, 0.02, 0.14), teal, Frame((0, 0.4, -0.04)), lid, 0.008)
    lib.sphere('LidKnob', 0.014, cream, Frame((0, 0.413, -0.04)), lid, scale=(1, 0.7, 1))
    lever = lib.empty('Lever', (0.12, 0.22, -0.02), r)              # grind lever pivot on the right side; rotate about +X
    rbox('LeverBoss', (0.02, 0.05, 0.05), dark, Frame((0.13, 0.22, -0.02)), lever, 0.01)
    tube('LeverArm', [(0.14, 0.22, -0.02), (0.15, 0.27, 0.04)], 0.008, dark, lever, res=1)
    lib.sphere('LeverBall', 0.022, M('Knob', 'clay', 'ceramic'), Frame((0.15, 0.28, 0.05)), lever)
    stream = lib.mat('CoffeeStream', COFFEE, 0.6)
    s = cyl('Stream', 0.006, 0.1, 0.22, stream, Frame((0, 0, 0.19)), r, seg=12, bevel=0.001)
    splash = lib.empty('Splash', (0, 0.12, 0.19), r)
    mb = meta('SplashMeta', 0.004)
    for i in range(7):
        a = 2 * math.pi * i / 7
        ball(mb, (math.cos(a) * 0.03, 0.13 + 0.012 * (i % 2), 0.19 + math.sin(a) * 0.03), 0.008 + 0.004 * (i % 3 == 0))
    ell(mb, (0, 0.12, 0.19), (0.03, 0.006, 0.03))
    lib.set_parent(solid('SplashDrops', [mb], 0.003, 1500, stream), splash)
    return r, {'pivot': 'base centre on the worktop', 'parts': {
        'Stream': 'coffee column spout -> mug (hidden by default)', 'Splash': 'coffee drop crown at the mug top',
        'Lever': 'grind lever, rotate about +X (0 up, ~+40 pulled)', 'HopperLid': 'rotate about +X at the back edge'}}


def mug_body(name, frame, parent, body_mat, band_mat):
    prof = [(0, 0.0), (0.04, 0.0), (0.045, 0.004), (0.046, 0.096), (0.044, 0.1), (0.04, 0.1), (0.038, 0.094),
            (0.038, 0.014), (0.0, 0.014)]
    o = lathe(name, prof, body_mat, frame, parent, seg=32)
    if band_mat is not None:
        lathe(name + 'Band', [(0.0465, 0.056), (0.0472, 0.058), (0.0472, 0.072), (0.0465, 0.074)], band_mat, frame,
              parent, seg=32)
    pts = [frame.at((0.042 + 0.034 * math.sin(a), 0.056 + 0.026 * math.cos(a), 0))
           for a in [math.radians(d) for d in range(10, 171, 20)]]                       # chunky D handle
    sweep(name + 'Handle', pts, lambda t: 0.0095, body_mat, parent, seg=12, n=24)
    return o


def mug():
    r = prop_root('mug')
    mug_body('Body', Frame((0, 0, 0)), r, M('MugCream', 'cream', 'ceramic'), M('MugPeach', 'peach', 'ceramic'))
    coffee = lib.mat('Coffee', COFFEE, 0.6)
    c = lathe('Coffee', [(0, 0.0), (0.0378, 0.0), (0.0378, 0.004), (0, 0.004)], coffee, Frame((0, 0.016, 0)), r,
              seg=32, pivot=(0, 0.02, 0))
    ph = lib.empty('Phone', (0, 0.1, 0), r)
    phone_body(ph, Frame((0.0, 0.1, 0.0), (0, 30, 72)), with_screen=False)
    splats = lib.empty('Splats', (0, 0, 0), r)
    rng = np.random.default_rng(9)
    for i in range(4):
        a = 2 * math.pi * i / 4 + rng.random()
        d = 0.07 + 0.04 * rng.random()
        outline = [(math.cos(t) * (0.012 + 0.006 * math.sin(3 * t + i)), math.sin(t) * (0.012 + 0.006 * math.sin(3 * t + i)))
                   for t in [2 * math.pi * k / 16 for k in range(16)]]
        lib.slab('Splat%d' % i, outline, 0.0015, 0.0006, coffee, Frame((math.cos(a) * d, 0.0004, math.sin(a) * d), UPF),
                 splats)
    return r, {'pivot': 'base centre', 'parts': {
        'Coffee': 'surface disc, y 0.02 (empty) -> 0.055 (half) -> 0.09 (full)',
        'Phone': 'the phone plopped in, top sticking out (hidden by default)',
        'Splats/Splat0..3': 'coffee drops on the worktop around the mug (hidden by default)'}}


PHONE = (0.162, 0.08, 0.152, 0.07)              # case length (x) x width (z), screen; lies landscape


def phone_screen_mat():
    """Landscape ringing face read from Bernard: portrait + heart on top, MOM across ~70% of the width below."""
    w, h = 300, int(300 * PHONE[3] / PHONE[2])
    c = ink.Canvas(w, h, '#22302F')
    c.ellipse((0.44, 0.82), 0.12, 0.12, PAL['peach'])                 # portrait: Mom (grey curls)
    c.ellipse((0.44, 0.9), 0.11, 0.05, '#B9B2A8')
    c.ellipse((0.425, 0.81), 0.013, 0.013, PAL['graphite'])
    c.ellipse((0.455, 0.81), 0.013, 0.013, PAL['graphite'])
    ink.heart(c, (0.58, 0.8), 0.13, PAL['clay'], fill=PAL['clay'])
    w2 = int(w / 1.38)                                                # bold, stretched 1.38x wide: ~70% of the width
    probe = ink.Canvas(w2, h, '#000000')                             # plain sans block caps: an M with a deep V
    sw = h * 0.085                                                    # stroke width (px)
    y0, y1, x0 = 0.1, 0.6, 0.16                                     # letter band (v) and left edge (u)
    lw, gap = 0.2, 0.04

    def m_(u):
        probe.stroke([(u, y0), (u, y1), (u + lw / 2, y0 + 0.08), (u + lw, y1), (u + lw, y0)], sw, '#ffffff')
    m_(x0)
    probe.ellipse((x0 + lw + gap + lw / 2, (y0 + y1) / 2), lw * w2 / h / 2 - 0.0, (y1 - y0) / 2, '#ffffff')
    probe.ellipse((x0 + lw + gap + lw / 2, (y0 + y1) / 2), lw * w2 / h / 2 - sw / h, (y1 - y0) / 2 - sw / h,
                  '#000000')
    m_(x0 + 2 * (lw + gap))
    m = probe.rgb[..., 0]
    xs = np.linspace(0, w2 - 1, w)
    mask = np.stack([np.interp(xs, np.arange(w2), row) for row in m])
    rows = np.where(mask.max(1) > 0.5)[0]
    cols = np.where(mask.max(0) > 0.5)[0]
    PHONE_TEXT.update(cap=(rows.max() - rows.min()) / h, width=(cols.max() - cols.min()) / w,
                      v=1 - (rows.max() + rows.min()) / 2 / h)
    c.paint(mask, PAL['porcelain'])
    c.ellipse((0.05, 0.33), 0.09, 0.09, '#5FAE6E')                   # answer / decline at the ends
    c.ellipse((0.95, 0.33), 0.09, 0.09, '#D2574A')
    return canvas_mat('PhoneScreen', c, rough=0.8, emit=0.9)


PHONE_TEXT = {}


def phone_body(parent, frame, with_screen=True):
    case = M('PhoneCase', 'graphite', 'rubber')
    L, W, sl, sw = PHONE
    lib.slab('Case', lib.rrect(L, W, 0.013, 4), 0.009, 0.0035, case, frame.child((0, -0.0045, 0), UPF), parent)
    if with_screen:
        uv_quad('Screen', frame.child((0, 0.0046, 0), (-90, 0, 0)), sl, sw, phone_screen_mat(), parent)
    else:
        rbox('ScreenDark', (sl, 0.0008, sw), M('ScreenDark', '#1E2423', 'rubber'), frame.child((0, 0.0046, 0)),
             parent, 0.0003)


def phone():
    r = prop_root('phone')
    phone_body(r, Frame((0, 0, 0)))
    return r, {'pivot': 'phone centre, lying flat in landscape (long axis local X; screen up = -Z, so MOM reads '
                        'from Bernard with its baseline toward the counter front)',
               'mom_cap_fraction_of_screen_height': round(PHONE_TEXT['cap'], 3),
               'mom_width_fraction': round(PHONE_TEXT['width'], 3), 'mom_centre_v': round(PHONE_TEXT['v'], 3),
               'parts': {'Case': 'graphite rounded case',
                         'Screen': 'quad %.3f x %.3f, UV 0..1 (u along X, v toward -Z): portrait + heart above, MOM; '
                                   'swap its material for a SubViewport texture if wanted. Hidden = off' % PHONE[2:]}}


def toaster():
    r = prop_root('toaster')
    peach = M('ToasterPeach', 'peach', 'ceramic')
    dark = M('ToasterDark', 'graphite', 'rubber')
    slots = [[(x, z + 0.035 * s) for x, z in lib.rrect(0.13, 0.022, 0.01, 3)] for s in (-1, 1)]
    lib.slab('Body', lib.rrect(0.27, 0.17, 0.06, 6), 0.175, 0.035, peach, Frame((0, 0.012, 0), UPF), r,
             holes=[s[::-1] for s in slots])
    rbox('Well', (0.15, 0.14, 0.1), dark, Frame((0, 0.1, 0)), r, 0.004)           # slot interiors read dark
    for i, (x, z) in enumerate(((-0.1, -0.06), (0.1, -0.06), (-0.1, 0.06), (0.1, 0.06))):
        cyl('Foot%d' % i, 0.012, 0.0, 0.014, dark, Frame((x, 0, z)), r, seg=12)
    rbox('LeverSlot', (0.004, 0.11, 0.016), dark, Frame((0.136, 0.1, 0.0)), r, 0.002)
    lever = lib.empty('Lever', (0.14, 0.15, 0), r)                   # slide down -Y (0.15 up -> 0.06 loaded)
    rbox('LeverKnob', (0.04, 0.025, 0.035), M('LeverCream', 'cream', 'ceramic'), Frame((0.155, 0.15, 0)), lever, 0.01)
    cyl('Dial', 0.018, 0.0, 0.012, M('LeverCream', 'cream', 'ceramic'), Frame((0.07, 0.06, 0.086), (90, 0, 0)), r)
    rbox('DialMark', (0.003, 0.012, 0.002), dark, Frame((0.07, 0.068, 0.099)), r, 0.0008)
    return r, {'pivot': 'base centre', 'slots': 'two slots along X at local z -0.035 / +0.035 (toast / toast_2)',
               'parts': {'Lever': 'slide down -Y 0.09 for `load`'}}


def toast_slab(name, frame, parent, bite=False):
    """Thick slice (0.1 x 0.11 x 0.018) in frame XY: honey crust ring, golden faces."""
    out = []
    for k in range(24):
        t = 2 * math.pi * k / 24
        x, y = math.cos(t) * 0.05, math.sin(t) * 0.055
        if y > 0.02:                                   # domed top with two shoulders
            y += 0.012 * abs(math.sin(2 * t))
        out.append((x, y))
    crust = M('Crust', 'honey', 'wood')
    face = M('ToastFace', TOASTY, 'paper')
    o = lib.slab(name, out, 0.018, 0.005, crust, frame.child((0, 0, -0.009)), parent)
    inner = [(x * 0.82, y * 0.82 - 0.002) for x, y in out]
    lib.slab(name + 'Face', inner, 0.0196, 0.002, face, frame.child((0, 0, -0.0098)), parent)
    return o


def toast():
    r = prop_root('toast')
    toast_slab('Slice', Frame((0, 0, 0)), r)
    crumbs = lib.empty('Crumbs', (0, 0, 0), r)
    rng = np.random.default_rng(3)
    crumb = M('Crust', 'honey', 'wood')
    for i in range(10):
        lib.sphere('Crumb%d' % i, 0.004 + 0.003 * rng.random(), crumb,
                   Frame((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 0.012)), crumbs, seg=8, rings=5)
    return r, {'pivot': 'slice centre; faces along +-Z (stands in a slot)', 'used_by': ['toast', 'toast_2'],
               'parts': {'Slice': 'crust + golden faces', 'Crumbs': 'crumb burst for the splat on the roommate '
                                                                   '(hidden by default; place at the hit point)'}}


def fragile_mat():
    c = ink.Canvas(512, 96, FRAGILE_RED)
    ink.text(c, 'FRAGILE', (0.5, 0.5), 0.62, PAL['porcelain'], weight=3)
    for u in (0.08, 0.92):                              # wine-glass icons
        c.stroke([(u - 0.03, 0.82), (u - 0.025, 0.55), (u, 0.44), (u + 0.025, 0.55), (u + 0.03, 0.82)], 5,
                 PAL['porcelain'])
        c.stroke([(u, 0.44), (u, 0.22)], 5, PAL['porcelain'])
        c.stroke([(u - 0.025, 0.18), (u + 0.025, 0.18)], 5, PAL['porcelain'])
    return canvas_mat('FragileTape', c, rough=0.8)


def parcel():
    r = prop_root('parcel')
    w, h, d = 0.30, 0.15, 0.20
    card = M('Cardboard', CARD, 'paper')
    rbox('Box', (w, h, d), card, Frame((0, h / 2, 0)), r, 0.006)
    rbox('Seam', (w + 0.001, 0.002, 0.004), M('CardDark', '#A87E52', 'paper'), Frame((0, h + 0.0005, 0)), r, 0.0008)
    rbox('PackTape', (w + 0.004, 0.0015, 0.05), M('PackTape', '#D8B27A', 0.7), Frame((0, h + 0.001, 0)), r, 0.0005)
    tape = fragile_mat()
    for s in (-1, 1):
        f = Frame((0, h * 0.55, s * (d / 2 + 0.0008)), (0, 0 if s > 0 else 180, 0))
        uv_quad('Fragile%s' % ('Front' if s > 0 else 'Back'), f, w - 0.02, (w - 0.02) * 96 / 512, tape, r)
    c = ink.paper(200, 130, PAL['porcelain'], seed=4)
    for k, v in enumerate((0.72, 0.52, 0.34)):
        c.stroke([(0.1, v), (0.5 + 0.12 * (k % 2), v + 0.03), (0.8 - 0.1 * k, v)], 3, '#3A4A5A')
    uv_quad('Label', Frame((0.07, h + 0.0018, 0.04), (-90, 0, 0)), 0.1, 0.065, canvas_mat('ParcelLabel', c), r)
    return r, {'pivot': 'base centre', 'size': [w, h, d], 'rotation_y': PROP_YAW['parcel'],
               'parts': {'FragileFront/Back': 'FRAGILE tape (white caps + glass icons) on both long sides'}}


def front_door():
    r = prop_root('front_door')
    leaf = lib.empty('Leaf', (0, 0, 0), r)                       # rotate about +Y; negative opens into the hall
    teal = M('DoorTeal', 'teal', 'painted')
    dark = M('DoorPanel', '#244A49', 'painted')
    w, h, t = 0.9, 2.05, 0.05
    rbox('Panel', (w, h - 0.01, t), teal, Frame((-t / 2, h / 2 + 0.005, -w / 2), (0, 90, 0)), leaf, 0.012)
    for i, (y0, y1) in enumerate(((0.12, 0.92), (1.0, 1.35))):
        rbox('Field%d' % i, (w - 0.22, y1 - y0, 0.008), dark, Frame((0.002, (y0 + y1) / 2, -w / 2), (0, 90, 0)), leaf,
             0.01)
    uv_quad('Pane', Frame((0.0045, 1.65, -w / 2), (0, 90, 0)), 0.36, 0.42, canvas_mat('AmberPane', amber_pane(),
            rough=0.9, emit=0.35), leaf)
    rbox('PaneBead', (0.4, 0.46, 0.004), M('Casing', 'porcelain', 'painted'), Frame((0.0015, 1.65, -w / 2), (0, 90, 0)),
         leaf, 0.02)
    brass = M('DoorKnob', 'honey', 'ceramic')
    lib.sphere('Knob', 0.045, brass, Frame((0.06, 1.0, -w + 0.09)), leaf, scale=(0.8, 1, 1))
    tube('KnobNeck', [(0.002, 1.0, -w + 0.09), (0.03, 1.0, -w + 0.09)], 0.014, brass, leaf, res=1)
    cyl('KnobRose', 0.032, 0.0, 0.012, brass, Frame((0.002, 1.0, -w + 0.09), (0, 0, -90)), leaf)
    rbox('Letterbox', (0.26, 0.05, 0.006), M('Letterbox', 'clay', 'ceramic'), Frame((0.003, 0.85, -w / 2), (0, 90, 0)),
         leaf, 0.008)
    return r, {'pivot': 'hinge (hall-side face, z 1.25 jamb)', 'leaf': {'width': w, 'height': h, 'thickness': t},
               'rotate': 'Leaf about +Y: 0 shut, negative opens into the hall (greybox -1.6 works); node rotation 0'}


PROP_BUILDERS = [coffee_machine, mug, phone, toaster, toast, parcel, front_door]


# --- export ----------------------------------------------------------------------------------------------------

def colliders():
    t = 1.0
    cz = (ZB + ZF) / 2
    x0, x1, hz0, hz1, hh = HALL
    boxes = [('Floor', (-1.5, -t / 2, cz), (7.0 + 2 * t, t, ZF - ZB + 2 * t)),
             ('Ceiling', (0, H + 0.05, cz), (XR - XL, 0.1, ZF - ZB)),
             ('WallBack', (0, H / 2, ZB - t / 2), (XR - XL + 2 * t, H, t)),
             ('WallFront', (0, H / 2, ZF + t / 2), (XR - XL + 2 * t, H, t)),
             ('WallRight', (XR + t / 2, H / 2, cz), (t, H, ZF - ZB)),
             ('WallLeftBack', (XL - 0.05, H / 2, (ZB + DOORWAY[0]) / 2), (0.1, H, DOORWAY[0] - ZB)),
             ('WallLeftFront', (XL - 0.05, H / 2, (DOORWAY[1] + ZF) / 2), (0.1, H, ZF - DOORWAY[1])),
             ('WallLeftTop', (XL - 0.05, (DOORWAY[2] + H) / 2, (DOORWAY[0] + DOORWAY[1]) / 2),
              (0.1, H - DOORWAY[2], DOORWAY[1] - DOORWAY[0])),
             ('HallNorth', ((x0 + x1) / 2, hh / 2, hz0 - t / 2), (x1 - x0, hh, t)),
             ('HallSouth', ((x0 + x1) / 2, hh / 2, hz1 + t / 2), (x1 - x0, hh, t)),
             ('HallEnd', (x0 - t / 2, hh / 2, (hz0 + hz1) / 2), (t, hh, hz1 - hz0)),
             ('Counter', ((COUNTER[0] + COUNTER[1]) / 2, COUNTER[2] / 2, ZB + 0.3), (COUNTER[1] - COUNTER[0], COUNTER[2], 0.6)),
             ('Fridge', (-1.73, 0.925, -0.75), (0.52, 1.85, 0.66)),
             ('NookCorner', (1.79, 0.235, (ZB - 0.68) / 2), (0.42, NOOK_Y, -0.68 - ZB)),
             ('NookRun', (1.85, 0.235, -0.29), (0.3, NOOK_Y, 0.78)),
             ('TableTop', (TABLE.x, TABLE_TOP - 0.018, TABLE.z), (0.6, 0.036, 0.6)),
             ('TablePedestal', (TABLE.x, (TABLE_TOP - 0.036) / 2, TABLE.z), (0.08, TABLE_TOP - 0.036, 0.08)),
             ('ShoeRack', (-3.875, 0.26, hz0 + 0.17), (0.75, 0.52, 0.32))]
    return [{'name': n, 'centre': [round(x, 4) for x in c], 'size': [round(x, 4) for x in sz]} for n, c, sz in boxes]


def scene_file(path, glb_name, node_name):
    with open(path, 'w') as f:
        f.write('[gd_scene format=3]\n\n[ext_resource type="PackedScene" path="res://breakfast/art/%s" id="1"]\n\n'
                '[node name="%s" instance=ExtResource("1")]\n' % (glb_name, node_name))


def main():
    out = os.path.join(lib.ROOT, 'breakfast', 'art')
    os.makedirs(os.path.join(out, 'props'), exist_ok=True)
    lib.reset()
    root = lib.empty('BreakfastRoom', (0, 0, 0))
    shell(root)
    counter(root)
    nook(root)
    table(root)
    rug(root)
    snake_plant((1.68, 0.0, 2.18), lib.empty('FloorPlant', (0, 0, 0), root))
    wall_bits(root)
    hall(root)
    manifest = {'asset_id': 'breakfast_v1', 'style_id': 'warm_ceramic_v1', 'date': '2026-10-16',
                'style_deviations': ['floor terracotta %s' % TERRACOTTA, 'cardboard %s' % CARD,
                                     'FRAGILE tape %s' % FRAGILE_RED, 'coffee %s' % COFFEE, 'toast face %s' % TOASTY,
                                     'plant %s' % LEAF, 'furniture wood %s' % HONEY_WOOD, 'coat %s' % COAT, 'hall planks %s' % WOOD,
                                     'fruit #E9965A/#C9564A', 'phone call buttons green/red', 'window sky emissive',
                                     'sill plant Kenney Furniture Kit plantSmall1 (CC0)'],
                'room': {'tris': BH.tris(root), 'file': 'breakfast_room.glb'}, 'props': {}}
    os.makedirs(os.path.join(lib.ROOT, 'source', 'breakfast'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(lib.ROOT, 'source', 'breakfast', 'breakfast.blend'))
    BH.export(root, os.path.join(out, 'breakfast_room.glb'), False)
    scene_file(os.path.join(out, 'breakfast_room.tscn'), 'breakfast_room.glb', 'BreakfastRoom')
    for build in PROP_BUILDERS:                     # one prop per scene: part names stay unique (Lever, Body..)
        lib.reset()
        r, info = build()
        pid = r.name
        info.update(node_position=list(PROPS[pid]), tris=BH.tris(r), file='props/%s.glb' % pid)
        manifest['props'][pid] = info
        BH.export(r, os.path.join(out, 'props', pid + '.glb'), True)
        scene_file(os.path.join(out, 'props', pid + '.tscn'), 'props/%s.glb' % pid,
                   ''.join(w.title() for w in pid.split('_')) + 'Art')
    f, _ = facing()
    layout = {'props': {k: list(v) for k, v in PROPS.items()}, 'prop_rotation_y': PROP_YAW,
              'marks': {'human': [0, 0, 0], 'roommate_hips': list(SEAT), 'roommate_yaw': SEAT_YAW,
                        'roommate_face_dir': [round(f.x, 3), 0, round(f.z, 3)],
                        'doorway': [-1.7, 0, 0.8], 'hallway': [-4.3, 0, 0.8], 'counter': [0.25, COUNTER[2], -0.62]},
              'table': {'centre': list(TABLE), 'radius': TABLE_R, 'top': TABLE_TOP},
              'nook_seat_top': NOOK_Y, 'colliders': colliders(),
              'lights': {'kitchen_lamp': [0, H - 0.1, 0.6], 'pendant': [TABLE.x, 1.84, TABLE.z],
                         'hall_lamp': [-3.5, HALL[4] - 0.1, 0.8], 'window': {'z': WINDOW[:2], 'y': WINDOW[2:]}}}
    with open(os.path.join(out, 'layout.json'), 'w') as fh:
        json.dump(layout, fh, indent=1)
    with open(os.path.join(out, 'manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=1)
    print('BREAKFAST_BUILT room tris=%d props=%s' % (manifest['room']['tris'],
                                                     {k: v['tris'] for k, v in manifest['props'].items()}))


if __name__ == '__main__':
    main()
