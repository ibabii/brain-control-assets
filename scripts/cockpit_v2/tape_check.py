"""Tape must lie on what it holds. Run on the built .blend:
  Blender -b source/cockpit/cockpit_v2.blend --python scripts/cockpit_v2/tape_check.py
Fails (exit 1) when a strip has more than LIMIT of its vertices over 3 mm from any surface."""
import os
import sys

import bpy
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402

LIMIT = 0.45                              # torn ends past an edge may hang a little


def main():
    dg = bpy.context.evaluated_depsgraph_get()
    verts, tris, tapes = [], [], []
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        if 'tape_normal' in o:
            tapes.append(o)
            continue
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        me.calc_loop_triangles()
        base = len(verts)
        verts += [o.matrix_world @ v.co for v in me.vertices]
        tris += [tuple(base + i for i in lt.vertices) for lt in me.loop_triangles]
        e.to_mesh_clear()
    t = BVHTree.FromPolygons(verts, tris)
    bad = 0
    for o in tapes:
        far = [t.find_nearest(o.matrix_world @ v.co, 1.0)[3] for v in o.data.vertices]
        frac = sum(d > 0.003 for d in far) / len(far)
        if frac > LIMIT:
            bad += 1
            print('TAPE_FLOAT %-22s %3.0f%% off, max %.1f mm' % (o.name, frac * 100, max(far) * 1000))
    print('TAPE_CHECK %d strips, %d floating' % (len(tapes), bad))
    return bad


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
