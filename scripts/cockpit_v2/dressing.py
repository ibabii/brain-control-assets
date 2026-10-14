"""Clutter: cables, fairy lights, paper notes and props. Positions are read from concept pixels.

Printed items (notes, labels, book spines, can, mug, trinkets) are textured straight from the concept image,
projected from the game camera, so the seated view matches the approved render. Their geometry is real, so they
keep depth and parallax for the reveal.
"""
import math
import random

import bmesh
from mathutils import Vector

import brain
import hardware as hw
import lib
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


def print_faces(o, body, threshold=0.25):
    """Faces turned toward the camera get the concept print; the rest get `body`."""
    me = o.data
    me.materials.clear()
    me.materials.append(lib.print_mat())
    me.materials.append(body)
    mw = o.matrix_world
    for p in me.polygons:
        c = lib.G(mw @ p.center)
        n = (lib.G(mw.to_3x3() @ p.normal)).normalized()
        p.material_index = 0 if n.dot((lib.CAM - c).normalized()) > threshold else 1
    lib.camera_uvs(o)
    return o


# --- proxies: simple solids fitted to a concept bounding box ----------------------------------------

def _fit(bbox, depth=None, ground_y=None, shrink=0.94):
    x0, y0, x1, y1 = bbox
    if ground_y is not None:
        base = lib.unproject((x0 + x1) / 2, y1 - (y1 - y0) * 0.06, ground((ground_y)))
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


def proxy(name, kind, bbox, parent, depth=None, ground_y=None, deep=None, body='#ffffff', yaw=0.0, threshold=-1.0,
          shrink=0.94):
    c, w, h = _fit(bbox, depth, ground_y, shrink)
    d = deep if deep is not None else w
    f = Frame(c, (0, yaw, 0))
    if kind == 'box':
        bm = lib.box_bm((w, h, d), f)
    elif kind == 'cyl':
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=w / 2, radius2=w / 2, depth=h)
        lib.transform_bm(bm, f.child((0, 0, 0), (90, 0, 0)))
    elif kind == 'ball':
        bm = lib.sphere_bm(1, f, (w / 2, h / 2, d / 2))
    elif kind == 'torus':
        bm = _torus(w / 2, h, f)
    elif kind == 'disc':
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=w / 2, radius2=w / 2, depth=d)
        lib.transform_bm(bm, f)
    o = lib.from_bmesh(name, bm, lib.print_mat(), parent, None, smooth=kind in ('cyl', 'ball', 'torus'))
    return print_faces(o, lib.mat('Body_' + name, body, 0.6), threshold)


def _torus(r_outer, height, frame, seg=28, ring=12):
    rt = height / 2
    rm = r_outer - rt
    bm = bmesh.new()
    grid = [[bm.verts.new(frame.at(((rm + rt * math.cos(b)) * math.cos(a), rt * math.sin(b),
                                    (rm + rt * math.cos(b)) * math.sin(a))))
             for b in (2 * math.pi * j / ring for j in range(ring))] for a in (2 * math.pi * i / seg for i in range(seg))]
    for i in range(seg):
        for j in range(ring):
            bm.faces.new([grid[i][j], grid[(i + 1) % seg][j], grid[(i + 1) % seg][(j + 1) % ring], grid[i][(j + 1) % ring]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


# --- paper -------------------------------------------------------------------------------------------

def notes(parent):
    g = lib.empty('Notes', (0, 1.2, -0.5), parent)
    wall = [
        ('Polaroid', [(72, 56), (250, 52), (265, 220), (85, 235)]),
        ('PolaroidTape', [(135, 22), (185, 8), (207, 70), (157, 82)]),
        ('YouGotThis', [(20, 230), (145, 212), (180, 350), (57, 372)]),
        ('ItsFine', [(1360, 97), (1467, 77), (1480, 177), (1372, 192)]),
        ('Chaos', [(1542, 112), (1642, 80), (1652, 275), (1552, 295)]),
        ('MopFloor', [(1495, 345), (1622, 352), (1600, 487), (1468, 478)]),
    ]
    for name, pts in wall:
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        lib.decal(name, pts, wall_plane(cx, cy, 0.32), g)
    lib.decal('SameBrain', [(487, 47), (633, 30), (636, 140), (500, 152)], lib.zplane(-0.5), g)
    lib.decal('HeartSticky', [(1135, 280), (1190, 279), (1191, 357), (1136, 358)], lib.zplane(-0.53), g)
    lib.decal('Smiley', circle_px(547, 187, 16), lib.zplane(-0.555), g)
    heart = [(432, 92), (442, 84), (458, 81), (472, 88), (478, 103), (474, 122), (458, 143), (433, 166), (408, 143),
             (391, 122), (387, 103), (393, 88), (407, 81), (423, 84)]
    lib.decal('SmallStepsHeart', heart, lib.facing(min(1.5, wall_depth(432, 120, 0.22))), g)
    lib.decal('DoTheThing', [(810, 702), (935, 685), (952, 752), (817, 770)], console_plane(0.004), g)
    # The list lies across the console lip onto the tray.
    top = lib.unproject(1050, 728, console_plane(0.004))
    bottom = lib.unproject(1065, 885, ground(0.9))
    lib.decal('TodoList', [(972, 722), (1132, 733), (1152, 892), (985, 882)],
              plane3(top, bottom, bottom + Vector((1, 0, 0))), g)
    # Task note: blank paper; gameplay writes the task on it.
    task_plane = (Vector((-0.74, 1.0, -0.12)), lib.rot((-10, 25, 0)) @ Vector((0, 0, 1)))
    o = lib.decal('TaskNote', [(267, 520), (420, 492), (447, 582), (295, 612)], task_plane, g,
                  material=lib.mat('TaskPaper', '#F7D77E', 0.85))
    o['gameplay'] = 'TaskNote paper: game Label goes on top, same transform as game TaskNote'
    return g


def circle_px(cx, cy, r, n=20):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def notebook(parent):
    g = lib.empty('Notebook', (-0.1, 0.9, 0.3), parent)
    y = 0.905
    page = [(615, 795), (900, 772), (962, 941), (600, 941)]
    world = [lib.unproject(x, yy, ground(y)) for x, yy in page]
    lo = Vector([min(p[i] for p in world) for i in range(3)])
    hi = Vector([max(p[i] for p in world) for i in range(3)])
    centre = (lo + hi) / 2
    lib.slab('Cover', rrect(hi.x - lo.x + 0.03, hi.z - lo.z + 0.03, 0.012, 3), 0.018, 0.004,
             lib.mat('NotebookCover', '#C9786A', 0.7), Frame((centre.x, 0.887, centre.z), UPF), g)
    lib.decal('Page', page, ground(y + 0.002), g)
    return g


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
    (6, 0.14, [(-40, 70, 2.0), (400, 40, 1.98), (800, 25, 2.05), (1200, 40, 1.98), (1720, 70, 2.0)]),
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
    for side, x0, x1 in ((-1, -1.0, -0.62), (1, 0.66, 1.05)):
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


BULBS = [(18, 170), (358, 33), (538, 8), (873, 35), (1068, 12), (1408, 37), (1622, 7), (1652, 380), (1640, 560)]


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
    g = lib.empty('Books', (-0.95, 1.0, -0.2), parent)
    spines = [
        ((-20, 372, 192, 405), '#D9A04C'), ((-20, 405, 212, 445), '#2F6470'), ((-20, 445, 215, 482), '#D86E73'),
        ((-20, 467, 218, 518), '#C9473D'), ((-20, 518, 215, 563), '#7EA04A'), ((-20, 535, 240, 610), '#3A63A8'),
        ((-20, 610, 200, 660), '#C9A464'), ((-20, 660, 190, 710), '#B85B4E'),
    ]
    depth = 1.12
    for i, (bbox, col) in enumerate(spines):
        x0, y0, x1, y1 = bbox
        a, b = at_depth(x0, y0, depth), at_depth(x1, y1, depth)
        w, h = abs(b.x - a.x), abs(a.y - b.y) * 0.98
        c = (a + b) / 2
        bm = lib.box_bm((w * 1.02, h, 0.2), Frame(c + Vector((0, 0, -0.1))))
        o = lib.from_bmesh('Book%d' % i, bm, lib.print_mat(), g, None, smooth=False)
        print_faces(o, lib.mat('Book%d' % i, col, 0.7), -0.2)
    return g


def trinkets(parent, shelf_top):
    g = lib.empty('Trinkets', (0, shelf_top, -0.62), parent)
    s = shelf_top
    proxy('MentalBandwidth', 'box', (854, 47, 1082, 142), g, ground_y=s, deep=0.12, body='#E6DCC6', threshold=0.3)
    proxy('Radio', 'box', (657, 110, 732, 146), g, ground_y=s, deep=0.08, body='#D9A04C', threshold=0.3)
    proxy('Alien', 'ball', (768, 66, 830, 146), g, ground_y=s, deep=0.05, shrink=0.9)
    proxy('Valve', 'cyl', (1080, 86, 1116, 146), g, ground_y=s, body='#C9473D')
    proxy('CatTV', 'box', (1107, -10, 1316, 148), g, ground_y=s + 0.02, deep=0.22, body='#E6DCC6', threshold=0.3)
    proxy('Banana', 'ball', (285, 18, 405, 188), g, depth=min(1.45, wall_depth(345, 100, 0.22)), deep=0.07, shrink=0.88)
    proxy('Speaker', 'disc', (618, -10, 702, 62), g, depth=wall_depth(660, 26, 0.12), deep=0.03, body='#3B3A36')
    dd = min(1.6, wall_depth(746, 76, 0.25))
    c = at_depth(746, 76, dd)
    r = 40 * m_per_px(dd)
    proxy('DiscoBall', 'ball', (706, 36, 786, 116), g, depth=dd, shrink=0.97)
    lib.tube('DiscoString', [c + Vector((0, r, 0)), c + Vector((0, r + 0.25, -0.05))], 0.002,
             lib.mat('FairyWire', '#3B3A36'), g)
    return g


def desk_props(parent):
    g = lib.empty('DeskProps', (0, 0.9, 0), parent)
    y = 0.865
    proxy('BrainFuel', 'cyl', (182, 586, 332, 818), g, ground_y=y, shrink=0.97, threshold=-1)
    proxy('Donut', 'torus', (22, 766, 246, 900), g, ground_y=y, shrink=0.93)
    proxy('Mug', 'cyl', (1472, 702, 1615, 905), g, ground_y=y, shrink=0.97)
    proxy('MugHandle', 'box', (1606, 760, 1672, 860), g, ground_y=y + 0.04, deep=0.02, shrink=0.95)
    proxy('LeverBox', 'box', (1352, 600, 1662, 735), g, ground_y=y, deep=0.22, body='#C9BC9F', threshold=0.3)
    box = g.children[-1]
    front = depth_of(lib.G(box.matrix_world.translation)) - 0.06
    proxy('AnxietyLever', 'cyl', (1474, 535, 1528, 650), g, depth=front, shrink=0.9)
    proxy('HypeLever', 'cyl', (1556, 550, 1606, 665), g, depth=front, shrink=0.9)
    proxy('Octopus', 'ball', (1140, 458, 1312, 590), g, ground_y=0.95, deep=0.16, shrink=0.95)
    proxy('PixelPal', 'box', (1302, 497, 1378, 612), g, ground_y=0.95, deep=0.05, shrink=0.95)
    proxy('ProgressPaper', 'ball', (1352, 795, 1486, 925), g, ground_y=y, deep=0.12, shrink=0.97)
    proxy('SmileyBadge', 'disc', (1140, 897, 1193, 941), g, ground_y=0.89, deep=0.01)
    proxy('Pencil', 'cyl', (900, 875, 1060, 941), g, ground_y=0.91, shrink=0.9)
    for i, bbox in enumerate([(100, 580, 197, 676), (1372, 715, 1480, 830)]):
        proxy('Crumple%d' % i, 'ball', bbox, g, ground_y=y, deep=0.1, shrink=0.97)
    return g


def frame_tape(parent):
    g = lib.empty('Tape', (0, 1.3, -0.55), parent)
    for name, spots in (('FrontScreen', [(-0.58, 0.27, 20), (0.58, 0.27, -25), (-0.6, -0.24, -15), (0.55, -0.25, 30),
                                         (-0.2, 0.3, 5)]),
                        ('LeftPanel', [(0.18, 0.2, -30), (0.17, -0.05, 10), (-0.16, -0.2, 20)]),
                        ('RightPanel', [(-0.17, 0.21, 25), (0.16, 0.22, -20), (-0.18, -0.15, 0)])):
        spec = hw.LAYOUT[name]
        f = Frame(spec['pos'], spec['deg'])
        for x, y, a in spots:
            hw.tape(g, f, (x, y, 0.024), (0.06, 0.04), a)
    for x in (-0.36, -0.12, 0.12, 0.36):
        hw.tape(g, hw.DIALS, (x, -0.09, 0.006), (0.045, 0.03), random.Random(int(x * 100)).uniform(-20, 20))
    return g


def build(root, shelf_top):
    dressing = lib.empty('Dressing', (0, 1.2, -0.3), root)
    notes(dressing)
    notebook(dressing)
    cables(dressing)
    _, bulbs = fairy_lights(dressing)
    books(dressing)
    trinkets(dressing, shelf_top)
    desk_props(dressing)
    frame_tape(dressing)
    return bulbs
