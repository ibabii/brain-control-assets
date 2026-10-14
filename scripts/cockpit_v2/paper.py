"""Paper props: real sheets (thickness, curl), generated paper textures, pins and tape. No baked wording.

Changeable wording lives in Godot text slots (cockpit/art/notes/cockpit_notes.tscn), placed from SLOTS, which this
module fills in Godot world space. Doodles that are part of the paper are painted into the texture.
"""
import math
import os

import bmesh
import numpy as np
from mathutils import Matrix, Vector

import brain
import hardware as hw
import ink
import lib
from lib import Frame

OUT = lib.ROOT + '/cockpit/art/notes/'
INK = {'red': '#7A2430', 'brown': '#4A2E22', 'blue': '#26405E', 'white': '#FFF6EC'}
YELLOW, PINK, ORANGE, PARCHMENT = '#F7D774', '#F5A3B4', '#F6C47C', '#EADCC0'
PX = 1400          # texture pixels per metre
SLOTS = {}         # id -> text slot (Godot world)


# --- placement -------------------------------------------------------------------------------------

def frame_from(pts, plane, shift=None, shrink=0.97):
    """Rectangle fitted to a concept-pixel quad (TL, TR, BR, BL) lying on `plane`. Returns (Frame, w, h).
    Local axes: +X along the writing, +Y up the page, +Z out of the paper toward the viewer."""
    point, normal = plane
    W = [lib.unproject(x, y, plane) for x, y in pts]
    n = Vector(normal).normalized()
    if n.dot(lib.CAM - W[0]) < 0:
        n = -n
    x = (W[1] - W[0]) + (W[2] - W[3])
    x = (x - n * x.dot(n)).normalized()
    y = n.cross(x)
    w = ((W[1] - W[0]).length + (W[2] - W[3]).length) / 2 * shrink
    h = ((W[0] - W[3]).length + (W[1] - W[2]).length) / 2 * shrink
    f = Frame()
    f.o = sum(W, Vector()) / 4 + (Vector(shift) if shift is not None else Vector())
    f.m = Matrix((x, y, n)).transposed()
    return f, w, h


def tilt(f, deg):
    """Spin a frame about its own normal (sticky notes are rarely straight)."""
    g = Frame()
    g.o, g.m = f.o.copy(), f.m @ lib.rot((0, 0, deg))
    return g


# --- geometry --------------------------------------------------------------------------------------

def sheet(name, f, w, h, material, parent, thick=0.0006, curl=0.0, corner=0.0, nx=10, ny=10, outline=None):
    """Paper sheet in f's XY plane, front face at z=0 (UVs 0..1), back at -thick. `curl` lifts the bottom edge
    toward the viewer, `corner` the bottom-right corner. Edges and back sample the texture's corner."""
    def lift(u, v):
        return curl * max(0.0, (0.2 - v) / 0.2) ** 2 + corner * max(0.0, (u - 0.7) / 0.3) ** 2 * max(0.0, (0.3 - v) / 0.3) ** 2

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    top, bot = [], []
    for j in range(ny + 1):
        rt, rb = [], []
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            z = lift(u, v)
            rt.append(bm.verts.new(f.at(((u - 0.5) * w, (v - 0.5) * h, z))))
            rb.append(bm.verts.new(f.at(((u - 0.5) * w, (v - 0.5) * h, z - thick))))
        top.append(rt)
        bot.append(rb)
    edge_uv = (0.004, 0.004)

    def face(vs, uvs):
        fc = bm.faces.new(vs)
        for loop, t in zip(fc.loops, uvs):
            loop[uv].uv = t

    for j in range(ny):
        for i in range(nx):
            face([top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]],
                 [(i / nx, j / ny), ((i + 1) / nx, j / ny), ((i + 1) / nx, (j + 1) / ny), (i / nx, (j + 1) / ny)])
            face([bot[j][i], bot[j + 1][i], bot[j + 1][i + 1], bot[j][i + 1]], [edge_uv] * 4)
    ring = [(i, 0) for i in range(nx)] + [(nx, j) for j in range(ny)] + \
        [(i, ny) for i in range(nx, 0, -1)] + [(0, j) for j in range(ny, 0, -1)]
    for (i0, j0), (i1, j1) in zip(ring, ring[1:] + ring[:1]):
        face([top[j0][i0], bot[j0][i0], bot[j1][i1], top[j1][i1]], [edge_uv] * 4)
    bm.normal_update()
    return lib.from_bmesh(name, bm, material, parent, pivot=f.o, smooth=False)


def card(name, outline, thick, f, size, material, parent):
    """Thick card cut to `outline` (local metres); front face UV-mapped over a size[0] x size[1] box."""
    bm = lib.slab_bm(outline, thick, thick * 0.3, bevel_res=1)
    uv = bm.loops.layers.uv.active or bm.loops.layers.uv.new('UVMap')     # curves bring their own layer
    for fc in bm.faces:
        front = all(v.co.z > thick * 0.97 for v in fc.verts)
        for loop in fc.loops:
            co = loop.vert.co
            loop[uv].uv = (co.x / size[0] + 0.5, co.y / size[1] + 0.5) if front else (0.004, 0.004)
    for v in bm.verts:
        v.co.z -= thick
    lib.transform_bm(bm, f)
    return lib.from_bmesh(name, bm, material, parent, pivot=f.o, smooth=False)


def paper_mat(name, canvas, rough=0.85):
    img = lib.image_from_array('Paper_' + name, canvas.image()[..., :3])
    return lib.mat('Paper_' + name, '#ffffff', rough, image=img)


def tape(name, f, pos, size, angle, parent, seed=0):
    """Thin masking-tape strip with torn ends, lying on the frame's surface."""
    rng = np.random.default_rng(seed)
    w, h = size
    n = 6
    right = [(w / 2 + rng.uniform(-0.003, 0.003), h / 2 - h * k / n) for k in range(n + 1)]
    left = [(-w / 2 + rng.uniform(-0.003, 0.003), -h / 2 + h * k / n) for k in range(n + 1)]
    outline = right + left
    g = f.child(pos, (0, 0, angle))
    bm = lib.slab_bm(outline, 0.0004, 0.0, bevel_res=0)
    lib.transform_bm(bm, g)
    return lib.from_bmesh(name, bm, lib.mat('MaskingTape', '#E9DDBF', 0.55), parent, pivot=g.o, smooth=False)


def pin(name, f, pos, color, parent, depth):
    """Push-pin through the paper into the wall behind."""
    g = f.child(pos)
    lib.slab(name, lib.circle(0.0065, 20), 0.0045, 0.0018, lib.mat('Pin_' + color, color, 0.35), g, parent)
    lib.slab(name + 'Grip', lib.circle(0.0035, 14), 0.008, 0.0015, lib.mat('Pin_' + color, color, 0.35),
             g.child((0, 0, 0.004)), parent)
    lib.tube(name + 'Needle', [g.at((0, 0, 0)), g.at((0, 0, -depth))], 0.0007, lib.mat('PinSteel', '#B9BDBE', 0.3, 0.8),
             parent, res=1, bevel_res=0)


def slot(id, f, w, h, box, text, ink_col, size, align='center', kind='label'):
    """Register a text slot: `box` = (u0, v0, u1, v1) of the paper, `size` = line height as a fraction of h."""
    u0, v0, u1, v1 = box
    c = f.at(((u0 + u1 - 1) / 2 * w, (v0 + v1 - 1) / 2 * h, 0.0008))
    SLOTS[id] = {'kind': kind, 'position': list(c), 'basis': [list(f.m.col[i]) for i in range(3)],
                 'size': [(u1 - u0) * w, (v1 - v0) * h], 'line_height': size * h, 'ink': ink_col,
                 'align': align, 'default': text}


# --- notes -----------------------------------------------------------------------------------------

def tex_size(w, h, scale=1.0):
    return max(int(w * PX * scale), 64), max(int(h * PX * scale), 64)


def sticky(name, f, w, h, color, parent, seed, doodles=(), curl=0.004, corner=0.0, scale=1.0):
    c = ink.paper(*tex_size(w, h, scale), color, seed)
    # Glue strip along the top: a touch darker and smoother.
    c.multiply(1 - 0.03 * (c.y < c.h * 0.16))
    for fn, *args in doodles:
        fn(c, *args)
    return sheet(name, f, w, h, paper_mat(name, c), parent, curl=curl, corner=corner)


def on_monitor(pts, name, lift=0.03):
    """Plane just in front of a monitor's bezel, so notes can be taped across it."""
    spec = hw.LAYOUT[name]
    f = Frame(spec['pos'], spec['deg'])
    return frame_from(pts, (f.at((0, 0, lift)), f.dir((0, 0, 1))))


def wall_note(name, pts, parent, gap=0.26, spin=0.0):
    cx, cy = sum(p[0] for p in pts) / 4, sum(p[1] for p in pts) / 4
    p, n = _wall_plane(cx, cy, gap)
    f, w, h = frame_from(pts, (p, n))
    return tilt(f, spin), w, h, gap


def _wall_plane(px, py, gap):
    p, _ = brain.wall_hit(px, py, gap)
    n = (brain.wall_normal(p) + (-lib.FWD)).normalized()
    return p, n


def notes(parent):
    g = lib.empty('Notes', (0, 1.2, -0.5), parent)
    red, brown = INK['red'], INK['brown']

    # Pinned to the brain wall (in front of the cables, like the concept).
    # The 16:9 side monitors cover the concept spots, so these are taped across the bezels.
    f, w, h = on_monitor([(18, 222), (158, 206), (176, 346), (36, 362)], 'LeftPanel')
    sticky('YouGotThis', f, w, h, PINK, g, 1, [(ink.smiley, (0.58, 0.13), 0.12, red)], curl=0.006)
    tape('YouGotThisTape', f, (w * 0.42, h * 0.38, 0.0003), (0.05, 0.02), -50, g, 7)
    slot('YouGotThis', f, w, h, (0.08, 0.24, 0.92, 0.95), 'YOU\nGOT THIS\n(probably)', red, 0.2)

    f, w, h, gap = wall_note('ItsFine', [(1405, 47), (1512, 27), (1525, 127), (1417, 142)], g)
    sticky('ItsFine', f, w, h, YELLOW, g, 2, [(ink.cat, (0.5, 0.3), 0.36, brown)], corner=0.004)
    pin('ItsFinePin', f, (-w * 0.38, h * 0.4, 0.0006), '#D4473A', g, gap)
    slot('ItsFine', f, w, h, (0.08, 0.58, 0.92, 0.94), "IT'S FINE", brown, 0.22)

    f, w, h, gap = wall_note('Chaos', [(1542, 112), (1642, 80), (1652, 275), (1552, 295)], g)
    sticky('Chaos', f, w, h, PINK, g, 3, [(ink.bulb, (0.55, 0.17), 0.17, red)], curl=0.005)
    pin('ChaosPin', f, (0, h * 0.44, 0.0006), '#EAC04A', g, gap)
    slot('Chaos', f, w, h, (0.06, 0.33, 0.94, 0.94), 'CHAOS\n=\nCREATIVITY\n?', red, 0.09)

    f, w, h = on_monitor([(1500, 345), (1630, 352), (1610, 487), (1478, 478)], 'RightPanel')
    sticky('MopFloor', f, w, h, YELLOW, g, 4, [(ink.smiley, (0.55, 0.12), 0.12, brown)], curl=0.005)
    tape('MopFloorTape', f, (-w * 0.44, h * 0.36, 0.0003), (0.05, 0.02), 40, g, 8)
    slot('MopFloor', f, w, h, (0.06, 0.24, 0.94, 0.95), 'MOP\nFLOOR\n=\nADULTING', brown, 0.15)

    # Taped to the main screen frame; they follow its corners for the chosen layout (concept frame 1.12 x 0.49).
    spec = hw.LAYOUT['FrontScreen']
    sw, sh = spec['size']
    _, scy, _ = spec['pos']
    d_r = Vector(((sw - 1.12) / 2, scy - 1.33, 0))
    f, w, h = on_monitor([(470, 12), (614, 4), (618, 102), (478, 110)], 'FrontScreen', 0.11)
    sticky('SameBrain', f, w, h, ORANGE, g, 5, [(ink.smiley, (0.8, 0.14), 0.13, brown)], curl=0.003)
    tape('SameBrainTape', f, (w * 0.32, h * 0.47, 0.0003), (0.045, 0.018), -30, g, 1)
    slot('SameBrain', f, w, h, (0.06, 0.2, 0.94, 0.95), 'SAME\nBRAIN\nDIFFERENT\nDAY...', brown, 0.2)

    f, w, h = frame_from([(1127, 280), (1182, 279), (1183, 357), (1128, 358)], lib.zplane(-0.47), d_r)
    sticky('HeartSticky', f, w, h, YELLOW, g, 6, [(ink.heart, (0.5, 0.45), 0.42, red, None, '#E8615A')])
    tape('HeartStickyTape', f, (0, h * 0.48, 0.0003), (0.035, 0.014), 4, g, 2)
    slot('HeartSticky', f, w, h, (0.08, 0.06, 0.92, 0.24), '', red, 0.16)

    # Smiley sticker on the frame corner.
    f, w, h = on_monitor([(772, 66), (800, 66), (800, 94), (772, 94)], 'FrontScreen', 0.026)
    c = ink.Canvas(96, 96, '#F2C94C')
    c.ellipse((0.5, 0.5), 0.48, 0.48, '#F5D25A', soft=10)
    ink.smiley(c, (0.5, 0.5), 0.8, '#3B2A1E', w=4, ring=False)
    card('SmileySticker', lib.circle(w / 2, 28), 0.0008, f, (w, w), paper_mat('Smiley', c, 0.5), g)

    # Small-steps heart: a thick card tag pinned near the banana.
    f, w, h, gap = wall_note('SmallStepsHeart', [(1180, 30), (1272, 30), (1272, 122), (1180, 122)], g)
    shape = []
    for i in range(48):
        t = 2 * math.pi * i / 48
        shape.append((16 * math.sin(t) ** 3 / 32 * w, (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t)
                                                       - math.cos(4 * t)) / 32 * h + 0.06 * h))
    c = ink.paper(*tex_size(w, h), '#D9483F', 7, grain=0.05)
    c.ellipse((0.42, 0.66), 0.22, 0.12, '#E86A5E', opacity=0.6, soft=12)
    ink.smiley(c, (0.5, 0.22), 0.12, INK['white'], ring=False)
    card('SmallStepsHeart', shape, 0.003, f, (w, h), paper_mat('SmallSteps', c, 0.6), g)
    pin('SmallStepsPin', f, (0, h * 0.36, 0.0003), '#F2EEE6', g, gap)
    slot('SmallSteps', f, w, h, (0.16, 0.32, 0.84, 0.78), 'SMALL\nSTEPS', INK['white'], 0.2)

    # Console notes, taped down.
    f, w, h = frame_from([(822, 714), (947, 697), (964, 764), (829, 782)], (hw.CONSOLE.at((0, 0.004, 0)),
                                                                             hw.CONSOLE.dir((0, 1, 0))))
    sticky('DoTheThing', f, w, h, YELLOW, g, 8, [(ink.heart, (0.8, 0.2), 0.16, '#D4473A')], curl=0.002)
    tape('DoTheThingTape', f, (-w * 0.42, h * 0.3, 0.0003), (0.04, 0.016), 60, g, 3)
    slot('DoTheThing', f, w, h, (0.06, 0.08, 0.94, 0.95), 'DO\nTHE THING\n(please)', brown, 0.22)

    # Lies flat on the tray, right of the notebook.
    f, w, h = frame_from([(978, 788), (1140, 792), (1154, 945), (985, 940)], (Vector((0, 0.8905, 0)), Vector((0, 1, 0))))
    f.o += Vector((0, 0, 0.045))                       # clear of the console lip
    c = ink.paper(*tex_size(w, h), PARCHMENT, 9, grain=0.05, vignette=0.12)
    ink.stain(c, (0.72, 0.18), 0.14)
    ink.heart(c, (0.8, 0.1), 0.06, '#D4473A')
    sheet('TodoList', f, w, h, paper_mat('TodoList', c), g, curl=0.0, corner=0.003)
    tape('TodoListTapeL', f, (-w * 0.45, -h * 0.42, 0.0003), (0.05, 0.02), 35, g, 4)
    tape('TodoListTapeR', f, (w * 0.42, -h * 0.4, 0.0003), (0.05, 0.02), -30, g, 5)
    slot('TodoList', f, w, h, (0.1, 0.08, 0.92, 0.95),
         '1. MOP\n2. EXIST\n3. SNACK\n4. MAYBE TIDY?\n5. BE PROUD\n     (for real)', brown, 0.1, align='left')

    # Polaroid: white card, printed photo, caption slot.
    f, w, h, gap = wall_note('Polaroid', [(4, 10), (168, 6), (180, 152), (14, 164)], g)
    c = ink.paper(*tex_size(w, h, 2), '#F4F0E6', 10, grain=0.02)
    photo = ink.dog_photo(int(c.w * 0.86), int(c.h * 0.7))
    x0, y0 = int(c.w * 0.07), int(c.h * 0.05)
    c.rgb[y0:y0 + photo.h, x0:x0 + photo.w] = photo.rgb
    ink.heart(c, (0.08, 0.13), 0.05, '#D4473A')
    ink.heart(c, (0.74, 0.13), 0.05, '#D4473A')
    sheet('Polaroid', f, w, h, paper_mat('Polaroid', c, 0.5), g, thick=0.0012, corner=0.004)
    tape('PolaroidTape', f, (-w * 0.02, h * 0.5, 0.0003), (0.06, 0.024), 18, g, 6)
    pin('PolaroidPin', f, (w * 0.3, h * 0.46, 0.0006), '#D4473A', g, gap)
    slot('Polaroid', f, w, h, (0.12, 0.03, 0.68, 0.22), 'Good Boy', '#2B2220', 0.12)

    # Task note: blank paper; gameplay writes the task on it (same transform as the game TaskNote).
    tf = Frame((-0.74, 1.0, -0.12), (-10, 25, 0))
    f, w, h = frame_from([(267, 520), (420, 492), (447, 582), (295, 612)], (tf.o, tf.dir((0, 0, 1))))
    o = sticky('TaskNote', f, w, h, YELLOW, g, 11, curl=0.002)
    o['gameplay'] = 'TaskNote paper: game Label goes on top, same transform as game TaskNote'
    return g


def _wall_depth(px, py, gap):
    p, _ = brain.wall_hit(px, py, gap)
    return (p - lib.CAM).dot(lib.FWD)


# --- notebook with the TODAY list --------------------------------------------------------------------

def notebook(parent):
    g = lib.empty('Notebook', (-0.1, 0.9, 0.3), parent)
    y = 0.905
    ground = (Vector((0, y, 0)), Vector((0, 1, 0)))
    f, w, h = frame_from([(615, 795), (900, 772), (962, 941), (600, 941)], ground, shrink=1.0)
    f.o += Vector((0, 0, 0.055))                       # clear of the console lip
    ext = 0.08                     # the page runs past the concept's bottom edge
    h += ext
    f.o = f.at((0, -ext / 2, 0))
    cover = lib.mat('NotebookCover', '#C9786A', 0.7)
    lib.slab('Cover', lib.rrect(w + 0.05, h + 0.025, 0.01, 3), 0.014, 0.003, cover, f.child((-0.01, 0, -0.0145)), g)
    lib.slab('PageBlock', lib.rrect(w, h, 0.004, 2), 0.0035, 0.001, lib.mat('PageBlock', '#E9DCC6', 0.85),
             f.child((0, 0, -0.0045)), g)
    c = ink.paper(*tex_size(w, h, 1.6), '#F6EEDD', 12, grain=0.025)
    ink.ruled(c, 0.082, top=0.86, margin=0.1)
    blue, pink = '#3F5FA8', '#D45C8A'
    ink.cat(c, (0.82, 0.74), 0.13, blue)
    ink.heart(c, (0.7, 0.86), 0.06, blue)
    ink.star(c, (0.94, 0.9), 0.06, blue)
    ink.rainbow(c, (0.8, 0.44), 0.18)
    ink.star(c, (0.66, 0.36), 0.06, blue)
    ink.heart(c, (0.95, 0.56), 0.05, pink)
    sheet('Page', f, w, h, paper_mat('TodayPage', c), g, thick=0.0004, curl=0.0, corner=0.002, nx=12, ny=12)
    # Spiral binding along the left edge.
    steel = lib.mat('Spiral', '#9AA1A3', 0.35, 0.8)
    n = 11
    for k in range(n):
        yy = (k + 0.5) / n - 0.5
        ring = [f.at((-w / 2 - 0.012 + 0.016 * math.cos(a), yy * h, 0.004 + 0.011 * math.sin(a)))
                for a in np.linspace(-0.6, math.pi + 0.3, 9)]
        lib.tube('Ring%02d' % k, ring, 0.0016, steel, g, res=3, bevel_res=1)
    SLOTS['Today'] = {'kind': 'list', 'position': list(f.at((-w * 0.12, 0.0, 0.0008))),
                      'basis': [list(f.m.col[i]) for i in range(3)], 'size': [w * 0.7, h * 0.8],
                      'line_height': 0.082 * h, 'ink': '#26405E', 'align': 'left',
                      'default': {'title': 'TODAY:', 'items': [
                          {'text': 'Mop kitchen floor', 'done': True},
                          {'text': 'Be a functional human', 'done': False},
                          {'text': 'Pet the cat/kind of', 'done': False},
                          {'text': "It's okay. :)", 'done': False}]}}
    # Checkbox art for the list (ink on transparent).
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (('check_box', ink.box), ('check_tick', ink.tick)):
        cv = ink.Canvas(64, 64, '#26405E', alpha=0.0)
        fn(cv, (0.5, 0.5), 0.8, '#26405E', w=4.5)
        img = lib.image_from_array(name, cv.image())
        img.filepath_raw = OUT + name + '.png'
        img.file_format = 'PNG'
        img.save()
    return g
