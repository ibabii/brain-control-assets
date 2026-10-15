"""Cassette answering machine on the crate right of the console (contract: interfaces.md, "Intercom, answering
machine, text kit"). Module origin = base centre, +Y up, -Z away from the player; exported on its own as
cockpit/art/answering_machine/answering_machine.glb and instanced by cockpit_art.tscn at the placed transform.
"""
import math

import bmesh
from mathutils import Matrix

import ink
import lib
import props
from lib import UPF, Frame, circle, rrect

W, D, H = 0.2, 0.16, 0.06
# Side profile (z toward the player, y up): flat top, sloped front panel facing the seat.
PROFILE = [(-0.085, 0.0), (0.075, 0.0), (0.075, 0.022), (0.035, H), (-0.085, H)]
SLOPE = -46.5                                    # panel tilt about X (normal ~45 deg up, toward the player)
PANEL = (0.0, 0.041, 0.055)                      # panel centre on the slope
BM_ = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))  # Godot -> Blender basis


def M(key, color, rough=0.6, metal=0.0):
    return lib.mat('Ans_' + key, color, rough, metal)


def _ccw(pts):
    return pts if lib._area(pts) > 0 else list(reversed(pts))


def place(o, frame, parent):
    """Give a mesh built at the origin (Godot local) the frame's position and rotation, so its axes are the node's."""
    o.matrix_world = Matrix.Translation(lib.B(frame.o)) @ (BM_ @ frame.m @ BM_.transposed()).to_4x4()
    lib.set_parent(o, parent)
    return o


def local_slab(name, outline, thick, bevel, mat, z0=0.0, holes=()):
    """Slab in local XY, thickness +Z from z0; node at the origin with no rotation (place() positions it)."""
    return lib.slab(name, outline, thick, bevel, mat, Frame((0, 0, z0)), None, holes=holes, pivot=(0, 0, 0))


def flat_slab(name, outline, thick, bevel, mat, y0=0.0, holes=()):
    """Slab with its thickness along local +Y from y0 (outline x right, outline y = local -Z); node at the origin."""
    return lib.slab(name, outline, thick, bevel, mat, Frame((0, y0, 0), UPF), None, holes=holes, pivot=(0, 0, 0))


def one_glyph(h):
    s = h / 24
    return _ccw([(2.5 * s, -12 * s), (2.5 * s, 12 * s), (-1 * s, 12 * s), (-6.5 * s, 7 * s), (-6.5 * s, 4 * s),
                 (-1.5 * s, 7.5 * s), (-1.5 * s, -12 * s)])


def reel(r):
    return _ccw([((r if i % 2 else r * 0.68) * math.cos(math.pi * i / 6), (r if i % 2 else r * 0.68) * math.sin(math.pi * i / 6))
                 for i in range(12)])


def build(parent, base, yaw):
    """Machine with its base centre at `base`, turned `yaw` degrees about Y. Returns (group, top frame)."""
    f = Frame(base)
    g = lib.empty('AnsweringMachine', base, parent)
    body_m = M('Body', '#4A4F4C', 0.55)
    lib.slab('AnsBody', PROFILE, W, 0.008, body_m, f.child((W / 2, 0, 0), (0, -90, 0)), g)
    top = f.child((0, H, 0), UPF)                 # local XY = top surface (local +Y = away), +Z = up
    # Smoked tape lid with the cassette and the two reels showing through.
    lib.slab('TapeLid', rrect(0.1, 0.07, 0.006), 0.002, 0.0006, M('Lid', '#2A2420', 0.25), top.child((-0.04, 0.02, -0.0005)), g)
    lib.slab('Cassette', rrect(0.085, 0.054, 0.004), 0.002, 0.0005, M('Cassette', '#CFC6B4', 0.6),
             top.child((-0.04, 0.02, 0.001)), g, holes=[list(reversed(circle(0.011, 20, sx * 0.021, 0.004))) for sx in (-1, 1)])
    tape = lib.empty('Tape', top.at((-0.04, 0.02, 0)), g)
    for side, sx in (('ReelL', -1), ('ReelR', 1)):
        o = flat_slab(side, reel(0.0085), 0.0028, 0.0006, M('Reel', '#F2EEE6', 0.45))
        place(o, Frame(top.at((-0.04 + sx * 0.021, 0.024, 0.0005))), tape)   # local Y = world up: gameplay spins about Y
    # Speaker grille, front right of the top.
    c = ink.Canvas(250, 110, '#3A3F3C')
    for i in range(9):
        for j in range(4):
            c.ellipse(((i + 0.5) / 9, (j + 0.5) / 4), 0.07, 0.07, '#16191A')
    props.face_card('AnsGrille', 0.05, 0.022, c, top.child((0.05, -0.012, 0.0012)), g, rough=0.7, thick=0.0015)
    # Sloped front panel: message LED ("1") and the buttons.
    panel = f.child(PANEL, (SLOPE, 0, 0))
    lib.slab('LedWindow', rrect(0.028, 0.026, 0.004), 0.002, 0.0005, M('Led', '#1A1412', 0.3), panel.child((-0.06, 0, -0.0005)), g)
    lamp = local_slab('Lamp', one_glyph(0.018), 0.0018, 0.0004, M('Lamp', '#F0A040', 0.35))
    place(lamp, panel.child((-0.06, 0, 0.0012)), g)
    for name, x, w in (('ButtonStop', -0.022, 0.022), ('ButtonRew', 0.005, 0.022)):
        lib.slab(name, rrect(w, 0.018, 0.004), 0.006, 0.0018, M('Button', '#8C8F86', 0.5), panel.child((x, 0, -0.001)), g)
    # Play: single-surface cap, origin at its top-face centre, local -Y = press direction (into the panel).
    cap = flat_slab('Button_Play', rrect(0.036, 0.02, 0.005), 0.008, 0.0022, M('Play', '#E2D3B5', 0.45), y0=-0.008)
    mark = flat_slab('PlayMark', _ccw([(-0.004, -0.005), (0.006, 0), (-0.004, 0.005)]), 0.0008, 0.0002,
                     M('PlayMark', '#3A3532', 0.6), y0=-0.0003)
    press = panel.child((0.047, 0, 0.007), (90, 0, 0))     # node +Y = panel normal, so the press is local -Y
    place(cap, press, g)
    place(mark, press, cap)
    # Coiled cord off the back into the wall clutter.
    lib.tube('AnsCord', [f.at((0.07, 0.02, -0.085)), f.at((0.08, 0.01, -0.13)), f.at((0.11, -0.02, -0.2))], 0.003,
             M('Cord', '#2F3434', 0.7), g, res=3)
    g.matrix_world = Matrix.Translation(lib.B(base)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
    return g, top
