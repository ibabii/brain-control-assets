"""Brain-pilot hands: chunky 4-finger cartoon hand + knitted sleeve, rigged (contract: coordination/interfaces.md "Hand art").
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/hands/build.py
Right hand in Blender coords: wrist pivot at the origin, fingers +Y, back of the hand +Z, thumb -X
(after glTF export, Godot: fingers -Z, back +Y, sleeve +Z).
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cockpit_v2'))
import lib  # noqa: E402

SCALE = 1.2                    # whole hand and sleeve, applied after building (chunky, oversized)
K = 0.55                       # metaball surface radius / element radius (stiffness 2)
SKIN, NAIL = '#F2A99A', '#F5BCAE'          # nail just lighter than skin (white read as dots)
KNITS = {'teal': '#4F7C77'}        # user pick 2026-10-14 (honey was the alternative: #D9A04C)

# Chains: (start, [segment directions], [segment lengths], radius). Fingers are straight in the rest pose.
CHAINS = {
    # Knuckles 35 mm apart and fanned out, so a clear gap stays between fingers (no webbing).
    'index': ((-0.029, 0.069, 0.001), [(-0.12, 1, 0)] * 3, (0.023, 0.016, 0.012), 0.0103),
    'middle': ((0.0, 0.074, 0.002), [(0, 1, 0)] * 3, (0.025, 0.017, 0.013), 0.0107),
    'ring': ((0.029, 0.068, 0.0), [(0.13, 1, 0)] * 3, (0.022, 0.015, 0.011), 0.0100),
    # Thumb (from the user's reference photos): rooted low by the wrist inside the palm mound, free part starts
    # halfway up the side, splayed ~35 deg from the fingers, turned on its side (nail faces out, see THUMB_UP) so
    # flexing curls it ACROSS the palm toward the fingers (opposition), not down like a fifth finger.
    'thumb': ((-0.012, 0.004, -0.009), [(-0.6, 0.78, -0.18), (-0.55, 0.82, -0.12), (-0.42, 0.9, -0.08)],
              (0.036, 0.026, 0.020), 0.0120),
}
THUMB_UP = Vector((-0.85, 0.0, 0.5))       # thumb nail faces sideways-out, ~60 deg from the finger nails


def joints(name):
    start, dirs, lens, _ = CHAINS[name]
    pts = [Vector(start)]
    for d, l in zip(dirs, lens):
        pts.append(pts[-1] + Vector(d).normalized() * l)
    return pts


# --- metaball modelling -------------------------------------------------------------------------

def _meta(name, res):
    mb = bpy.data.metaballs.new(name)
    mb.resolution = mb.render_resolution = res      # sets the final density: no decimation afterwards
    o = bpy.data.objects.new(name, mb)
    bpy.context.scene.collection.objects.link(o)
    return mb, o


def ellipsoid(mb, c, semi):
    r = max(semi) / K
    e = mb.elements.new(type='ELLIPSOID')
    e.co, e.radius = c, r
    e.size_x, e.size_y, e.size_z = (s / (K * r) for s in semi)


def capsule(mb, a, b, radius):
    a, b = Vector(a), Vector(b)
    e = mb.elements.new(type='CAPSULE')
    e.co, e.radius, e.size_x = (a + b) / 2, radius / K, (b - a).length / 2
    e.rotation = Vector((1, 0, 0)).rotation_difference((b - a).normalized())


def ball(mb, c, radius):
    e = mb.elements.new(type='BALL')
    e.co, e.radius = c, radius / K


def to_mesh(o):
    """Metaball -> mesh object (same name). Evaluated geometry copied, so families stay independent."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    name = o.name
    mb = o.data
    bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.metaballs.remove(mb)
    m = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(m)
    return m


def model_parts():
    """Palm block and one mesh per finger (separate metaball families so fingers never fuse)."""
    mb, o = _meta('PartPalm', 0.0026)
    ellipsoid(mb, (0, 0.042, 0.0), (0.040, 0.034, 0.0155))
    ellipsoid(mb, (0, 0.065, 0.003), (0.034, 0.013, 0.0145))     # knuckle ridge, inside the palm outline
    ellipsoid(mb, (-0.024, 0.018, -0.009), (0.018, 0.024, 0.0135))  # thumb mound (around thumb_1)
    ellipsoid(mb, (0, 0.004, 0.0), (0.029, 0.026, 0.0190))        # wrist
    capsule(mb, (0, -0.06, 0), (0, -0.012, 0), 0.020)              # forearm (inside the cuff)
    parts = {'palm': to_mesh(o)}
    for name in CHAINS:
        mb, o = _meta('Part' + name.title(), 0.0024)
        pts = joints(name)
        r = CHAINS[name][3]
        for i in range(3):
            capsule(mb, pts[i], pts[i + 1], r * (1.0, 0.97, 0.95)[i])
        ball(mb, pts[3], r * 1.12)                                 # rounded ball tip
        parts[name] = to_mesh(o)
    return parts


PART_IDS = ['palm', 'index', 'middle', 'ring', 'thumb']


def union(parts):
    """One skin: voxel union of palm + fingers, finger/palm joins filleted (never finger/finger, so no
    webbing), then rebuilt as even quads (smooth shading at a game budget). Per-vertex 'part' = nearest part."""
    objs = []
    for p in parts.values():
        c = bpy.data.objects.new('U_' + p.name, p.data.copy())
        bpy.context.scene.collection.objects.link(c)
        objs.append(c)
    for x in bpy.data.objects:
        x.select_set(x in objs)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = 'Hand'
    o.data.remesh_voxel_size = 0.0014
    bpy.ops.object.voxel_remesh()
    trees = {}
    for name, p in parts.items():
        b = bmesh.new()
        b.from_mesh(p.data)
        trees[name] = BVHTree.FromBMesh(b)
        b.free()

    def nearest(co, limit=0.03):
        d = {n: (t.find_nearest(co, limit)[3] or 1.0) for n, t in trees.items()}
        return sorted(d, key=d.get), d

    bm = bmesh.new()
    bm.from_mesh(o.data)
    seam = set()
    for v in bm.verts:
        order, d = nearest(v.co)
        if 'palm' in order[:2] and d[order[1]] < 0.006:      # finger/palm join only
            seam.add(v)
    for _ in range(2):                                       # widen the fillet band
        seam |= {e.other_vert(v) for v in list(seam) for e in v.link_edges}
    for _ in range(14):
        bmesh.ops.smooth_vert(bm, verts=list(seam), factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()
    for x in bpy.data.objects:
        x.select_set(x == o)
    bpy.context.view_layer.objects.active = o
    n = len(o.data.polygons)
    bpy.ops.object.quadriflow_remesh(target_faces=3200, use_preserve_sharp=False, use_preserve_boundary=False,
                                     use_mesh_symmetry=False, smooth_normals=True)
    if len(o.data.polygons) == n:                            # QuadriFlow refused: collapse, then relax below
        print('QUADRIFLOW failed, decimating')
        m = o.modifiers.new('Dec', 'DECIMATE')
        m.ratio = 3000 / n                                   # ~6k triangles
        bpy.ops.object.modifier_apply(modifier='Dec')
    bm = bmesh.new()
    bm.from_mesh(o.data)
    for _ in range(3):
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.4, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    part = bm.verts.layers.int.new('part')
    for v in bm.verts:
        v[part] = PART_IDS.index(nearest(v.co)[0][0])
    bm.to_mesh(o.data)
    bm.free()
    for f in o.data.polygons:
        f.use_smooth = True
    return o


def nails():
    bm = bmesh.new()
    owner = []
    for name in CHAINS:
        pts = joints(name)
        r = CHAINS[name][3]
        d = (pts[3] - pts[2]).normalized()
        up = (THUMB_UP if name == 'thumb' else Vector((0, 0, 1)))
        up = (up - d * up.dot(d)).normalized()
        side = d.cross(up)
        c = pts[3] - d * r * 0.05 + up * r * 1.05            # just proud of the ball tip (1.12 r)
        nb = bmesh.new()
        bmesh.ops.create_uvsphere(nb, u_segments=16, v_segments=8, radius=1.0)
        frame = Matrix((side * r * 0.62, d * r * 0.8, up * r * 0.2)).transposed().to_4x4()
        frame.translation = c
        bmesh.ops.transform(nb, matrix=frame, verts=nb.verts)
        me = bpy.data.meshes.new('tmp')
        nb.to_mesh(me)
        nb.free()
        n0 = len(bm.verts)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        owner += [name] * (len(bm.verts) - n0)
    me = bpy.data.meshes.new('Nails')
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new('Nails', me)
    bpy.context.scene.collection.objects.link(o)
    o['owner'] = owner
    return o


# --- knitted sleeve -----------------------------------------------------------------------------

def knit_texture(color, rib=False):
    """Tileable knit: rows of V stitches (or vertical ribs for the cuff). 128 x 96 px = 8 x 8 stitches."""
    h, w = 96, 128
    y, x = np.mgrid[0:h, 0:w].astype(float)
    cx, cy = (x % 16) / 16.0, (y % 12) / 12.0
    if rib:
        shape = 0.5 + 0.5 * np.cos((x % 16) / 16.0 * 2 * math.pi)
        shape = shape * (0.85 + 0.15 * np.cos(cy * 2 * math.pi))
    else:
        half = np.abs(cx - 0.5) * 2                                  # 0 centre .. 1 edge
        d = np.abs((1 - cy) - half)                                  # distance to the V arm
        shape = np.clip(1 - d * 2.2, 0, 1) ** 0.7
    rgb = np.array([lib.linear(c) for c in lib.srgb(color)])
    noise = np.random.default_rng(7).normal(0, 0.03, (h, w, 1))
    img = rgb[None, None, :] ** (1 / 2.2) * (0.62 + 0.45 * shape[..., None] + noise)
    name = 'Knit' + ('Rib' if rib else '') + color[1:]
    gx = (np.roll(shape, -1, 1) - np.roll(shape, 1, 1)) * 1.6     # tileable gradients -> tangent-space normal
    gy = (np.roll(shape, 1, 0) - np.roll(shape, -1, 0)) * 1.6
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return (lib.image_from_array(name, np.clip(img, 0, 1)),
            lib.image_from_array(name + 'N', n * 0.5 + 0.5, non_color=True))


def sleeve(color):
    """Ribbed cuff + slightly puffy sleeve running back along -Y, off-screen. Open at the far end."""
    seg = 24
    rows = []                                    # (y, radius scale, ribbed, inner)
    y0 = -0.012
    rows.append((y0 + 0.006, 0.86, True, True))  # inner lip, tucked back inside
    rows.append((y0 + 0.0005, 0.92, True, False))
    rows.append((y0 - 0.0015, 0.99, True, False))
    for i in range(1, 4):
        rows.append((y0 - 0.0015 - i * 0.018, 1.0, True, False))
    yc = rows[-1][0]
    for i in range(1, 14):
        t = i / 13
        rows.append((yc - t * 0.6, 1.1 + 0.08 * math.sin(min(t * 8, 1) * math.pi / 2) + 0.4 * t, False, False))
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    ring = []
    for y, s, ribbed, inner in rows:
        vs = []
        for k in range(seg):
            a = k / seg * 2 * math.pi
            rx, rz = 0.034 * s, 0.027 * s
            bump = 0.0 if ribbed else 0.0012 * math.sin(a * 3 + y * 45)    # knit and ribs live in the texture
            vs.append(bm.verts.new((math.cos(a) * (rx + bump), y, math.sin(a) * (rz + bump))))
        ring.append(vs)
    cuff_rows = sum(1 for r in rows if r[2])
    for j in range(len(rows) - 1):
        for k in range(seg):
            q = [ring[j][k], ring[j][(k + 1) % seg], ring[j + 1][(k + 1) % seg], ring[j + 1][k]]
            f = bm.faces.new(q)
            f.material_index = 0 if j < cuff_rows - 1 else 1
            f.smooth = True
            for l, (jj, kk) in zip(f.loops, ((j, k), (j, k + 1), (j + 1, k + 1), (j + 1, k))):
                l[uv].uv = (kk / seg * 6, -rows[jj][0] / 0.028)
    me = bpy.data.meshes.new('Sleeve')
    bm.to_mesh(me)
    bm.free()
    for key, rib in (('KnitRib_', True), ('Knit_', False)):
        albedo, normal = knit_texture(KNITS[color], rib)
        me.materials.append(lib.mat(key + color, KNITS[color], 0.9, image=albedo, normal=normal))
    o = bpy.data.objects.new('Sleeve', me)
    bpy.context.scene.collection.objects.link(o)
    _outward(o)
    return o


def _outward(o):
    """Tube normals point away from the axis (recalc can't tell inside from out on an open tube)."""
    me = o.data
    me.update()
    p = me.polygons[len(me.polygons) // 2]
    radial = Vector((p.center.x, 0, p.center.z))
    if p.normal.dot(radial) < 0:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()


# --- rig ----------------------------------------------------------------------------------------

def armature():
    arm = bpy.data.armatures.new('Skeleton')
    rig = bpy.data.objects.new('Skeleton', arm)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones

    def bone(name, head, tail, parent=None, up=Vector((0, 0, 1))):
        b = eb.new(name)
        b.head, b.tail = head, tail
        b.align_roll(up)
        if parent:
            b.parent = eb[parent]
            b.use_connect = (b.head - eb[parent].tail).length < 1e-5
        return b

    bone('forearm', (0, -0.14, 0), (0, 0, 0))
    bone('wrist', (0, 0, 0), (0, 0.014, 0), 'forearm')
    bone('palm', (0, 0.014, 0), (0, 0.068, 0), 'wrist')
    for name in CHAINS:
        pts = joints(name)
        up = THUMB_UP if name == 'thumb' else Vector((0, 0, 1))
        for i in range(3):
            bone('%s_%d' % (name, i + 1), pts[i], pts[i + 1], 'palm' if i == 0 else '%s_%d' % (name, i), up)
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


def _smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def _chain_s(v, pts):
    """Arc-length position of v's nearest point on the polyline pts (clamped to its ends)."""
    best, s_best, s = 1e9, 0.0, 0.0
    for a, b in zip(pts, pts[1:]):
        ab = b - a
        t = min(max((v - a).dot(ab) / ab.length_squared, 0.0), 1.0)
        d = (a + ab * t - v).length
        if d < best:
            best, s_best = d, s + t * ab.length
        s += ab.length
    return s_best, best


def chain_weights(v, name, blend=0.005):
    pts = joints(name)
    s, _ = _chain_s(v, pts)
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + (b - a).length)
    t = [_smooth((s - cum[j]) / blend + 0.5) for j in range(3)] + [0.0]
    w = {'palm': 1 - t[0]}
    for i in range(3):
        w['%s_%d' % (name, i + 1)] = t[i] - t[i + 1]
    return w


def palm_weights(v):
    w = {'forearm': 1 - _smooth((v.y + 0.006) / 0.012 + 0.5)}
    w['wrist'] = (1 - w['forearm']) * (1 - _smooth((v.y - 0.016) / 0.016 + 0.5))
    w['palm'] = 1 - w['forearm'] - w['wrist']
    take = {}
    for name in ('index', 'middle', 'ring'):
        pts = joints(name)
        d = pts[1] - pts[0]
        lateral = (v - pts[0]) - d.normalized() * (v - pts[0]).dot(d.normalized())
        lat = 1 - _smooth((Vector((lateral.x, lateral.y, 0)).length - 0.009) / 0.008)
        take['%s_1' % name] = 0.45 * _smooth((v.y - (pts[0].y - 0.008)) / 0.014) * lat
    tp = joints('thumb')
    _, dist = _chain_s(v, tp[:2])
    take['thumb_1'] = 0.85 * (1 - _smooth((dist - 0.009) / 0.012))
    total = sum(take.values())
    if total > 0.9:
        take = {k: x * 0.9 / total for k, x in take.items()}
        total = 0.9
    w = {k: x * (1 - total) for k, x in w.items()}
    w.update(take)
    return w


WEIGHT_SMOOTH = 8


def skin(hand, parts, rig, nails_obj):
    groups = {}
    for o in (hand, nails_obj):
        for b in rig.data.bones:
            groups[(o.name, b.name)] = o.vertex_groups.new(name=b.name)
    ids = hand.data.attributes['part'].data
    W = []
    for v in hand.data.vertices:
        part = PART_IDS[ids[v.index].value]
        W.append(palm_weights(v.co) if part == 'palm' else chain_weights(v.co, part))
    # Smooth the weights over the surface: removes jumps where the part labels meet (thumb/palm flaps).
    nbrs = [[] for _ in W]
    for e in hand.data.edges:
        a, b = e.vertices
        nbrs[a].append(b)
        nbrs[b].append(a)
    for _ in range(WEIGHT_SMOOTH):
        new = []
        for i, w in enumerate(W):
            acc = {k: x * 0.5 for k, x in w.items()}
            share = 0.5 / max(len(nbrs[i]), 1)
            for j in nbrs[i]:
                for k, x in W[j].items():
                    acc[k] = acc.get(k, 0.0) + x * share
            new.append(acc)
        W = new
    for i, w in enumerate(W):
        top = sorted(w.items(), key=lambda kv: -kv[1])[:4]        # Godot skins use 4 influences
        total = sum(x for _, x in top)
        for b, x in top:
            if x / total > 0.01:
                groups[(hand.name, b)].add([i], x / total, 'REPLACE')
    for v, owner in zip(nails_obj.data.vertices, nails_obj['owner']):
        groups[(nails_obj.name, owner + '_3')].add([v.index], 1.0, 'REPLACE')
    for o in (hand, nails_obj):
        o.parent = rig
        m = o.modifiers.new('Armature', 'ARMATURE')
        m.object = rig


# --- poses --------------------------------------------------------------------------------------

POSES = {
    # bone: (flex deg (toward the palm), side deg); thumb uses (flex, across-the-palm)
    'relaxed': {'index': (14, 10, 6), 'middle': (18, 14, 8), 'ring': (24, 18, 10), 'thumb': (6, 10, 8, 0)},
    'point': {'index': (32, 8, 4), 'middle': (85, 100, 60), 'ring': (88, 100, 60), 'thumb': (25, 30, 30, 30)},
    'fist': {'index': (82, 100, 65), 'middle': (85, 102, 65), 'ring': (88, 100, 62), 'thumb': (28, 40, 35, 35)},
    'grip': {'index': (62, 62, 30), 'middle': (66, 64, 30), 'ring': (70, 64, 30), 'thumb': (20, 30, 25, 40)},
}


def pose(rig, name):
    p = POSES[name]
    for pb in rig.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
    for chain, angles in p.items():
        if chain == 'thumb':
            f1, f2, f3, across = angles
            rig.pose.bones['thumb_1'].rotation_euler = (-math.radians(f1), 0, -math.radians(across))
            rig.pose.bones['thumb_2'].rotation_euler = (-math.radians(f2), 0, 0)
            rig.pose.bones['thumb_3'].rotation_euler = (-math.radians(f3), 0, 0)
        else:
            for i, a in enumerate(angles):
                rig.pose.bones['%s_%d' % (chain, i + 1)].rotation_euler = (-math.radians(a), 0, 0)
    bpy.context.view_layer.update()
    if name in THUMB_OVER:
        solve_thumb(rig, THUMB_OVER[name])


# The thumb is solved, not hand-typed, with only its real joints: thumb_1 swings (flex across the palm + spread),
# thumb_2/3 are hinges. Target: tip pad on the backs of the curled fingers (fist), against the curled middle
# finger (point), on the side of the ball (grip). Never inside a finger or the palm.
THUMB_OVER = {'point': 'point', 'fist': 'fist', 'grip': 'grip', 'grip_fit': 'grip'}


def _seg_dist(a, b, c, d):
    best = 1e9
    cd = d - c
    for i in range(6):
        p = a.lerp(b, i / 5)
        t = min(max((p - c).dot(cd) / cd.length_squared, 0.0), 1.0)
        best = min(best, (c + cd * t - p).length)
    return best


def thumb_target(rig, mode):
    S = SCALE
    rt = CHAINS['thumb'][3] * S
    if mode == 'grip':
        return grip_local(rig) + Vector((-0.036, 0.002, 0.006)) * S
    tip = Vector()
    over = ('index', 'middle') if mode == 'fist' else ('middle',)
    for ch in over:
        b2 = rig.pose.bones[ch + '_2']
        m = b2.matrix.to_3x3()
        back, side = m @ Vector((0, 0, 1)), m @ Vector((-1, 0, 0))
        out = back if mode == 'fist' else (back * 0.4 + side).normalized()   # point: against its thumb-side
        tip += (b2.head + b2.tail) / 2 + out.normalized() * (CHAINS[ch][3] * S + rt) * 0.95
    return tip / len(over)


def solve_thumb(rig, mode):
    from mathutils import Euler
    S = SCALE
    bones = rig.data.bones
    rest = [bones['thumb_%d' % i].matrix_local for i in (1, 2, 3)]
    l3 = bones['thumb_3'].length
    rt = CHAINS['thumb'][3] * S
    target = thumb_target(rig, mode)
    others = []
    for ch in ('index', 'middle', 'ring'):
        for i in (1, 2, 3):
            pb = rig.pose.bones['%s_%d' % (ch, i)]
            others.append((pb.head.copy(), pb.tail.copy(), CHAINS[ch][3] * S * (1.12 if i == 3 else 1.0)))
    palm_c, semi = Vector((0, 0.042, 0)) * S, Vector((0.040, 0.034, 0.0155)) * S

    def fk(f1, s1, f2):
        r = [Euler((-math.radians(f1), 0, -math.radians(s1))).to_matrix().to_4x4(),
             Euler((-math.radians(f2), 0, 0)).to_matrix().to_4x4(),
             Euler((-math.radians(f2 * 0.8), 0, 0)).to_matrix().to_4x4()]
        ms = [rest[0] @ r[0]]
        for i in (1, 2):
            ms.append(ms[-1] @ (rest[i - 1].inverted() @ rest[i]) @ r[i])
        return ms

    best = None
    for f1 in range(-60, 71, 5):
        for s1 in range(-50, 51, 5):
            for f2 in range(0, 81, 8):
                ms = fk(f1, s1, f2)
                pts = [ms[1].translation, ms[2].translation, ms[2] @ Vector((0, l3, 0))]
                tip = ms[2] @ Vector((0, l3 + rt * 1.12, 0))
                cost = (tip - target).length * 100
                for a, b in ((pts[0], pts[1]), (pts[1], pts[2])):
                    for c, d, rf in others:
                        cost += 300 * max(0.0, rt + rf - 0.002 - _seg_dist(a, b, c, d))
                for q in pts[1:]:
                    q = q - palm_c
                    if (q.x / (semi.x + rt)) ** 2 + (q.y / (semi.y + rt)) ** 2 + (q.z / (semi.z + rt)) ** 2 < 1:
                        cost += 3
                if best is None or cost < best[0]:
                    best = (cost, f1, s1, f2, (tip - target).length)
    _, f1, s1, f2, miss = best
    rig.pose.bones['thumb_1'].rotation_euler = (-math.radians(f1), 0, -math.radians(s1))
    rig.pose.bones['thumb_2'].rotation_euler = (-math.radians(f2), 0, 0)
    rig.pose.bones['thumb_3'].rotation_euler = (-math.radians(f2 * 0.8), 0, 0)
    bpy.context.view_layer.update()
    print('THUMB %s: flex %d spread %d curl %d  tip miss %.1f mm  cost %.2f' % (mode, f1, s1, f2, miss * 1000, best[0]))


def bake(objs, name, matrix, mirror=False):
    """Static copy of the posed meshes, placed by `matrix` (Blender world)."""
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        if mirror:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.scale(bm, vec=(-1, 1, 1), verts=bm.verts)
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
        c = bpy.data.objects.new(name + o.name, me)
        bpy.context.scene.collection.objects.link(c)
        c.matrix_world = matrix
        out.append(c)
    return out


def tip_local(rig, chain):
    """Fingertip surface point (rig space) in the current pose."""
    pb = rig.pose.bones[chain + '_3']
    r = CHAINS[chain][3] * 1.12 * SCALE
    return pb.tail + (pb.tail - pb.head).normalized() * r


def fit_grip(rig, diameter):
    """Scale the 'grip' curl so the hook (palm under knuckles -> middle tip) wraps a ball of `diameter`."""
    base = dict(POSES['grip'])
    best = None
    for k in range(30, 101, 2):
        c = k / 100
        POSES['_g'] = {ch: tuple(a * c for a in v) for ch, v in base.items()}
        pose(rig, '_g')
        gap = (Vector((0, 0.064, -0.018)) * SCALE - tip_local(rig, 'middle')).length
        if best is None or abs(gap - diameter) < best[0]:
            best = (abs(gap - diameter), c)
    POSES['grip_fit'] = {ch: tuple(a * best[1] for a in v) for ch, v in base.items()}
    pose(rig, 'grip_fit')
    print('GRIP curl x%.2f' % best[1])


def grip_local(rig):
    """Centre of the curled-finger hook (rig space): between the palm under the knuckles and the middle tip."""
    under = Vector((0, 0.064, -0.018)) * SCALE
    return (under + tip_local(rig, 'middle')) / 2


def placement(fwd_g, back_g, wrist_g):
    """Blender world matrix for a hand whose fingers point fwd_g and back faces back_g (Godot vectors)."""
    f, n = Vector(fwd_g).normalized(), Vector(back_g).normalized()
    n = (n - f * n.dot(f)).normalized()
    r = f.cross(n)
    m = Matrix((lib.B(r), lib.B(f), lib.B(n))).transposed().to_4x4()
    m.translation = lib.B(wrist_g)
    return m


# --- style sheet --------------------------------------------------------------------------------

CON_N = Vector((0, math.cos(math.radians(18)), math.sin(math.radians(18))))     # console normal (Godot)
CON_F = Vector((0, math.sin(math.radians(18)), -math.cos(math.radians(18))))    # along the console, away


def control_points():
    """Godot positions of the S key cap top and the joystick ball (centre, radius) from the control GLBs."""
    import audit
    before = set(bpy.data.objects)
    audit.import_controls()
    new = set(bpy.data.objects) - before
    bpy.context.view_layer.update()

    def chain(o):
        while o:
            yield o.name
            o = o.parent
    cap = next(o for o in new if o.name.startswith('Cap_left_2'))
    knob = next(o for o in new if o.name.startswith('Knob') and 'joystick' in chain(o) and o.type == 'MESH')
    pts = [knob.matrix_world @ Vector(c) for c in knob.bound_box]
    centre = sum(pts, Vector()) / 8
    radius = max((p - centre).length for p in pts) / math.sqrt(3)
    out = lib.G(cap.matrix_world.translation), lib.G(centre), radius
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    return out


def _g(m, v):
    return lib.G(m.to_3x3() @ Vector(v))


def export(objs, path):
    for o in bpy.data.objects:
        o.select_set(o in objs)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, use_selection=True,
                              export_cameras=False, export_lights=False, export_image_format='AUTO')
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)


def stub(objs, keep=0.16):
    """Cut a baked sleeve short (for floating line-up hands)."""
    for o in objs:
        if 'Sleeve' in o.name:
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -keep], context='VERTS')
            bm.to_mesh(o.data)
            bm.free()


def sheet(rig, meshes):
    cap, knob, kr = control_points()
    print('S cap', tuple(round(x, 3) for x in cap), 'knob', tuple(round(x, 3) for x in knob), 'r', round(kr, 3))
    out = os.path.join(lib.ROOT, 'previews', 'hands')
    for colour, sleeve_obj in meshes['sleeves'].items():
        objs = [meshes['hand'], meshes['nails'], sleeve_obj]
        baked = []
        # Left hand: index finger hovering 12 mm over the S key.
        pose(rig, 'point')
        m = placement(CON_F, CON_N, (0, 0, 0))
        tip = tip_local(rig, 'index')
        tip.x = -tip.x
        wrist = cap + CON_N * 0.012 - _g(m, tip)
        baked += bake(objs, 'L_', placement(CON_F, CON_N, wrist), mirror=True)
        # Right hand: palm on top of the joystick ball, fingers over its front.
        fit_grip(rig, 2 * kr)
        wrist = knob - _g(m, grip_local(rig))
        print('GRIP hook gap %.3f (ball %.3f)' % ((Vector((0, 0.064, -0.018)) * SCALE - tip_local(rig, 'middle')).length,
                                                 2 * kr))
        baked += bake(objs, 'R_', placement(CON_F, CON_N, wrist))
        export(baked, os.path.join(out, 'sheet_%s.glb' % colour))
    # Line-ups: the four poses side by side in front of the seat, fingers up, seen from the back, thumb side, palm.
    objs = [meshes['hand'], meshes['nails'], meshes['sleeves']['teal']]
    for view, yaw_deg in (('lineup', -32), ('lineup_thumb', 75), ('lineup_palm', 165)):
        baked = []
        for i, name in enumerate(('relaxed', 'point', 'fist', 'grip')):
            pose(rig, name)
            yaw = math.radians(yaw_deg)
            back = Vector((math.sin(yaw), 0.0, math.cos(yaw)))
            b = bake(objs, '%s_' % name, placement((0, 1, 0.25), back, (-0.27 + i * 0.18, 1.06, 0.36)))
            stub(b)
            baked += b
        export(baked, os.path.join(out, view + '.glb'))


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    lib.reset()
    parts = model_parts()
    hand = union(parts)
    hand.data.materials.append(lib.mat('Skin', SKIN, 0.55))
    nl = nails()
    nl.data.materials.append(lib.mat('Nail', NAIL, 0.35))
    rig = armature()
    skin(hand, parts, rig, nl)
    for p in parts.values():
        bpy.data.objects.remove(p, do_unlink=True)
    sleeves = {}
    for colour in KNITS:
        s = sleeve(colour)
        s.name = 'Sleeve_' + colour
        g = s.vertex_groups.new(name='forearm')
        g.add(list(range(len(s.data.vertices))), 1.0, 'REPLACE')
        s.parent = rig
        s.modifiers.new('Armature', 'ARMATURE').object = rig
        sleeves[colour] = s
    for o in (hand, nl, *sleeves.values()):           # modelled at 1.0, weights done; scale the rest data
        o.data.transform(Matrix.Scale(SCALE, 4))
    rig.data.transform(Matrix.Scale(SCALE, 4))
    lo = [min(v.co[i] for v in hand.data.vertices) for i in range(3)]
    hi = [max(v.co[i] for v in hand.data.vertices) for i in range(3)]
    print('HAND tris=%d  x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f' % (
        sum(len(p.vertices) - 2 for p in hand.data.polygons), lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    sheet(rig, {'hand': hand, 'nails': nl, 'sleeves': sleeves})
    pose(rig, 'relaxed')
    os.makedirs(os.path.join(lib.ROOT, 'source', 'hands'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(lib.ROOT, 'source', 'hands', 'hands.blend'))
    print('HANDS_BUILT')


main()
