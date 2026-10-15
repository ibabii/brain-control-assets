"""Clipping audit for the cockpit art. Run on the built .blend:
  Blender -b source/cockpit/cockpit_v2.blend --python scripts/cockpit_v2/audit.py
Imports the control modules at the console anchors (layout.json), then reports every pair of parts from different
assemblies where one pokes more than TOL into the other. Exit code 1 if anything is found.
"""
import json
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402

TOL = 0.0025
ZTOL = 0.0004          # surfaces closer than this flicker (z-fight)
ZAREA = 2e-4           # 2 cm2 of shared surface
# Designed joins (part sunk into the part it is mounted on). Patterns match name prefixes.
ALLOW = [('ConsoleSlab', 'ConsoleRim'), ('ConsoleSlab', 'ConsoleSkirt'), ('ConsoleRim', 'ConsoleSkirt'),
         ('ConsoleSlab', 'SlotInset'), ('SlotInset', 'SlotRim'), ('ConsoleSlab', 'SlotRim'), ('ConsoleSlab', 'ButtonPlate'),
         ('ButtonPlate', 'UndoButton'), ('ButtonPlate', 'DistractButton'), ('UndoButton', 'UndoButton'),
         ('DistractButton', 'DistractButton'), ('ConsoleSlab', 'Knob'), ('ConsoleSlab', 'Housing'),
         ('ConsoleSlab', 'Base'), ('SlotInset', 'Base'), ('SlotInset', 'Housing'), ('ConsoleSlab', 'Plate'), ('SlotInset', 'Plate'),
         ('ConsoleSlab', 'Screw'), ('ConsoleRim', 'Screw'), ('DeskTop', 'Deck'), ('DeskTop', 'Tray'),
         ('DeskTop', 'Console'), ('Tray', 'Console'), ('DeskTop', 'BrainFolds'), ('Deck', 'BrainFolds'),
         ('GaugePanel', 'Screw'), ('GaugePanel', 'Bezel'), ('Bezel', 'Face'), ('GaugePanel', 'Paper'),
         ('Frame', 'Screw'), ('Frame', 'Glass'), ('Back', 'Glass'), ('Shelf', 'Frame'), ('Shelf', 'Back'),
         ('Shelf', 'BrainFolds'), ('Deck', 'GaugePanel'), ('Deck', 'Console')]


def allowed(a, b):
    a, b = a.split('.')[0], b.split('.')[0]
    for x, y in ALLOW:
        if (_m(a, x) and _m(b, y)) or (_m(a, y) and _m(b, x)):
            return True
    return False


def _m(name, pat):
    return pat in name
# Thin dressing that is meant to touch or pierce things (tape, pins, cables run into the walls).
SKIP = ('Tape', 'Pin', 'Needle', 'Cable', 'Bundle', 'Fairy', 'Bulb', 'Wire', 'String', 'Antenna', 'Crumb',
        'CoffeeRing', 'Preview')
GROUPS = ('Notes', 'Notebook', 'Books', 'Trinkets', 'DeskProps', 'EdgeDressing', 'GaugeHousing', 'ConsoleHousing',
          'Desk', 'Shell', 'FrontScreen', 'LeftPanel', 'RightPanel', 'Controls')
ALONE = ('ConsoleHousing', 'GaugeHousing', 'Desk')      # each part is its own assembly
PROP_GROUPS = ('Books', 'Trinkets', 'DeskProps', 'EdgeDressing')
SLOT_MODULES = ('joystick', 'simon_pad', 'lever', 'arrow_keys')


def import_controls():
    with open(lib.ROOT + '/cockpit/art/layout.json') as f:
        anchors = json.load(f)['console']['anchors']
    con = lib.Frame(*_console(json.load(open(lib.ROOT + '/cockpit/art/layout.json'))['console']))
    root = bpy.data.objects.new('Controls', None)
    bpy.context.scene.collection.objects.link(root)
    R = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))       # Godot -> Blender basis
    for module, node in (('left_keys', 'LeftKeys'), ('panic_button', 'PanicButton'), ('joystick', 'RightSlot'),
                         ('simon_pad', 'RightSlot'), ('lever', 'RightSlot'), ('arrow_keys', 'RightSlot')):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=lib.ROOT + '/cockpit/art/controls/%s.glb' % module)
        new = set(bpy.data.objects) - before
        m = bpy.data.objects.new(module, None)
        bpy.context.scene.collection.objects.link(m)
        for o in new:
            if o.parent is None:
                o.parent = m
        m.parent = root
        m.matrix_world = Matrix.Translation(lib.B(con.at(anchors[node]))) @ (R @ con.m @ R.inverted()).to_4x4()


def _console(c):
    return c['position'], c['rotation_deg']


def assembly(o):
    chain = []
    p = o
    while p is not None:
        chain.append(p)
        p = p.parent
    for i, a in enumerate(chain):
        if a.name.split('.')[0] in GROUPS:
            g = a.name.split('.')[0]
            if g in ALONE:
                return o.name
            if g == 'Controls':                               # slot modules swap in place: one assembly
                m = chain[i - 1].name if i > 0 else o.name
                return 'RightSlot' if m in SLOT_MODULES else m
            if g in PROP_GROUPS:
                return chain[i - 1].name if i > 0 else o.name      # one prop
            return g
    return o.name


def tree(o, dg):
    bm = bmesh.new()
    bm.from_object(o, dg)
    bm.transform(o.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.normal_update()
    t = BVHTree.FromBMesh(bm)
    verts = [v.co.copy() for v in bm.verts]
    faces = [(f.calc_center_median(), f.normal.copy(), f.calc_area()) for f in bm.faces if f.calc_area() > 1e-7]
    bm.free()
    return t, verts, faces


def inside(p, t):
    """Ray-parity test (independent of face normals): odd number of crossings = inside."""
    n = 0
    o = p.copy()
    d = Vector((0.5773, 0.5774, 0.5773))
    for _ in range(64):
        loc, _, _, dist = t.ray_cast(o, d, 10.0)
        if loc is None:
            break
        n += 1
        o = loc + d * 1e-5
    return n % 2 == 1


def depth_inside(verts, t):
    """Deepest vertex of `verts` inside the closed mesh `t`."""
    d = 0.0
    for v in verts:
        hit = t.find_nearest(v, 0.3)
        if hit[0] is None or hit[3] <= d or hit[3] < TOL:
            continue
        if inside(v, t):
            d = hit[3]
    return d


def behind(verts, t):
    """Deepest vertex behind an open surface whose normals face the room."""
    d = 0.0
    for v in verts:
        loc, n, _, dist = t.find_nearest(v, 0.3)
        if loc is not None and (v - loc).dot(n) < 0:
            d = max(d, dist)
    return d


def coplanar(faces, t):
    """Area of `faces` lying on a same-facing surface of `t` (z-fighting)."""
    a = 0.0
    for c, n, ar in faces:
        loc, m, _, dist = t.find_nearest(c, ZTOL)
        if loc is not None and n.dot(m) > 0.995:
            a += ar
    return a


MOUNTED = ('Screw', 'Knob')     # small parts that must sit fully on a surface


def floating(dg):
    """Mounted parts whose underside (centre + rim) is more than 1 mm off any surface."""
    others = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()
              and not any(s in o.name for s in MOUNTED + ('Preview',))]
    verts, tris = [], []
    for o in others:                       # (appending meshes into one BMesh silently drops some of them)
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        me.calc_loop_triangles()
        base = len(verts)
        verts += [o.matrix_world @ v.co for v in me.vertices]
        tris += [tuple(base + i for i in lt.vertices) for lt in me.loop_triangles]
        e.to_mesh_clear()
    world = BVHTree.FromPolygons(verts, tris)
    bad = []
    for o in bpy.data.objects:
        if o.type != 'MESH' or not any(s in o.name for s in MOUNTED) or not o.visible_get():
            continue
        _, verts, _ = tree(o, dg)
        c = sum(verts, Vector()) / len(verts)
        cov = Matrix(((0,) * 3,) * 3)
        for v in verts:
            d = v - c
            for i in range(3):
                for j in range(3):
                    cov[i][j] += d[i] * d[j]
        import numpy as np
        w, vec = np.linalg.eigh(np.array(cov))
        if w[0] > 0.6 * w[1]:                         # not a flat part (tall knobs): check by eye
            continue
        n = Vector(vec[:, 0])                         # thinnest axis = mount normal
        u = n.orthogonal().normalized()
        r = max((v - c - n * (v - c).dot(n)).length for v in verts) * 0.8
        half = max(abs((v - c).dot(n)) for v in verts)
        worst = 0.0
        for k in range(9):
            q = c if k == 0 else c + (Matrix.Rotation(k * 0.785, 3, n) @ u) * r
            hits = [world.ray_cast(q, d, 0.05) for d in (n, -n)]
            dist = min([h[3] for h in hits if h[0] is not None] or [1.0])
            worst = max(worst, dist - half)
        if worst > 0.001:
            bad.append((worst, o.name, tuple(round(x, 3) for x in (c.x, c.z, -c.y))))
    return bad


def main():
    import_controls()
    dg = bpy.context.evaluated_depsgraph_get()
    objs = [o for o in bpy.data.objects if o.type == 'MESH' and not any(s in o.name for s in SKIP)
            and o.visible_get()]
    data = {o.name: (assembly(o),) + tree(o, dg) for o in objs}
    found = []
    names = list(data)
    for i, a in enumerate(names):
        ga, ta, va, fa = data[a]
        for b in names[i + 1:]:
            gb, tb, vb, fb = data[b]
            if ga == gb or not ta.overlap(tb):
                continue
            z = max(coplanar(fa, tb), coplanar(fb, ta))    # never allowed, even for designed joins
            if z > ZAREA:
                found.append((0.0, a, b))
                print('ZFIGHT %.1f cm2  %s  x  %s' % (z * 1e4, a, b))
            if allowed(a, b):
                continue
            if 'BrainFolds' in (a, b):            # open surface: use its inward-facing normals
                d = behind(vb if a == 'BrainFolds' else va, ta if a == 'BrainFolds' else tb)
            else:
                d = max(depth_inside(va, tb), depth_inside(vb, ta))
            if d > TOL:
                found.append((d, a, b))
    for d, name, at in sorted(floating(dg), reverse=True):
        found.append((d, name, 'air'))
        print('FLOAT %.1f mm  %s at %s (Godot)' % (d * 1000, name, at))
    for d, a, b in sorted(found, reverse=True):
        print('CLIP %.1f mm  %s  x  %s' % (d * 1000, a, b))
    print('AUDIT %d clipping pairs' % len(found))
    return found


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
