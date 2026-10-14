"""Screens, gauge panel, console and desk. Anchors follow the concept layout (see LAYOUT)."""
import math

import bmesh
import numpy as np
from mathutils import Vector

import lib
from lib import UPF, Frame, rrect, circle

# Screen anchors fitted to the concept from the game camera (centre, size, rotation degrees).
LAYOUT = {
    'FrontScreen': {'pos': (0.0, 1.33, -0.58), 'size': (1.12, 0.49), 'deg': (0, 0, 0)},
    'LeftPanel': {'pos': (-0.77, 1.265, -0.38), 'size': (0.33, 0.42), 'deg': (0, 25, -4)},
    'RightPanel': {'pos': (0.79, 1.262, -0.38), 'size': (0.33, 0.40), 'deg': (0, -27, 3)},
}
CONSOLE = Frame((0, 0.95, 0.1), (18, 0, 0))     # game Console node
DIALS = Frame((0, 0.955, -0.59))                  # game GaugeDials node
DIAL_X = [-0.48, -0.24, 0.0, 0.24, 0.48]
GAUGES = ['Coordination', 'Confidence', 'Balance', 'Focus', 'Embarrassment']

C = {
    'housing': '#3E5250', 'housing_dark': '#2E3B3A', 'side_frame': '#B4B09D', 'panel': '#4A5755',
    'face': '#F3E5C8', 'steel': '#C4C0B5', 'needle': '#D23B2F', 'red_zone': '#D9473A', 'beige': '#B7A88C',
    'inset': '#4A5250', 'screw': '#A39D90', 'copper': '#B8763F', 'tape': '#D2CBB4', 'desk': '#7B6B5B',
    'tray': '#4C5654', 'space': '#E2402F', 'ring': '#E9A23B', 'rubber': '#2F3434', 'joy': '#2FA6A3',
    'undo': '#9A58C6', 'distract': '#35B6AA', 'screen': '#1E2A31',
    'keys': ['#E8487F', '#4CC04F', '#2F80DD', '#F2A332'],
}


def M(key, rough=0.6, metal=0.0):
    return lib.mat(key, C[key], rough, metal)


def screw(parent, frame, pos, r=0.009, mat=None):
    f = frame.child(pos)
    return lib.slab('Screw', circle(r, 12), 0.006, 0.003, mat or M('screw', 0.35, 0.6), f, parent, bevel_res=2)


def tape(parent, frame, pos, size=(0.05, 0.035), angle=0.0):
    f = frame.child(pos, (0, 0, angle))
    return lib.box('Tape', (size[0], size[1], 0.002), M('tape', 0.55), f.child((0, 0, 0.001)), parent)


# --- screens -------------------------------------------------------------------------------------

def screen_housing(root, name, main=False):
    spec = LAYOUT[name]
    w, h = spec['size']
    f = Frame(spec['pos'], spec['deg'])
    group = lib.empty(name, spec['pos'], root)
    group['screen_size'] = list(spec['size'])
    group['screen_rotation_deg'] = list(spec['deg'])
    if main:
        side, top, bottom, depth = 0.075, 0.06, 0.035, 0.075
        frame_mat, back_mat = M('housing', 0.5), M('housing_dark', 0.6)
    else:
        side, top, bottom, depth = 0.034, 0.034, 0.034, 0.055
        frame_mat, back_mat = M('side_frame', 0.5), M('housing', 0.55)
    ow, oh = w + 2 * side, h + top + bottom
    oy = (top - bottom) / 2
    outer = [(x, y + oy) for x, y in rrect(ow, oh, 0.045 if main else 0.03, 6)]
    inner = list(reversed(rrect(w + 0.004, h + 0.004, 0.022 if main else 0.016, 5)))
    lib.slab(name + 'Frame', outer, depth, 0.016, frame_mat, f.child((0, 0, -depth + 0.022)), group, holes=[inner])
    # Deep back shell so the monitor reads as a chunky box; side monitors show a dark casing rim around the bezel.
    back_d = 0.12 if main else 0.17
    grow = 0.0 if main else 0.035
    lib.slab(name + 'Back', rrect(ow - 0.02 + grow, oh - 0.02 + grow, 0.045, 5), back_d, 0.03, back_mat,
             f.child((0, oy, -depth + 0.022 - back_d + (0.01 if main else -0.004))), group)
    # Dark glass bezel just behind the live screen plane (never in front of it).
    lib.box(name + 'Glass', (w + 0.01, h + 0.01, 0.004), M('screen', 0.3), f.child((0, 0, -0.006)), group)
    for sx in (-1, 1):
        for sy in (-1, 1):
            screw(group, f, (sx * (w / 2 + side / 2), sy * (h / 2 + (top if sy > 0 else bottom) / 2) + 0, 0.022),
                  0.0075 if main else 0.006)
    return group, f


def shelf(root):
    """Ledge on top of the main housing where the trinkets sit."""
    spec = LAYOUT['FrontScreen']
    y = spec['pos'][1] + spec['size'][1] / 2 + 0.06
    f = Frame((0, y, -0.66), UPF)
    return lib.slab('Shelf', rrect(1.30, 0.26, 0.04, 5), 0.035, 0.012, M('housing', 0.5), f, root), y + 0.035


# --- gauges --------------------------------------------------------------------------------------

def dial_face_image(danger_high):
    n = 256
    yy, xx = np.mgrid[0:n, 0:n]
    cx = cy = (n - 1) / 2
    r = np.hypot(xx - cx, yy - cy) / (n / 2)
    ang = np.degrees(np.arctan2(xx - cx, cy - yy))      # 0 = up, clockwise positive
    img = np.ones((n, n, 3)) * np.array(lib.srgb(C['face']))
    zone = (r > 0.62) & (r < 0.8) & ((ang > 70) & (ang < 125) if danger_high else (ang < -70) & (ang > -125))
    img[zone] = lib.srgb(C['red_zone'])
    for a in np.linspace(-125, 125, 11):
        tick = (np.abs(ang - a) < (2.2 if int(round(a)) % 50 == 0 else 1.2)) & (r > 0.66) & (r < 0.84)
        img[tick] = lib.srgb('#3A3532')
    img[r > 0.97] = lib.srgb('#D8C9AA')
    return lib.image_from_array('DialFace' + ('High' if danger_high else 'Low'), img)


def gauges(root):
    group = lib.empty('GaugeHousing', DIALS.o, root)
    lib.slab('GaugePanel', rrect(1.26, 0.22, 0.03, 4), 0.05, 0.012, M('panel', 0.55), DIALS.child((0, 0, -0.05)), group)
    faces = {hi: lib.mat('DialFace' + str(hi), C['face'], 0.45, image=dial_face_image(hi)) for hi in (False, True)}
    needles = lib.empty('Needles', DIALS.o, group)
    for i, (x, name) in enumerate(zip(DIAL_X, GAUGES)):
        f = DIALS.child((x, 0, 0))
        lib.slab(name + 'Bezel', circle(0.078, 40), 0.03, 0.01, M('steel', 0.32, 0.65), f.child((0, 0, -0.012)), group,
                 holes=[list(reversed(circle(0.064, 40)))])
        face = lib.slab(name + 'Face', circle(0.066, 40), 0.004, 0.0, faces[name == 'Embarrassment'],
                        f.child((0, 0, 0.0)), group)
        _planar_uvs(face, f, 0.066)
        pivot = f.at((0, 0, 0.008))
        nf = Frame(pivot)
        bm = bmesh.new()
        pts = [(-0.004, -0.008), (0.004, -0.008), (0.0016, 0.055), (-0.0016, 0.055)]
        vs = [bm.verts.new(nf.at((x2, y2, 0))) for x2, y2 in pts]
        bm.faces.new(vs)
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.002)
        needle = lib.from_bmesh(name + 'Needle', bm, M('needle', 0.4), needles, pivot=pivot, smooth=False)
        needle['rotation_axis'] = 'local +Z (Godot)'
        lib.slab(name + 'Cap', circle(0.009, 16), 0.008, 0.004, M('needle', 0.4), Frame(pivot), needle, bevel_res=2)
        # Taped paper label across the lower face; gameplay/art scene writes the full name on it.
        paper = f.child((0, -0.05, 0.021), (0, 0, (-3, 2, -2, 3, -1)[i]))
        lib.box(name + 'Paper', (0.215, 0.034, 0.002), lib.mat('LabelPaper', '#F4ECDC', 0.85), paper, group)
        for sx in (-1, 1):
            hw_tape = paper.child((sx * 0.104, 0.007, 0.002), (0, 0, sx * 12))
            lib.box('LabelTape', (0.028, 0.022, 0.0015), M('tape', 0.55), hw_tape, group)
        # Copper rivets between dials, like the concept.
        if i < 4:
            screw(group, DIALS, (x + 0.12, 0.08, 0.0), 0.007, M('copper', 0.35, 0.6))
            screw(group, DIALS, (x + 0.12, -0.08, 0.0), 0.007, M('copper', 0.35, 0.6))
    return group


def _planar_uvs(o, frame, radius):
    me = o.data
    uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    inv = frame.m.inverted()
    for loop in me.loops:
        p = inv @ (lib.G(o.matrix_world @ me.vertices[loop.vertex_index].co) - frame.o)
        uv.data[loop.index].uv = (0.5 + p.x / (2 * radius), 0.5 + p.y / (2 * radius))


# --- console -------------------------------------------------------------------------------------

def console(root):
    group = lib.empty('ConsoleHousing', CONSOLE.o, root)
    top = CONSOLE.child((0, 0, 0), UPF)          # local +Z = console normal; local +Y = toward the back
    # Main beige slab: x -0.64..0.64, depth z -0.18..0.14 (local console z; +z toward the camera).
    outline = [(x, -z) for x, z in [(-0.64, 0.14), (0.62, 0.14), (0.70, 0.02), (0.66, -0.18), (-0.66, -0.18)]]
    outline = _round_poly(outline, 0.035)
    lib.slab('ConsoleSlab', outline, 0.07, 0.018, M('beige', 0.62), top.child((0, 0, -0.07)), group)
    rim = _round_poly([(x * 1.0, y) for x, y in [(-0.665, -0.155), (0.645, -0.155), (0.725, -0.02), (0.685, 0.195), (-0.685, 0.195)]], 0.04)
    lib.slab('ConsoleRim', rim, 0.07, 0.02, M('housing', 0.55), top.child((0, 0, -0.085)), group)
    for x, y, a in ((-0.6, -0.15, 15), (-0.05, -0.16, -10), (0.15, 0.12, 25), (0.62, -0.12, -30), (-0.45, 0.13, 8),
                    (0.36, 0.165, -12)):
        tape(group, top, (x, y, 0.001), (0.07, 0.035), a)
    # Front skirt down to the tray.
    lib.box('ConsoleSkirt', (1.30, 0.12, 0.05), M('beige', 0.62), CONSOLE.child((0, -0.09, 0.115)), group, bevel=0.012)
    # Left inset holding the keys.
    lib.slab('KeyInset', rrect(0.44, 0.17, 0.025, 4), 0.012, 0.004, M('inset', 0.6), top.child((-0.29, -0.005, -0.004)), group)
    lib.slab('KeyWell', rrect(0.37, 0.10, 0.02, 4), 0.016, 0.004, M('rubber', 0.8), top.child((-0.287, -0.02, 0.0)), group)
    # SPACE ring base.
    lib.slab('SpaceRing', circle(0.088, 48), 0.03, 0.012, M('ring', 0.45), top.child((0.028, 0.053, 0.0)), group,
             holes=[list(reversed(circle(0.067, 48)))])
    lib.slab('SpaceWell', circle(0.072, 40), 0.012, 0.004, M('rubber', 0.8), top.child((0.028, 0.053, 0.0)), group)
    # Right inset where the swappable slot lives (game slot at x 0.30).
    lib.slab('SlotInset', rrect(0.30, 0.25, 0.03, 4), 0.012, 0.004, M('inset', 0.6), top.child((0.30, 0.01, -0.004)), group)
    rim = [(x, y) for x, y in rrect(0.30, 0.25, 0.03, 4)]
    lib.slab('SlotRim', rim, 0.016, 0.005, M('housing_dark', 0.6), top.child((0.30, 0.01, 0.0)), group,
             holes=[list(reversed(rrect(0.26, 0.21, 0.02, 4)))])
    # Right plate for UNDO / DISTRACT (positions read from the concept on the console plane).
    lib.slab('ButtonPlate', _round_poly([(0.38, 0.16), (0.62, 0.16), (0.66, -0.13), (0.38, -0.13)], 0.03), 0.014, 0.005,
             M('inset', 0.6), top.child((0, 0, -0.004)), group)
    for name, x, z, col in (('UndoButton', 0.459, -0.053, 'undo'), ('DistractButton', 0.468, 0.084, 'distract')):
        f = top.child((x, -z, 0.006))
        lib.slab(name + 'Rim', circle(0.056, 32), 0.016, 0.006, M('rubber', 0.8), f, group)
        lib.slab(name, circle(0.047, 32), 0.028, 0.012, M(col, 0.4), f.child((0, 0, 0.008)), group)
    # Screws around the slab edge.
    for x in (-0.6, -0.36, -0.06, 0.12, 0.47, 0.6):
        screw(group, top, (x, -0.155, 0.0))
        screw(group, top, (x, 0.12, 0.0))
    for x, y in ((-0.5, -0.11), (-0.12, -0.11), (0.155, 0.1), (0.155, -0.08)):
        screw(group, top, (x, -y, 0.0))
    # Small knobs (decor) like the concept.
    for x, y in ((-0.12, 0.085), (0.285, 0.15)):
        lib.slab('Knob', circle(0.014, 20), 0.03, 0.006, M('rubber', 0.7), top.child((x, y, 0.0)), group)
    return group


def _round_poly(pts, r, seg=4):
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        a, b = (p0 - p1).normalized(), (p2 - p1).normalized()
        s, e = p1 + a * r, p1 + b * r
        for k in range(seg + 1):
            t = k / seg
            q = (1 - t) ** 2 * s + 2 * (1 - t) * t * p1 + t * t * e
            out.append((q.x, q.y))
    return out


def controls(root):
    """Preview versions of the gameplay controls, at the game's local anchors. Gameplay decides whether to adopt."""
    group = lib.empty('Controls', CONSOLE.o, root)
    top = CONSOLE.child((0, 0, 0), UPF)
    keys = lib.empty('LeftKeys', CONSOLE.at((-0.287, 0, 0.018)), group)
    for i, (letter, col) in enumerate(zip('ASDF', C['keys'])):
        f = top.child((-0.414 + i * 0.085, -0.018, 0.0))
        k = lib.slab('Key' + letter, rrect(0.074, 0.072, 0.014, 4), 0.032, 0.008,
                     lib.mat('Key' + letter, col, 0.45), f, keys, pivot=f.o)
    btn = lib.empty('PanicButton', CONSOLE.at((0.028, 0, -0.053)), group)
    f = top.child((0.028, 0.053, 0.012))
    lib.slab('SpaceCap', circle(0.064, 40), 0.042, 0.02, M('space', 0.38), f, btn, pivot=f.o)
    joy = lib.empty('Joystick', CONSOLE.at((0.277, 0, 0.021)), group)
    jf = top.child((0.277, -0.021, 0.0))
    lib.slab('JoyBase', circle(0.065, 36), 0.025, 0.01, M('rubber', 0.75), jf, joy)
    lib.slab('JoyBoot', circle(0.035, 24), 0.03, 0.014, M('rubber', 0.85), jf.child((0, 0, 0.02)), joy)
    stick = lib.empty('Stick', jf.o, joy)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.011, radius2=0.009, depth=0.12)
    lib.transform_bm(bm, jf.child((0, 0, 0.07)))
    lib.from_bmesh('Shaft', bm, M('rubber', 0.5), stick, pivot=jf.o)
    lib.sphere('Knob', 0.034, M('joy', 0.35), jf.child((0, 0, 0.14)), stick)
    return group


def desk(root):
    group = lib.empty('Desk', (0, 0.86, 0.1), root)
    lib.slab('DeskTop', rrect(2.6, 0.9, 0.08, 5), 0.06, 0.016, M('desk', 0.75), Frame((0, 0.80, 0.0), UPF), group)
    # Dark tray in front of the console where the notebook and list lie.
    lib.slab('Tray', rrect(1.35, 0.34, 0.04, 4), 0.03, 0.01, M('tray', 0.65), Frame((0.0, 0.86, 0.36), UPF), group)
    # Deck connecting the console back to the gauge panel (hidden from the seat, seen in the reveal).
    lib.slab('Deck', rrect(1.3, 0.46, 0.04, 4), 0.04, 0.01, M('housing_dark', 0.7), Frame((0, 0.80, -0.36), UPF), group)
    return group


def preview_screens():
    """Preview-only screen quads showing the concept's screen content (game renders live content here)."""
    g = lib.empty('PreviewScreens')
    m = lib.mat('ScreenPrint', '#000000', 0.4, emit_image=lib.concept_image(), strength=1.0)
    for name, spec in LAYOUT.items():
        w, h = spec['size']
        f = Frame(spec['pos'], spec['deg'])
        corners = [f.at((sx * w / 2, sy * h / 2, 0)) for sx, sy in ((-1, 1), (1, 1), (1, -1), (-1, -1))]
        px = [lib.project(c) for c in corners]
        lib.decal(name + 'Preview', px, (f.o, f.dir((0, 0, 1))), g, material=m)
    return g


def build(root):
    housings = lib.empty('ScreenHousings', (0, 0, 0), root)
    for name in LAYOUT:
        screen_housing(housings, name, main=name == 'FrontScreen')
    sh, shelf_top = shelf(housings)
    gauges(root)
    console(root)
    controls(root)
    desk(root)
    return shelf_top
