"""Organ-cam characters (art_direction.md "Portraits"): calm clay Heart and Stomach with tiny faces, in the intercom
lamp colours, for the idle side monitors and the reveal lower-third icons.
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/organs/build.py
Writes organs/art/<id>.glb + .tscn: root `<Id>` (pivot on the floor under it, faces -Z), child `Body` (mesh + face
parts) carrying the loop: Heart `pulse` (slow lub-dub, 1.2 s), Stomach `gurgle` (soft wobble + a gurgle, 2.4 s).
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cockpit_v2'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'human'))
import lib  # noqa: E402
from lib import B, Frame  # noqa: E402
from sculpt import meta, ell, ball, solid, adopt, Surface, decal  # noqa: E402

INK = '#2E2624'
FPS = 30


def ellipse(a, b, n=20, cx=0.0, cy=0.0):
    return [(cx + a * math.cos(2 * math.pi * k / n), cy + b * math.sin(2 * math.pi * k / n)) for k in range(n)]


def arc(cx, cy, w, h, n=12, up=True):
    """Upturned (or down) arc points in XY, w wide, h tall."""
    return [(cx + w * (2 * i / n - 1), cy + (1 if up else -1) * h * (1 - (2 * i / n - 1) ** 2)) for i in range(n + 1)]


def face(surf, body, cx, cy, s, eyes='open', mouth='smile', k=1.45):
    """Small calm face on the front of `surf` around (cx, cy), s = eye spacing (m), k = feature scale (icons)."""
    E = lambda a, b, n, x, y: ellipse(a * k, b * k, n, x, y)
    ink = lib.mat('OrganInk', INK, 0.7)
    glint = lib.mat('OrganGlint', '#FFFFFF', 0.6)
    blush = lib.mat('OrganBlush', '#E07C7C', 0.9)
    front = Frame((0, 0, 0))
    for k_ in (-1, 1):
        ex = cx + k_ * s / 2
        if eyes == 'open':
            decal('Eye%d' % (k_ + 1), surf, E(0.011, 0.014, 20, ex, cy), front, ink, body, offset=0.0015)
            decal('Glint%d' % (k_ + 1), surf, E(0.0035, 0.0035, 10, ex + 0.003 * k, cy + 0.005 * k), front, glint, body,
                  offset=0.0025)
        else:                                               # sleepy: soft closed lids (down-curved arcs)
            pts = arc(ex, cy + 0.002, 0.013 * k, 0.006 * k, 10, up=False)
            pts = [(x, y) for x, y in pts] + [(x, y - 0.0035 * k) for x, y in reversed(pts)]
            decal('Lid%d' % (k_ + 1), surf, pts, front, ink, body, offset=0.0015)
        decal('Blush%d' % (k_ + 1), surf, E(0.016, 0.009, 18, cx + k_ * s * 0.95, cy - 0.022 * k), front, blush, body,
              offset=0.0012)
    if mouth == 'smile':
        pts = arc(cx, cy - 0.03 * k, 0.014 * k, 0.008 * k, 10, up=False)
    else:                                                   # small content 'o'
        pts = E(0.005, 0.006, 14, cx, cy - 0.03 * k)
        decal('Mouth', surf, pts, front, ink, body, offset=0.0015)
        return
    band = [(x, y) for x, y in pts] + [(x, y + 0.004 * k) for x, y in reversed(pts)]
    decal('Mouth', surf, band, front, ink, body, offset=0.0015)


def key_scale(o, keys, name):
    o.animation_data_create()
    act = bpy.data.actions.new(name)
    o.animation_data.action = act
    for f, sc in keys:
        o.scale = sc
        o.keyframe_insert('scale', frame=f)
    act.use_fake_user = True


def key_rot(o, keys):
    for f, r in keys:
        o.rotation_euler = (0, 0, math.radians(r))
        o.keyframe_insert('rotation_euler', frame=f)


def heart():
    root = lib.empty('Heart', (0, 0, 0))
    c = Vector((0, 0.17, 0))
    mb = meta('HeartMeta', 0.004)
    for k in (-1, 1):                                       # two round lobes, a chunky rounded point
        ball(mb, c + Vector((k * 0.055, 0.04, 0)), 0.075)
    ell(mb, c + Vector((0, -0.035, 0)), (0.095, 0.08, 0.06))
    ell(mb, c + Vector((0, -0.095, 0)), (0.04, 0.045, 0.035))
    ell(mb, c + Vector((0, 0.115, -0.0)), (0.022, 0.03, 0.08), neg=True)   # the notch between the lobes
    body = adopt(solid('HeartBody', [mb], 0.003, 9000, lib.mat('HeartClay', '#C98778', 0.8)), None, c)
    pivot = lib.empty('Body', tuple(c), root)               # the pulse scales about the heart's middle
    lib.set_parent(body, pivot)
    surf = Surface(body)
    face(surf, pivot, 0.0, 0.175, 0.064)
    b0 = 1.0
    key_scale(pivot, [(0, (b0,) * 3), (4, (1.07, 1.06, 1.07)), (8, (0.99, 1.0, 0.99)), (12, (1.045, 1.04, 1.045)),
                      (17, (b0,) * 3), (36, (b0,) * 3)], 'pulse')
    return root


def stomach():
    root = lib.empty('Stomach', (0, 0, 0))
    c = Vector((0, 0.16, 0))
    mb = meta('StomachMeta', 0.004)                         # soft bean: a fat kidney, leaning a little
    ell(mb, c + Vector((-0.03, 0.03, 0)), (0.09, 0.075, 0.065))
    ell(mb, c + Vector((0.045, -0.035, 0)), (0.085, 0.07, 0.065))
    ball(mb, c + Vector((0.0, 0.0, 0.0)), 0.08)
    ell(mb, c + Vector((-0.07, 0.085, 0)), (0.03, 0.04, 0.03))   # the little top tube (oesophagus nub)
    body = adopt(solid('StomachBody', [mb], 0.003, 9000, lib.mat('StomachSage', '#8FA585', 0.8)), None, c)
    pivot = lib.empty('Body', tuple(c - Vector((0, 0.1, 0))), root)   # wobble from near the bottom
    lib.set_parent(body, pivot)
    surf = Surface(body)
    face(surf, pivot, -0.005, 0.17, 0.064, eyes='sleepy', mouth='o')
    keys, rots = [], []
    for f in range(0, 73, 6):                               # slow breathing squash, gurgle shake mid-loop
        t = f / 72
        w = 0.025 * math.sin(2 * math.pi * t)
        g = 0.03 * math.sin(2 * math.pi * t * 6) * math.exp(-((t - 0.55) / 0.08) ** 2)
        keys.append((f, (1 + w + g, 1 - w - g, 1 + w)))
        rots.append((f, 3 * math.sin(2 * math.pi * t) + 4 * math.sin(2 * math.pi * t * 6) * math.exp(-((t - 0.55) / 0.08) ** 2)))
    key_scale(pivot, keys, 'gurgle')
    key_rot(pivot, rots)
    return root


def main():
    out = os.path.join(lib.ROOT, 'organs', 'art')
    os.makedirs(out, exist_ok=True)
    bpy.context.scene.render.fps = FPS
    for build in (heart, stomach):
        lib.reset()
        for a in list(bpy.data.actions):
            bpy.data.actions.remove(a)
        root = build()
        bpy.context.view_layer.update()
        for o in bpy.data.objects:
            o.select_set(o == root or o in root.children_recursive)
        name = root.name.lower()
        lib.export_glb(filepath=os.path.join(out, name + '.glb'), export_format='GLB', export_yup=True,
                       use_selection=True, export_cameras=False, export_lights=False, export_animations=True,
                       export_animation_mode='ACTIONS', export_force_sampling=True)
        with open(os.path.join(out, name + '.tscn'), 'w') as f:
            f.write('[gd_scene format=3]\n\n[ext_resource type="PackedScene" path="res://organs/art/%s.glb" id="1"]\n\n'
                    '[node name="%s" instance=ExtResource("1")]\n' % (name, root.name))
        print('ORGAN_BUILT', name)


main()
