"""Console control art, one script-free GLB per module (contract: coordination/interfaces.md, "Control art hooks").

Module-local coordinates: origin = the game module node origin (console top surface), +Y = console normal,
-Z = away from the player. Caps are single-material meshes named Cap_<action> with origin at the top-face centre.
"""
import math

import bmesh
import bpy

import lib
from lib import UPF, Frame, circle, rrect

OUT = lib.ROOT + '/cockpit/art/controls/'
# Game action colours (src/core/palette.gd); SPACE stays red like the concept.
ACTION = {'left_1': '#FF5FA2', 'left_2': '#6BDC5A', 'left_3': '#3AA8FF', 'left_4': '#FFB03A',
          'right_left': '#B57BFF', 'right_up': '#3EE0D0', 'right_down': '#3EE0D0', 'right_right': '#B57BFF',
          'thumb': '#E2402F'}
O = Frame()


def M(key, color, rough=0.6, metal=0.0):
    return lib.mat('Ctl_' + key, color, rough, metal)


def cap_mat(action):
    return lib.mat('Cap_' + action, ACTION[action], 0.42)


def top(y=0.0, x=0.0, z=0.0):
    """Frame on a horizontal plane at height y; local +Z points up, local +Y points to -Z (away)."""
    return O.child((x, y, z), UPF)


def cap_slab(action, outline, height, bevel, x, z, bottom):
    """Pressable cap: rest top at bottom + height; origin at the top-face centre."""
    f = top(bottom, x, z)
    return lib.slab('Cap_' + action, outline, height, bevel, cap_mat(action), f, pivot=(x, bottom + height, z))


def left_keys():
    objs = [lib.slab('Housing', rrect(0.40, 0.13, 0.024, 4), 0.012, 0.004, M('inset', '#4A5250'), top(-0.004)),
            lib.slab('Well', rrect(0.36, 0.1, 0.02, 4), 0.006, 0.002, M('rubber', '#2F3434', 0.8), top(0.008))]
    for i, action in enumerate(['left_1', 'left_2', 'left_3', 'left_4']):
        objs.append(cap_slab(action, rrect(0.076, 0.074, 0.016, 4), 0.03, 0.009, (i - 1.5) * 0.085, 0.0, 0.01))
    return objs


def panic_button():
    ring = lib.slab('Housing', circle(0.088, 48), 0.03, 0.012, M('ring', '#E9A23B', 0.45), top(0.0),
                    holes=[list(reversed(circle(0.068, 48)))])
    well = lib.slab('Well', circle(0.07, 40), 0.012, 0.004, M('rubber', '#2F3434', 0.8), top(0.0))
    cap = cap_slab('thumb', circle(0.064, 40), 0.042, 0.02, 0.0, 0.0, 0.016)
    return [ring, well, cap]


def joystick():
    base = lib.slab('Base', circle(0.065, 36), 0.025, 0.01, M('rubber', '#2F3434', 0.75), top(0.0))
    boot = lib.slab('Boot', circle(0.035, 24), 0.03, 0.014, M('boot', '#262A2A', 0.85), top(0.015))
    pivot = lib.empty('Pivot', (0, 0.03, 0))
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.012, radius2=0.009, depth=0.12)
    lib.transform_bm(bm, Frame((0, 0.09, 0), (90, 0, 0)))
    lib.from_bmesh('Shaft', bm, M('shaft', '#3B4040', 0.5), pivot, pivot=(0, 0.03, 0))
    lib.sphere('Knob', 0.034, lib.mat('Ctl_knob', '#2FA6A3', 0.35), Frame((0, 0.16, 0)), pivot)
    return [base, boot, pivot]


def lever():
    housing = lib.box('Housing', (0.07, 0.11, 0.06), M('leverbox', '#C9BC9F', 0.6), top(0.03), bevel=0.012)
    slot = lib.box('Slot', (0.016, 0.08, 0.004), M('rubber', '#2F3434', 0.8), top(0.0605))
    pivot = lib.empty('Pivot', (0, 0.06, 0))      # hinge; arm points +Y at rotation 0
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.011, radius2=0.009, depth=0.16)
    lib.transform_bm(bm, Frame((0, 0.14, 0), (90, 0, 0)))
    lib.from_bmesh('Arm', bm, M('shaft', '#3B4040', 0.4, 0.3), pivot, pivot=(0, 0.06, 0))
    lib.sphere('Knob', 0.03, lib.mat('Ctl_leverknob', '#D4473A', 0.4), Frame((0, 0.22, 0)), pivot)
    # Rest pose -15 deg about X (Godot and Blender X agree in sign); gameplay drives this rotation.
    pivot.rotation_euler = (math.radians(-15), 0, 0)
    return [housing, slot, pivot]


def simon_pad():
    objs = [lib.slab('Plate', circle(0.088, 40), 0.02, 0.006, M('simonplate', '#3E5250', 0.55), top(0.0))]
    offsets = {'right_left': (-1, 0), 'right_up': (0, -1), 'right_down': (0, 1), 'right_right': (1, 0)}
    for action, (ox, oz) in offsets.items():
        objs.append(lib.slab('Ring_' + action, circle(0.032, 28), 0.006, 0.002, M('rubber', '#2F3434', 0.8),
                             top(0.02, ox * 0.055, oz * 0.055), holes=[list(reversed(circle(0.027, 28)))]))
        objs.append(cap_slab(action, circle(0.026, 28), 0.02, 0.008, ox * 0.055, oz * 0.055, 0.016))
    return objs


def arrow_keys():
    objs = [lib.slab('Housing', rrect(0.23, 0.155, 0.024, 4), 0.012, 0.004, M('inset', '#4A5250'), top(-0.004))]
    grid = {'right_up': (1, 0), 'right_left': (0, 1), 'right_down': (1, 1), 'right_right': (2, 1)}
    for action, (col, row) in grid.items():
        objs.append(cap_slab(action, rrect(0.066, 0.066, 0.014, 4), 0.026, 0.008, (col - 1) * 0.075,
                             (row - 0.5) * 0.075, 0.01))
    return objs


MODULES = {'left_keys': left_keys, 'panic_button': panic_button, 'joystick': joystick, 'lever': lever,
           'simon_pad': simon_pad, 'arrow_keys': arrow_keys}


def build_all():
    import os
    os.makedirs(OUT, exist_ok=True)
    report = {}
    for name, fn in MODULES.items():
        lib.reset()
        roots = fn()
        for o in bpy.data.objects:
            o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=OUT + name + '.glb', export_format='GLB', export_yup=True,
                                  use_selection=True, export_apply=True, export_cameras=False, export_lights=False)
        report[name] = {'nodes': sorted(o.name for o in bpy.data.objects), 'triangles': lib.count_tris()}
    return report
