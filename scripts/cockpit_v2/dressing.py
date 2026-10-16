"""Clutter: cables, fairy lights, paper notes and props. Positions are read from concept pixels.

Everything is modelled and textured in Blender (paper.py, props.py); placement follows the concept from the game
camera. No concept pixels are used.
"""
import math
import random

import bmesh
from mathutils import Vector

import answering_machine
import brain
import hardware as hw
import lib
import paper
import props
from lib import Frame, UPF, circle, rrect

CABLE = ['#2F6F70', '#1F4B4D', '#D4473A', '#E59A3A', '#EAC04A', '#3F6A86', '#2F6F70', '#D4473A']


def at_depth(px, py, depth):
    return lib.unproject(px, py, lib.facing(depth))


def depth_of(p):
    return (Vector(p) - lib.CAM).dot(lib.FWD)


def wall_plane(px, py, gap=0.1, yaw=0.0):
    """Plane through the wall point under (px, py), tilted halfway from facing the camera to lying on the wall."""
    p, _ = brain.wall_hit(px, py, gap)
    n = (brain.wall_normal(p) + (-lib.FWD)).normalized()
    return p, n


def plane3(a, b, c):
    n = (Vector(b) - Vector(a)).cross(Vector(c) - Vector(a)).normalized()
    if n.dot(lib.CAM - Vector(a)) < 0:
        n = -n
    return Vector(a), n


def console_plane(offset=0.003):
    return hw.CONSOLE.at((0, offset, 0)), hw.CONSOLE.dir((0, 1, 0))


def ground(y):
    return Vector((0, y, 0)), Vector((0, 1, 0))


def m_per_px(depth):
    return 2 * lib.TY * depth / lib.CH


def _fit(bbox, depth=None, ground_y=None, shrink=0.94):
    """Centre and size (m) of a concept-pixel box at `depth`, or standing on the floor height `ground_y`."""
    x0, y0, x1, y1 = bbox
    if ground_y is not None:
        base = lib.unproject((x0 + x1) / 2, y1 - (y1 - y0) * 0.06, ground(ground_y))
        depth = depth_of(base)
    s = m_per_px(depth) * shrink
    w, h = (x1 - x0) * s, (y1 - y0) * s
    centre = at_depth((x0 + x1) / 2, (y0 + y1) / 2, depth)
    if ground_y is not None:
        centre = Vector((centre.x, ground_y + h / 2, centre.z))
    return centre, w, h


def wall_depth(px, py, gap):
    p, _ = brain.wall_hit(px, py, gap)
    return depth_of(p)


# --- cables and lights ----------------------------------------------------------------------------

CABLE_PATHS = [
    # (colour index, radius, [(px, py, depth), ...]) traced over the concept. Depth is clamped to sit on the wall.
    # Bundle between the left screen and the main housing, ending behind the console.
    (0, 0.016, [(520, -40, 1.65), (510, 150, 1.5), (530, 320, 1.45), (515, 480, 1.4), (500, 640, 1.2)]),
    (2, 0.014, [(565, -40, 1.65), (540, 120, 1.52), (505, 260, 1.48), (522, 420, 1.42), (540, 650, 1.2)]),
    (3, 0.013, [(470, -40, 1.75), (498, 180, 1.55), (538, 350, 1.48), (520, 520, 1.38), (480, 660, 1.2)]),
    (1, 0.018, [(605, -30, 1.75), (565, 200, 1.6), (548, 380, 1.52), (528, 580, 1.35), (560, 680, 1.2)]),
    (5, 0.012, [(490, -40, 1.7), (488, 200, 1.52), (512, 400, 1.45), (495, 640, 1.22)]),
    (4, 0.011, [(545, -40, 1.7), (525, 150, 1.55), (548, 300, 1.5), (530, 560, 1.38), (515, 680, 1.2)]),
    # Around the left screen and the polaroid.
    (4, 0.012, [(330, 250, 1.35), (296, 302, 1.3), (250, 282, 1.38), (222, 335, 1.42), (240, 430, 1.35)]),
    (0, 0.015, [(170, 430, 1.5), (215, 300, 1.55), (300, 205, 1.58), (420, 185, 1.6), (470, 140, 1.62)]),
    (5, 0.013, [(240, 470, 1.4), (230, 560, 1.32), (250, 640, 1.2), (330, 690, 1.05)]),
    (2, 0.013, [(260, 180, 1.6), (240, 250, 1.55), (215, 380, 1.5), (230, 520, 1.4), (300, 600, 1.25)]),
    # Swags across the top.
    (3, 0.014, [(230, -30, 2.05), (400, 45, 1.95), (600, 70, 1.95), (800, 20, 2.0), (900, -40, 2.1)]),
    (0, 0.016, [(850, -40, 2.1), (1000, 45, 1.95), (1200, 30, 1.95), (1400, -40, 2.1)]),
    (2, 0.015, [(1080, -30, 2.1), (1300, 70, 1.95), (1500, 45, 1.95), (1700, 15, 2.05)]),
    (1, 0.017, [(620, -30, 1.9), (700, 60, 1.82), (820, 80, 1.8), (960, 50, 1.85), (1060, -30, 1.95)]),
    (4, 0.012, [(-30, 60, 2.0), (120, 20, 2.0), (260, 60, 1.95), (420, 0, 2.0), (520, -40, 2.1)]),
    (5, 0.013, [(1250, -40, 2.1), (1350, 30, 2.0), (1480, 90, 1.95), (1600, 60, 2.0), (1700, 120, 2.0)]),
    # Bundle between the main housing and the right screen.
    (0, 0.016, [(1180, -40, 1.65), (1172, 150, 1.52), (1186, 300, 1.48), (1172, 460, 1.42), (1160, 640, 1.2)]),
    (3, 0.013, [(1222, 110, 1.55), (1192, 200, 1.5), (1180, 350, 1.45), (1196, 470, 1.4), (1180, 640, 1.2)]),
    (2, 0.015, [(1245, -40, 1.75), (1203, 230, 1.55), (1192, 480, 1.45), (1170, 650, 1.2)]),
    (1, 0.015, [(1150, -40, 1.7), (1160, 200, 1.55), (1150, 420, 1.45), (1140, 640, 1.2)]),
    # Right of the right screen, behind the notes.
    (0, 0.016, [(1462, 280, 1.45), (1530, 322, 1.5), (1562, 400, 1.55), (1600, 520, 1.6), (1640, 640, 1.6)]),
    (4, 0.012, [(1462, 300, 1.42), (1515, 332, 1.45), (1570, 318, 1.5)]),
    (2, 0.014, [(1600, 250, 1.7), (1660, 320, 1.65), (1700, 420, 1.6)]),
    (1, 0.016, [(1480, 500, 1.5), (1540, 540, 1.45), (1620, 520, 1.5), (1700, 560, 1.5)]),
    (6, 0.013, [(1700, 230, 1.7), (1630, 290, 1.7), (1560, 300, 1.65), (1480, 250, 1.5)]),
]


BUNDLES = [
    # (count, spread m, [(px, py, depth), ...]) — loose bundles that fill the gaps like the concept.
    (10, 0.07, [(520, -40, 1.75), (512, 200, 1.58), (526, 400, 1.48), (508, 650, 1.2)]),
    (8, 0.06, [(1178, -40, 1.75), (1182, 200, 1.58), (1170, 420, 1.48), (1160, 650, 1.2)]),
    (9, 0.11, [(250, -40, 1.8), (232, 200, 1.62), (200, 400, 1.5), (170, 620, 1.3)]),
    (7, 0.09, [(1470, 200, 1.55), (1520, 350, 1.55), (1565, 500, 1.5), (1600, 660, 1.4)]),
    (6, 0.14, [(-450, 160, 2.0), (-40, 70, 2.0), (400, 40, 1.98), (800, 25, 2.05), (1200, 40, 1.98), (1720, 70, 2.0),
               (2120, 160, 2.0)]),
    (6, 0.12, [(-420, -60, 2.0), (-300, 300, 1.9), (-350, 650, 1.8)]),
    (6, 0.12, [(2090, -60, 2.0), (1980, 300, 1.9), (2040, 650, 1.8)]),
    (5, 0.08, [(555, 420, 1.42), (545, 520, 1.4), (560, 620, 1.25)]),
    (5, 0.08, [(1135, 420, 1.42), (1150, 520, 1.4), (1140, 620, 1.25)]),
]


def droop(pts, k=0.18):
    """Insert sagging midpoints so cables hang instead of running straight."""
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        span = math.hypot(b.x - a.x, b.z - a.z)
        out += [(a + b) / 2 - Vector((0, k * span, 0)), b]
    return out


def cables(parent):
    g = lib.empty('Cables', (0, 1.3, -0.6), parent)
    mats = [lib.mat('Cable%d' % i, c, 0.45) for i, c in enumerate(CABLE)]
    for i, (ci, r, path) in enumerate(CABLE_PATHS):
        pts = [at_depth(px, py, wall_depth(px, py, 0.13)) for px, py, d in path]   # on the wall, behind notes
        lib.tube('Cable%02d' % i, droop(pts), r, mats[ci], g)
    rb = random.Random(11)
    for b, (count, spread, path) in enumerate(BUNDLES):
        base = [at_depth(px, py, wall_depth(px, py, 0.13)) for px, py, d in path]   # on the wall, behind notes
        for k in range(count):
            off = Vector((rb.uniform(-spread, spread), 0, rb.uniform(-spread, spread) * 0.6))
            pts = [p + off + Vector((rb.uniform(-0.03, 0.03), rb.uniform(-0.03, 0.03), rb.uniform(-0.02, 0.02)))
                   for p in base]
            lib.tube('Bundle%d_%d' % (b, k), droop(pts, rb.uniform(0.1, 0.3)), rb.uniform(0.008, 0.015),
                     mats[rb.randrange(len(mats))], g)
    # Tangles on the desk, left and right of the console.
    rnd = random.Random(4)
    for side, x0, x1 in ((-1, -1.55, -0.62), (1, 0.66, 1.55)):
        for k in range(12):
            pts = []
            x = rnd.uniform(x0, x1)
            z = rnd.uniform(-0.35, 0.15)
            for s in range(5):
                pts.append(Vector((x, 0.875 + rnd.uniform(0, 0.03), z)))
                x = min(max(x + rnd.uniform(-0.12, 0.12), x0), x1)
                z = min(max(z + rnd.uniform(-0.12, 0.12), -0.4), 0.2)
            lib.tube('DeskCable%d%d' % (side + 1, k), pts, rnd.uniform(0.011, 0.016), mats[rnd.randrange(len(mats))], g)
    return g


BULBS = [(-380, 420), (-250, 230), (18, 170), (358, 33), (538, 8), (873, 35), (1068, 12), (1408, 37), (1622, 7), (1652, 380), (1640, 560), (1880, 420), (2030, 250)]


def fairy_lights(parent):
    g = lib.empty('FairyLights', (0, 1.8, -0.6), parent)
    wire = lib.mat('FairyWire', '#3B3A36', 0.6)
    bulb = lib.mat('FairyBulb', '#FFD39A', 0.3, emit='#FFB04A', strength=5.0)
    pts = []
    for px, py in BULBS:
        p, _ = brain.wall_hit(px, py, 0.16)
        pts.append(p)
    route = []
    for a, b in zip(pts, pts[1:]):
        route += [a, (a + b) / 2 - Vector((0, 0.08, 0))]
    route.append(pts[-1])
    lib.tube('FairyWire', route, 0.004, wire, g, bevel_res=1)
    for i, p in enumerate(pts):
        lib.sphere('Bulb%02d' % i, 0.017, bulb, Frame(p), g, seg=14, rings=8)
    g['bulbs_godot'] = [list(p) for p in pts]
    return g, pts


# --- props -----------------------------------------------------------------------------------------

def books(parent):
    """Book stack: spines face the camera where the concept has them; the books run on past its left edge
    (seen on ultrawide screens). Returns the point on top of the stack."""
    g = lib.empty('Books', (-0.95, 1.0, -0.2), parent)
    spines = [
        ((0, 372, 192, 405), '#D9A04C', ''), ((0, 405, 212, 445), '#2F6470', 'PROCRASTINATION'),
        ((0, 445, 215, 482), '#D86E73', 'OVERTHINKING'), ((0, 482, 218, 518), '#C9473D', 'RANDOM FACTS'),
        ((0, 518, 215, 563), '#7EA04A', 'SNACK IDEAS'), ((0, 563, 240, 610), '#3A63A8', 'EMERGENCY MOTIVATION'),
        ((0, 610, 200, 660), '#C9A464', ''), ((0, 660, 190, 710), '#B85B4E', ''),
    ]
    depth = 1.12
    boxes = []
    for bbox, col, title in spines:
        x0, y0, x1, y1 = bbox
        a, b = at_depth(x0, y0, depth), at_depth(x1, y1, depth)
        boxes.append((a, b, abs(a.y - b.y) * 0.97))
    y = DESK_TOP + 0.0005                                    # stack from the desk up, no overlaps
    top = None
    for i in reversed(range(len(spines))):
        a, b, h = boxes[i]
        ext = 0.28 + 0.05 * (i % 3)
        jog = 0.012 * ((i * 7) % 3 - 1)
        d = 0.16 + 0.012 * (i % 2)
        zf = a.z + jog * 0.5
        x0, x1 = _book_span(a.x - ext + jog, b.x + 0.01 + jog, y, h, zf, d)
        props.book('Book%d' % i, x0, x1, y + h / 2, h, zf, d, spines[i][1], spines[i][2], g, i,
                   label_x0=a.x + 0.01)
        y += h
        if i == 0:
            top = Vector((a.x + 0.075, y, a.z - 0.03))   # clear left end, in front of the wall notes
    return g, top


def _book_span(x0, x1, y, h, zf, d):
    """Trim a book so its left end stays clear of the brain folds and its right end clear of the left monitor."""
    corners = [(yy, zz) for yy in (y + 0.002, y + h - 0.002) for zz in (zf, zf - d)]
    while x1 - x0 > 0.14 and not all(brain.inside(Vector((x0 - brain.DEPTH - 0.02, yy, zz))) for yy, zz in corners):
        x0 += 0.01
    box = hw.casing_box('LeftPanel', 0.012)
    while x1 - x0 > 0.14 and any(box(Vector((x1, yy, zz))) for yy, zz in corners):
        x1 -= 0.01
    return x0, x1


def monitor_top(name, along=0.0, back=0.06):
    """Point on top of a side monitor's casing: `along` metres across its width (from centre), `back` behind the bezel."""
    spec = hw.LAYOUT[name]
    f = Frame(spec['pos'], spec['deg'])
    return f.at((along, hw.casing_top(name) + 0.001, -back))


DESK_TOP, TRAY_TOP = 0.86, 0.89
AM_SHIFT, AM_YAW = 0.03, -25.0       # answering machine: x offset from the pal's old spot, yaw (deg)
MACHINE = None


def support(x, z):
    """Height of the surface under (x, z): the tray in front of the console, else the desk."""
    return TRAY_TOP if abs(x) < 0.675 and 0.19 < z < 0.53 else DESK_TOP


def seat(p, lift=0.0005):
    """Put a base point on the surface below it."""
    return Vector((p.x, support(p.x, p.z) + lift, p.z))


def on_ground(bbox, y, shrink=0.94):
    c, w, h = _fit(bbox, ground_y=y, shrink=shrink)
    return Vector((c.x, y, c.z)), w, h


def trinkets(parent, shelf_top, books_top):
    """Shelf items sit where the concept has them, lifted with the shelf for the chosen layout.
    Tall items that would leave a 16:9 frame sit on the side monitors and the book stack instead."""
    g = lib.empty('Trinkets', (0, shelf_top, -0.62), parent)
    s = hw.CONCEPT_SHELF_TOP
    up = Vector((0, shelf_top - s, 0))
    base, w, h = on_ground((657, 110, 732, 146), s)
    props.radio('Radio', base + up, w * 0.9, g)
    base, w, h = on_ground((768, 66, 830, 146), s, 0.9)
    props.alien('Alien', base + up, h, g)
    base, w, h = on_ground((1080, 86, 1116, 146), s)
    props.valve('Valve', base + up, h, g)
    _, w, h = on_ground((854, 47, 1082, 142), s)
    props.meter_box('MentalBandwidth', monitor_top('LeftPanel', 0.02), w * 0.75, g, 32)
    _, w, h = on_ground((1107, -10, 1316, 148), s + 0.02)
    props.cat_tv('CatTV', monitor_top('RightPanel', -0.03), w * 0.6, g, -32)
    c, w, h = _fit((285, 18, 405, 188), min(1.45, wall_depth(345, 100, 0.22)), shrink=0.88)
    props.banana('Banana', books_top, h * 0.8, g, 20)
    print('BANANA', books_top, h)
    c, w, h = _fit((618, -10, 702, 62), wall_depth(660, 26, 0.12))
    props.speaker('Speaker', c, w / 2, g)
    dd = min(1.6, wall_depth(746, 76, 0.25))
    c = at_depth(746, 76, dd) + up
    r = 40 * m_per_px(dd) * 0.97
    props.disco_ball('DiscoBall', c, r, g)
    lib.tube('DiscoString', [c + Vector((0, r * 1.1, 0)), c + Vector((0, r + 0.25, -0.05))], 0.002,
             lib.mat('FairyWire', '#3B3A36'), g)
    return g


def desk_props(parent):
    g = lib.empty('DeskProps', (0, 0.9, 0), parent)
    y = 0.865
    base, w, h = on_ground((182, 586, 332, 818), y, 0.95)
    # The TODAY notebook stand took the left desk front (2026-10-15): the can moves back left (seen on ultrawide),
    # the donut beside it (both seen on ultrawide).
    props.can('BrainFuel', seat(Vector((-0.95, 0, 0.12))), h, g)
    base, w, h = on_ground((22, 766, 246, 900), y, 0.86)
    props.donut('Donut', seat(Vector((-1.0, 0, 0.3))), w, g)
    base, w, h = on_ground((1472, 702, 1615, 905), y, 0.95)
    props.mug('Mug', seat(Vector((0.625, 0, 0.3))), h * 0.8, g)
    base, w, h = on_ground((1352, 600, 1662, 735), 0.93)
    props.lever_box('LeverBox', seat(base + Vector((0.205, 0, -0.08))), w * 0.85, h, g)
    # Octopus and voxel pal sit on a crate behind the console's right end.
    ob, ow, oh = on_ground((1140, 458, 1312, 590), 0.95, 0.95)
    pb, pw, ph = on_ground((1302, 497, 1378, 612), 0.95, 0.95)
    ob, pb = ob + Vector((0.05, 0, -0.08)), pb + Vector((0.11, 0, -0.08))
    # The answering machine takes the voxel pal's spot on the crate (2026-10-15); the pal stands on the machine.
    am_base = Vector((pb.x + AM_SHIFT, ob.y, pb.z - 0.02))
    props.crate('Crate', Vector(((ob.x + am_base.x + 0.1) / 2 - 0.02, DESK_TOP + 0.0005, am_base.z - 0.035)),
                abs(am_base.x + 0.1 - ob.x) + 0.15, 0.25, ob.y - DESK_TOP - 0.0005, g)
    props.octopus('Octopus', ob, ow * 0.88, g)
    global MACHINE
    MACHINE = answering_machine.build(g, am_base, AM_YAW)[0], am_base, AM_YAW
    a = math.radians(AM_YAW)
    lx, lz = 0.055, -0.05                                  # back-right of the machine top
    props.pixel_pal('PixelPal', am_base + Vector((lx * math.cos(a) + lz * math.sin(a), answering_machine.H,
                                                  -lx * math.sin(a) + lz * math.cos(a))), ph * 0.85, g)
    base, w, h = on_ground((1140, 897, 1193, 941), 0.89)
    props.badge('SmileyBadge', seat(Vector((0.55, 0, 0.47)), w * 0.42), w, g)
    for i, (bbox, seed, shift) in enumerate([((100, 580, 197, 676), 1, (0, 0, 0)), ((1372, 715, 1480, 830), 2, (0.19, 0, 0.22))]):
        base, w, h = on_ground(bbox, y, 0.97)
        props.crumple('Crumple%d' % i, seat(base + Vector(shift)), w / 2, g, seed)
    base, w, h = on_ground((1352, 795, 1486, 925), y, 0.97)
    lean = math.radians(62)
    f = props.face_cam(seat(base + Vector((-0.05, 0, 0.05)), h * 0.95 / 2 * math.cos(lean) + 0.012), 12).child(
        (0, 0, 0), (-62, 0, 10))
    props.folded_note('ProgressPaper', f, w * 0.95, h * 0.95, 'PROGRESS\n>\nPERFECTION', g, 7)
    return g


def edge_dressing(parent):
    """Modelled clutter for what 21:9 (sides) and 4:3 (desk front) show beyond the concept frame."""
    g = lib.empty('EdgeDressing', (0, 0.9, 0), parent)
    rnd = random.Random(21)
    y = 0.86
    books = ['#D9A04C', '#2F6470', '#D86E73', '#7EA04A', '#3A63A8', '#C9473D']
    # Right-hand book pile and a plant-less pot of pens.
    h0 = y
    for i in range(5):
        h = rnd.uniform(0.035, 0.055)
        lib.box('PileBook%d' % i, (rnd.uniform(0.22, 0.28), h, rnd.uniform(0.16, 0.2)), lib.mat('Book%d' % (i + 10), books[i], 0.7),
                Frame((1.32 + rnd.uniform(-0.02, 0.02), h0 + h / 2, -0.05), (0, rnd.uniform(-12, 12), 0)), g, bevel=0.006)
        h0 += h
    cup = Frame((1.25, y, 0.25))
    lib.slab('PenCup', circle(0.045, 24), 0.11, 0.006, lib.mat('PenCup', '#2F6470', 0.55), cup.child((0, 0, 0), (-90, 0, 0)), g,
             holes=[list(reversed(circle(0.038, 24)))])
    for k, col in enumerate(['#E8487F', '#2F80DD', '#F2A332', '#4CC04F']):
        a = k * 1.6
        tip = cup.at((0.02 * math.cos(a), 0.17, 0.02 * math.sin(a)))
        lib.tube('Pen%d' % k, [cup.at((0.015 * math.cos(a), 0.01, 0.015 * math.sin(a))), tip], 0.006,
                 lib.mat('Pen%d' % k, col, 0.45), g, res=2)
    # Left: a second crumpled pile and a snack wrapper.
    for i, (x, z, r) in enumerate([(-1.35, 0.1, 0.06), (-1.42, -0.12, 0.05), (1.45, 0.42, 0.05), (-1.2, 0.42, 0.045)]):
        props.crumple('EdgeCrumple%d' % i, seat(Vector((x, 0, z))), r, g, 10 + i)
    # Desk front (4:3): pencils, a ruler, an eraser, a sticky pad, crumbs and coffee rings, on the tray top.
    y = 0.89
    for k, (x, z, yaw, col) in enumerate([(-0.52, 0.42, 70, '#F2C94C'), (-0.42, 0.47, 100, '#9A58C6'), (0.4, 0.45, 60, '#D4473A'),
                                          (1.12, 0.32, 115, '#2F80DD')]):
        f = Frame((x, y + 0.008, z), (0, yaw, 0))
        lib.tube("Pencil%d" % k, [f.at((-0.06, 0, 0)), f.at((0.06, 0, 0))], 0.006, lib.mat('Pencil%d' % k, col, 0.5), g, res=2)
    lib.box('Ruler', (0.3, 0.004, 0.035), lib.mat('Ruler', '#E9D9A6', 0.6), Frame((0.32, y + 0.002, 0.5), (0, -8, 0)), g)
    lib.box('Eraser', (0.05, 0.018, 0.025), lib.mat('Eraser', '#F29684', 0.8), Frame((-0.3, y + 0.009, 0.47), (0, 25, 0)), g, bevel=0.004)
    lib.box('StickyPad', (0.09, 0.02, 0.09), lib.mat('StickyPad', '#FECF82', 0.85), Frame((0.85, 0.87, 0.48), (0, -15, 0)), g, bevel=0.003)
    stain = lib.mat('CoffeeRing', '#8A5A3A', 0.6)
    for k, (x, z, r) in enumerate([(0.5, 0.24, 0.04), (-0.6, 0.48, 0.035)]):
        lib.slab('CoffeeRing%d' % k, circle(r, 28), 0.001, 0.0, stain, Frame((x, y + 0.0005, z), (-90, 0, 0)), g,
                 holes=[list(reversed(circle(r - 0.006, 28)))])
    crumb = lib.mat('Crumb', '#B9773F', 0.8)
    for k in range(14):
        p = Vector((rnd.uniform(-0.62, -0.35), y + 0.004, rnd.uniform(0.3, 0.5)))
        lib.sphere('Crumb%d' % k, rnd.uniform(0.004, 0.008), crumb, Frame(p), g, seg=6, rings=4, smooth=False)
    return g


def frame_tape(parent):
    g = lib.empty('Tape', (0, 1.3, -0.55), parent)
    for name, border, spots in (
            ('FrontScreen', (0.0375, 0.03), [(-1, 1, 20), (1, 1, -25), (-1, -1, -15), (1, -1, 30), (-0.35, 1, 5)]),
            ('LeftPanel', (0.017, 0.017), [(1, 0.9, -30), (1, -0.2, 10), (-1, -0.9, 20)]),
            ('RightPanel', (0.017, 0.017), [(-1, 1, 25), (1, 1, -20), (-1, -0.7, 0)])):
        spec = hw.LAYOUT[name]
        w, h = spec['size']
        f = Frame(spec['pos'], spec['deg'])
        for fx, fy, a in spots:
            hw.tape(g, f, (fx * (w / 2 + border[0]), fy * (h / 2 + border[1]), 0.024), (0.06, 0.04), a)
    for x in (-0.36, -0.12, 0.12, 0.36):
        hw.tape(g, hw.DIALS, (x, -0.09, 0.006), (0.045, 0.03), random.Random(int(x * 100)).uniform(-20, 20))
    return g


def build(root, shelf_top):
    dressing = lib.empty('Dressing', (0, 1.2, -0.3), root)
    paper.notes(dressing)
    paper.notebook(dressing)
    cables(dressing)
    _, bulbs = fairy_lights(dressing)
    _, books_top = books(dressing)
    trinkets(dressing, shelf_top, books_top)
    edge_dressing(dressing)
    desk_props(dressing)
    # frame_tape(dressing): removed (user 2026-10-14: no tape that holds nothing).
    return bulbs
