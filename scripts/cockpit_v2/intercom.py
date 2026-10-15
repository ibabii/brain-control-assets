"""Intercom under the front screen (contract: coordination/interfaces.md, "Intercom, answering machine, text kit").

Local frame: origin = display centre, +X right, +Y up, +Z toward the player. Exported on its own as
cockpit/art/intercom/intercom.glb; cockpit_art.tscn instances intercom.tscn at POS.
"""
import math

import bmesh
import bpy
from mathutils import Vector

import hardware as hw
import ink
import lib
import props
from lib import Frame, circle, rrect

SCREEN = hw.LAYOUT['FrontScreen']
CHIN_Y = SCREEN['pos'][1] - SCREEN['size'][1] / 2 - hw.CHIN / 2
FACE = (1.22, 0.08)                      # cream faceplate on the chin
DISPLAY = (0.656, 0.056)
GLASS = (0.67, 0.06)
FP_Z = -0.003                            # faceplate front (display plane = 0)
POS = (0.0, CHIN_Y, SCREEN['pos'][2] + 0.022 + 0.0055 - FP_Z)      # faceplate back 0.5 mm into the chin
# Caller lamps, left of the text so the eye meets the speaker first (game-ux). Colour = lit tone; unlit albedo is dimmed.
LAMPS = [('Brain', -0.553, '#EAA78B'), ('Heart', -0.4993, '#C98778'), ('Stomach', -0.4457, '#A9B89F'),
         ('Gary', -0.392, '#D9A04C')]
SIZE = 0.046                             # lamp icon span
UNLIT = 0.55                             # unlit albedo = lit colour x this (a clear on/off jump, not only hue)


def M(key, color, rough=0.6, metal=0.0):
    return lib.mat('Intercom_' + key, color, rough, metal)


def _ccw(pts):
    return pts if lib._area(pts) > 0 else list(reversed(pts))


def _smooth(pts, n=2):
    """Chaikin corner cutting: the bevel inset needs no sharp concave corners."""
    for _ in range(n):
        out = []
        for a, b in zip(pts, pts[1:] + pts[:1]):
            out += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        pts = out
    return pts


def heart(s):
    pts = []
    for i in range(1, 48):                       # skip the top cusp (t = 0)
        t = 2 * math.pi * i / 48
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x * s / 34, (y + 2.5) * s / 34))
    pts.insert(0, (0, 3.2 * s / 34))                # shallow dip instead of the cusp
    return _ccw(_smooth(pts[::2]))


def bean(s):
    """Stomach: a round bean with a shallow dent (smooth, unlike the lumpy brain)."""
    pts = []
    for i in range(64):
        t = 2 * math.pi * i / 64
        d = math.atan2(math.sin(t - 1.2), math.cos(t - 1.2))
        r = 1 - 0.2 * math.exp(-(d / 0.5) ** 2)
        pts.append((math.cos(t) * 0.52 * r * s, math.sin(t) * 0.44 * r * s))
    return _ccw(_smooth(pts, 1))


def brain(s):
    """Brain: wide lumpy cloud (seven lobes)."""
    pts = []
    for i in range(84):
        t = 2 * math.pi * i / 84
        r = 1 + 0.09 * math.cos(7 * t) + 0.03 * math.cos(13 * t)
        pts.append((math.cos(t) * 0.52 * r * s, math.sin(t) * 0.38 * r * s + 0.02 * s))
    return _ccw(_smooth(pts, 1))


def _dim(col):
    r, g, b = (int(col[i:i + 2], 16) * UNLIT for i in (1, 3, 5))
    return '#%02X%02X%02X' % (round(r), round(g), round(b))


def cassette(s):
    w, h = s * 1.1, s * 0.72
    holes = [list(reversed(circle(s * 0.12, 16, sx * s * 0.25, s * 0.05))) for sx in (-1, 1)]
    return rrect(w, h, s * 0.08, 3), holes


def build(root):
    f = Frame(POS)
    g = lib.empty('Intercom', POS, root)
    lib.slab('Faceplate', rrect(*FACE, 0.012), 0.006, 0.002, M('Faceplate', '#E2D3B5', 0.5), f.child((0, 0, FP_Z - 0.006)), g)
    lib.slab('DisplayBezel', rrect(0.696, 0.072, 0.01), 0.005, 0.0015, M('Bezel', '#2F3434', 0.7),
             f.child((0, 0, FP_Z - 0.0005)), g, holes=[list(reversed(rrect(*GLASS, 0.006)))])
    lib.box('Glass', (GLASS[0] - 0.002, GLASS[1] - 0.002, 0.002), M('Glass', '#14181A', 0.25), f.child((0, 0, FP_Z + 0.001)), g)
    # Display: one quad for the dot-matrix shader. In Godot UV (0,0) is the top-left (glTF flips V).
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    dw, dh = DISPLAY
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    face_ = bm.faces.new([bm.verts.new(f.at((sx * dw / 2, sy * dh / 2, 0))) for sx, sy in corners])
    for loop, (sx, sy) in zip(face_.loops, corners):
        loop[uv].uv = ((sx + 1) / 2, (sy + 1) / 2)
    lib.from_bmesh('Display', bm, M('Display', '#1C1A16', 0.4), g, pivot=f.o, smooth=False)
    # Speaker grille: painted holes on a dark card.
    c = ink.Canvas(500, 200, '#3A3F3C')
    for i in range(14):
        for j in range(5):
            c.ellipse(((i + 0.5) / 14, (j + 0.5) / 5), 0.055, 0.055, '#16191A')
    props.face_card('Grille', 0.2, 0.06, c, f.child((0.468, 0, FP_Z + 0.0015)), g, rough=0.7, thick=0.002)
    lib.slab('LampPlate', rrect(0.228, 0.066, 0.012), 0.003, 0.001, M('LampPlate', '#2F3434', 0.8),
             f.child((-0.468, 0, FP_Z - 0.0005)), g)
    lamps = lib.empty('Lamps', POS, g)
    base = FP_Z + 0.002
    for name, x, col in LAMPS:
        holes = []
        if name == 'Brain':
            out = brain(SIZE)
        elif name == 'Heart':
            out = heart(SIZE)
        elif name == 'Stomach':
            out = bean(SIZE)
        else:
            out, holes = cassette(SIZE)
        lib.slab(name, out, 0.008, 0.0022, M('Lamp' + name, _dim(col), 0.35), f.child((x, 0, base)), lamps,
                 holes=holes, pivot=f.at((x, 0, base + 0.008)))
    face = bpy.data.objects['Faceplate']
    for sx in (-1, 1):
        for sy in (-1, 1):
            hw.screw(g, f, (sx * 0.597, sy * 0.028, FP_Z), 0.0045, on=face, sink=0.0008)
    # Second-hand retrofit: tape over the faceplate's top-right corner onto the chin (in the main art, not the module).
    lib.tape_strip('IntercomTape', f.child((0.59, 0.042, FP_Z + 0.0005), (0, 0, -35)), (0.045, 0.026), root, seed=77)
    return g, {'position': list(POS), 'display_size': list(DISPLAY), 'lamp_lit': {n: c for n, _, c in LAMPS}}
