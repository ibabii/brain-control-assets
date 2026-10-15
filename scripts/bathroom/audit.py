"""Clipping audit for the bathroom (built .blend, props in place):
  Blender -b source/bathroom/bathroom.blend --python scripts/bathroom/audit.py
Pairs from different assemblies (top-level groups of the room, and each prop) that poke more than TOL into each
other, z-fighting surfaces, and anything behind the room shell (walls, floor, ceiling). Exit 1 on findings.
"""
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cockpit_v2'))
from audit import tree, depth_inside, coplanar, behind, TOL, ZAREA  # noqa: E402

PROPS = ('toothpaste', 'cup', 'soap', 'lotion', 'smudge', 'towel', 'faucet', 'tub', 'door')
# Designed joins: (assembly, assembly) that are meant to sit into each other.
ALLOW = {('Door', 'Shell'), ('Hall', 'Shell'), ('Hall', 'Door'), ('Window', 'Shell'), ('faucet', 'Vanity'), ('Tub', 'tub'), ('towel', 'TowelBar')}
OPEN = ('Shell',)                                    # single-sided surfaces facing the room
SHELL_TOL = 0.03     # behind a wall or floor is invisible from inside: only gross misplacement counts
SKIP = ('Ring', 'Glass', 'Reveal', 'Hook')           # thin bits meant to hang or sit in openings


def assembly(o):
    p = o
    while p.parent is not None and p.parent.name not in ('BathroomRoom',):
        p = p.parent
    return p.name.split('.')[0]


def _closed(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    ok = all(e.is_manifold for e in bm.edges)
    bm.free()
    return ok


RESTING = ('Cup', 'Dish', 'Bottle', 'Jar', 'PlantPot', 'Duck', 'Folded', 'Roll', 'ShelfBasket', 'Bin', 'Basket',
           'TubeBody', 'Toilet', 'Plinth', 'BathMat')


def resting(dg):
    """Parts that stand on something: gap under their footprint (5 rays) above GAP is floating."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    objs = [o for o in bpy.data.objects if o.type == 'MESH']
    bad = []
    for o in objs:
        if not o.name.startswith(RESTING) or any(k in o.name for k in ('Cap', 'Rim', 'Lid', 'Pedal', 'Beak', 'Eye')):
            continue
        verts, tris = [], []
        for x in objs:
            if x == o or x.parent == o:
                continue
            e = x.evaluated_get(dg)
            me = e.to_mesh()
            me.calc_loop_triangles()
            base = len(verts)
            verts += [x.matrix_world @ v.co for v in me.vertices]
            tris += [tuple(base + i for i in lt.vertices) for lt in me.loop_triangles]
            e.to_mesh_clear()
        world = BVHTree.FromPolygons(verts, tris)
        vs = [o.matrix_world @ v.co for v in o.data.vertices]
        zmin = min(v.z for v in vs)
        low = [v for v in vs if v.z < zmin + 0.003]
        c = sum(low, Vector()) / len(low)
        r = max((Vector((v.x - c.x, v.y - c.y, 0))).length for v in low) * 0.6
        gaps = []
        for dx, dy in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r)):
            q = Vector((c.x + dx, c.y + dy, zmin + 0.004))
            hit = world.ray_cast(q, Vector((0, 0, -1)), 0.2)
            gaps.append(hit[3] - 0.004 if hit[0] is not None else 0.2)
        if min(gaps) > GAP:
            bad.append((min(gaps), o.name))
    return bad


GAP = 0.002


def main():
    dg = bpy.context.evaluated_depsgraph_get()
    objs = [o for o in bpy.data.objects if o.type == 'MESH' and not any(s in o.name for s in SKIP)]
    data = {o.name: (assembly(o),) + tree(o, dg) for o in objs}
    closed = {o.name: _closed(o) for o in objs}          # inside/outside only means something for closed meshes
    found = []
    names = list(data)
    for i, a in enumerate(names):
        ga, ta, va, fa = data[a]
        for b in names[i + 1:]:
            gb, tb, vb, fb = data[b]
            if ga == gb or not ta.overlap(tb):
                continue
            z = max(coplanar(fa, tb), coplanar(fb, ta))
            if z > ZAREA:
                found.append((0.0, a, b))
                print('ZFIGHT %.1f cm2  %s  x  %s' % (z * 1e4, a, b))
            if (ga, gb) in ALLOW or (gb, ga) in ALLOW:
                continue
            if ga in OPEN or gb in OPEN:
                d = behind(vb, ta) if ga in OPEN else behind(va, tb)
            else:
                d = max(depth_inside(va, tb) if closed[b] else 0.0, depth_inside(vb, ta) if closed[a] else 0.0)
            if d > (SHELL_TOL if (ga in OPEN or gb in OPEN) else TOL):
                found.append((d, a, b))
    for g, name in resting(dg):
        found.append((g, name, 'air'))
        print('FLOAT %.1f mm  %s' % (g * 1000, name))
    for d, a, b in sorted(found, reverse=True):
        if d and b != 'air':
            print('CLIP %.1f mm  %s (%s)  x  %s (%s)' % (d * 1000, a, data[a][0], b, data[b][0]))
    print('BATHROOM AUDIT %d findings' % len(found))
    return found


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
