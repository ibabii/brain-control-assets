"""Cartoon fly for the cockpit (gameplay flies it around; the left hand swats at it).
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/fly/build.py
Godot space: origin = body centre, faces -Z, up +Y. ~4 cm long so it reads from the seat.
Nodes: Fly/Body..., Fly/WingL, Fly/WingR (pivot at the hinge; flap = rotation about local Z).
Clips: buzz (loop, wings flap), rest (wings folded back).
"""
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cockpit_v2'))
import lib  # noqa: E402
from lib import Frame  # noqa: E402

FPS = 100
LOW = dict(seg=14, rings=8)                                   # tiny: low sphere detail


def mat(name, color, rough=0.5, alpha=1.0, metal=0.0):
    m = lib.mat('Fly' + name, color, rough, metal)
    if alpha < 1.0:
        bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        bsdf.inputs['Alpha'].default_value = alpha
        m.surface_render_method = 'BLENDED'
    return m


def build():
    lib.reset()
    root = lib.empty('Fly', (0, 0, 0))
    body = mat('Body', '#343B44', 0.45)
    band = mat('Band', '#6B7682', 0.5)
    white = mat('Eye', '#FBF8F1', 0.3)
    black = mat('Pupil', '#14161A', 0.25)
    wing = mat('Wing', '#DDEBF2', 0.15, alpha=0.42)
    vein = mat('Vein', '#5E6E78', 0.4, alpha=0.6)
    s = 1.35                                                    # cartoon scale
    lib.sphere('Thorax', 0.0085 * s, body, Frame((0, 0, 0)), root, **LOW)
    lib.sphere('Head', 0.0072 * s, body, Frame((0, 0.0012 * s, -0.0105 * s)), root, **LOW)
    lib.sphere('Abdomen', 0.0095 * s, body, Frame((0, -0.001 * s, 0.0125 * s)), root, scale=(0.9, 0.8, 1.25), **LOW)
    for i, z in enumerate((0.0105, 0.0158)):
        lib.sphere('Band%d' % i, 0.0097 * s, band, Frame((0, -0.001 * s, z * s)), root, scale=(0.9, 0.81, 0.16), **LOW)
    for sx in (-1, 1):
        side = 'L' if sx < 0 else 'R'
        eye = (sx * 0.0045 * s, 0.0042 * s, -0.0142 * s)
        lib.sphere('Eye' + side, 0.0047 * s, white, Frame(eye), root, **LOW)
        lib.sphere('Pupil' + side, 0.0024 * s, black,
                   Frame((eye[0] + sx * 0.0012 * s, eye[1] + 0.0004 * s, eye[2] - 0.0036 * s)), root, seg=10, rings=6)
        # Wing on a hinge empty: rest along the body, tilted up a little.
        hinge = lib.empty('Wing' + side, (sx * 0.0040 * s, 0.0068 * s, 0.0010 * s), root)
        hf = Frame((sx * 0.0040 * s, 0.0068 * s, 0.0010 * s), (0, sx * -28, sx * -12))
        lib.sphere('WingBlade' + side, 0.0125 * s, wing, hf.child((sx * 0.0115 * s, 0, 0.004 * s)), hinge,
                   scale=(1.0, 0.05, 0.5), seg=20, rings=6)
        for k, (dz, ln) in enumerate(((-0.002, 0.020), (0.003, 0.018))):
            lib.tube('WingVein%s%d' % (side, k), [hf.at((sx * 0.001 * s, 0.0004, dz * s)),
                                                   hf.at((sx * ln * 0.5 * s, 0.0006, (dz + 0.002) * s)),
                                                   hf.at((sx * ln * s, 0.0004, (dz + 0.005) * s))],
                     0.00025, vein, hinge, res=4, bevel_res=1)
        # Three bent legs per side.
        for k, z in enumerate((-0.004, 0.0, 0.0045)):
            lib.tube('Leg%s%d' % (side, k), [(sx * 0.0035 * s, -0.0055 * s, z * s),
                                             (sx * 0.0105 * s, -0.0075 * s, (z + (k - 1) * 0.002) * s),
                                             (sx * 0.0125 * s, -0.0135 * s, (z + (k - 1) * 0.004) * s)],
                     0.0007 * s, body, root, res=3, bevel_res=0)
    return root


def animate():
    """Object clips on the wing hinges, one NLA track each (glTF exports them as named animations)."""
    bpy.context.scene.render.fps = FPS
    wings = [bpy.data.objects['WingL'], bpy.data.objects['WingR']]
    # Blender axis for Godot local Z (the flap axis): Godot (x, y, z) -> Blender (x, -z, y).
    clips = {'buzz': [(0, 38), (2, -30), (4, 38)],        # 0.04 s cycle
             'rest': [(0, -8), (30, -5), (60, -8)]}    # slow twitch (a static clip gets dropped on export)
    fold = {'buzz': 0, 'rest': 32}                        # rest: wings swept back along the body
    for w in wings:
        w.rotation_mode = 'XYZ'
        w.animation_data_create()
    for name, keys in clips.items():
        for w in wings:
            sx = -1 if w.name.endswith('L') else 1
            act = bpy.data.actions.new('%s_%s' % (name, w.name))
            w.animation_data.action = act
            for f, deg in keys:
                # flap = rotation about the body axis (Blender Y = Godot -Z); fold = sweep about Blender Z (Godot Y)
                w.rotation_euler = (0, math.radians(deg) * sx, math.radians(fold[name]) * sx)
                w.keyframe_insert('rotation_euler', frame=f)
            w.animation_data.action = None
            tr = w.animation_data.nla_tracks.new()
            tr.name = name
            tr.strips.new(name, 0, act)
    for w in wings:
        w.rotation_euler = (0, 0, 0)


def main():
    root = build()
    animate()
    out = os.path.join(lib.ROOT, 'fly', 'art')
    os.makedirs(out, exist_ok=True)
    for o in bpy.data.objects:
        o.select_set(o == root or o in root.children_recursive)
    lib.export_glb(filepath=os.path.join(out, 'fly.glb'), export_format='GLB', export_yup=True,
                              use_selection=True, export_cameras=False, export_lights=False,
                              export_animation_mode='NLA_TRACKS', export_force_sampling=True)
    os.makedirs(os.path.join(lib.ROOT, 'source', 'fly'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(lib.ROOT, 'source', 'fly', 'fly.blend'))
    print('FLY_BUILT tris=%d' % lib.count_tris())


main()
