"""Where things are, without opening Blender: world bounds (Godot coords) and the 16:9 1080p seat-view rect of named
objects, and what sits near a point. Run on a built blend:
  Blender -b source/cockpit/cockpit_v2.blend --python scripts/tools/probe.py -- Mug Alien Cover
  Blender -b source/cockpit/cockpit_v2.blend --python scripts/tools/probe.py -- --near 0.94,1.04,-0.30 0.16
Names match object-name prefixes; a group (empty) reports the union of its meshes. --near lists meshes whose bounds come
within R of the point (a cheap pre-check before proposing a placement, hang point or swing cone).
"""
import math
import sys

import bpy
from mathutils import Vector

CAM = Vector((0, 1.36, 0.8))
PITCH = math.radians(-14)
FWD = Vector((0, math.sin(PITCH), -math.cos(PITCH)))
UP = Vector((0, math.cos(PITCH), math.sin(PITCH)))
F = 540 / math.tan(math.radians(34))          # 1080p focal length (vertical FOV 68)


def corners(o):
    out = []
    for m in [o, *o.children_recursive]:
        if m.type == 'MESH':
            for c in m.bound_box:
                w = m.matrix_world @ Vector(c)
                out.append(Vector((w.x, w.z, -w.y)))   # Blender -> Godot
    return out


def screen(p):
    d = p - CAM
    z = d.dot(FWD)
    return 960 + d.x / z * F, 540 - d.dot(UP) / z * F


args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if args[:1] == ['--near']:
    p = Vector([float(v) for v in args[1].split(',')])
    r = float(args[2]) if len(args) > 2 else 0.15
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        pts = corners(o)
        lo = Vector([min(q[i] for q in pts) for i in range(3)])
        hi = Vector([max(q[i] for q in pts) for i in range(3)])
        gap = Vector([max(lo[i] - p[i], 0, p[i] - hi[i]) for i in range(3)]).length
        if gap <= r and (hi - lo).length < 2.0:                    # skip the shell and the desk
            print('NEAR %-24s gap %.3f  lo %s  hi %s' % (o.name, gap, tuple(round(v, 3) for v in lo),
                                                        tuple(round(v, 3) for v in hi)))
else:
    for o in bpy.data.objects:
        if not any(o.name.startswith(n) for n in args) or (o.parent and any(o.parent.name.startswith(n) for n in args)):
            continue
        pts = corners(o)
        if not pts:
            continue
        lo = [min(q[i] for q in pts) for i in range(3)]
        hi = [max(q[i] for q in pts) for i in range(3)]
        sx = [screen(q) for q in pts if (q - CAM).dot(FWD) > 0.05]
        rect = (min(s[0] for s in sx), min(s[1] for s in sx), max(s[0] for s in sx), max(s[1] for s in sx)) if sx else None
        print('PROBE %-22s lo %s hi %s  px %s' % (o.name, tuple(round(v, 3) for v in lo), tuple(round(v, 3) for v in hi),
                                                 tuple(int(v) for v in rect) if rect else '-'))
