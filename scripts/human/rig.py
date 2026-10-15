"""The Human's rig: SkeletonProfileHumanoid bone names, skin weights, finger/idle clips, markers and the ragdoll spec
(contract: coordination/interfaces.md "Human rig"). Godot coords in (lib convention), Blender bones out.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import lib
from lib import B, G

FPS = 30
PARTS = {}          # mesh family -> {part: BVH} (filled by the builders before the voxel union)
HAND_BONES = {}     # side -> [(name, head, tail, up, parent)] from the brain hand's relaxed pose
FINGERS = ('Thumb', 'Index', 'Middle', 'Ring')
SEG = {'Thumb': ('Metacarpal', 'Proximal', 'Distal'), 'Index': ('Proximal', 'Intermediate', 'Distal'),
       'Middle': ('Proximal', 'Intermediate', 'Distal'), 'Ring': ('Proximal', 'Intermediate', 'Distal')}
BRAIN_TO_HUMAN = {'forearm': 'LowerArm', 'wrist': 'Hand', 'palm': 'Hand'}
for _f in FINGERS:
    for _i, _s in enumerate(SEG[_f]):
        BRAIN_TO_HUMAN['%s_%d' % (_f.lower(), _i + 1)] = _f + _s


def side_name(s):
    return 'Left' if s < 0 else 'Right'      # the Human's left is -X (faces -Z)


def meta_tree(mb):
    """BVH (Godot coords) of one metaball family, without consuming it."""
    src = next(o for o in bpy.data.objects if o.data == mb)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))
    me.calc_loop_triangles()
    verts = [G(src.matrix_world @ v.co) for v in me.vertices]
    t = BVHTree.FromPolygons(verts, [lt.vertices for lt in me.loop_triangles])
    bpy.data.meshes.remove(me)
    return t


# --- skeleton -----------------------------------------------------------------------------------------------

def bone_table(L):
    """[(name, head, tail, up, parent)] in Godot coords. L = landmarks dict from the build."""
    fwd = Vector((0, 0, -1))
    t = [('Root', Vector((0, 0, 0)), Vector((0, 0.12, 0)), fwd, None),
         ('Hips', Vector((0, 0.84, 0)), Vector((0, 0.98, 0)), fwd, 'Root'),
         ('Spine', Vector((0, 0.98, 0)), Vector((0, 1.10, -0.005)), fwd, 'Hips'),
         ('Chest', Vector((0, 1.10, -0.005)), Vector((0, 1.24, 0)), fwd, 'Spine'),
         ('UpperChest', Vector((0, 1.24, 0)), Vector((0, 1.36, 0.01)), fwd, 'Chest'),
         ('Neck', Vector((0, 1.36, 0.01)), Vector((0, 1.47, 0)), fwd, 'UpperChest'),
         ('Head', Vector((0, 1.47, 0)), Vector((0, 1.76, 0)), fwd, 'Neck')]
    for s in (-1, 1):
        n = side_name(s)
        m = lambda v: Vector((v.x * s, v.y, v.z))
        up = Vector((0, 1, 0))
        t += [(n + 'Shoulder', m(Vector((0.035, 1.335, 0.0))), m(L['SHOULDER']), up, 'UpperChest'),
              (n + 'UpperArm', m(L['SHOULDER']), m(L['ELBOW']), fwd, n + 'Shoulder'),
              (n + 'LowerArm', m(L['ELBOW']), m(L['WRIST']), fwd, n + 'UpperArm')]
        hb = {b[0]: b for b in HAND_BONES[s]}
        t.append((n + 'Hand', m(L['WRIST']), hb['Hand'][2], hb['Hand'][3], n + 'LowerArm'))
        for f in FINGERS:
            for i, sg in enumerate(SEG[f]):
                b = hb[f + sg]
                t.append((n + f + sg, b[1], b[2], b[3], n + 'Hand' if i == 0 else n + f + SEG[f][i - 1]))
        ankle = m(L['ANKLE_J'])
        ball_ = ankle + Vector((0, -0.06, -0.11))
        t += [(n + 'UpperLeg', m(L['HIP']), m(L['KNEE']), fwd, 'Hips'),
              (n + 'LowerLeg', m(L['KNEE']), ankle, fwd, n + 'UpperLeg'),
              (n + 'Foot', ankle, ball_, Vector((0, 1, 0)), n + 'LowerLeg'),
              (n + 'Toes', ball_, ball_ + Vector((0, 0, -0.08)), Vector((0, 1, 0)), n + 'Foot')]
    return t


def armature(table, parent):
    arm = bpy.data.armatures.new('Skeleton')
    rig = bpy.data.objects.new('Rig', arm)
    lib.COLL.objects.link(rig)
    lib.set_parent(rig, parent)
    for o in bpy.data.objects:
        o.select_set(o == rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones
    for name, head, tail, up, par in table:
        b = eb.new(name)
        b.head, b.tail = B(head), B(tail)
        b.align_roll(B(up))
        if par:
            b.parent = eb[par]
            b.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


# --- weights ------------------------------------------------------------------------------------------------

def _ss(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def chain(p, pts, bones, blend):
    """Weights along a joint chain: nearest segment, blended across each inner joint over +-blend metres."""
    seg_d = []
    for a, b in zip(pts, pts[1:]):
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
        seg_d.append(((a + ab * t - p).length, t * ab.length, ab.length))
    k = min(range(len(seg_d)), key=lambda i: seg_d[i][0])
    w = {bones[k]: 1.0}
    _, s, ln = seg_d[k]
    if k > 0 and s < blend:                                    # near the joint with the previous bone
        f = 0.5 + 0.5 * _ss(s / blend)
        w = {bones[k]: f, bones[k - 1]: 1 - f}
    elif k < len(bones) - 1 and ln - s < blend:
        f = 0.5 + 0.5 * _ss((ln - s) / blend)
        w = {bones[k]: f, bones[k + 1]: 1 - f}
    return w


SPINE = [(0.80, 'Hips'), (0.98, 'Hips'), (1.10, 'Spine'), (1.24, 'Chest'), (1.36, 'UpperChest'), (1.47, 'Neck')]


def torso(p):
    """Body by height (Hips .. UpperChest), shoulders blend in at the top corners."""
    ys = [y for y, _ in SPINE]
    pts = [Vector((0, y, 0)) for y in ys]
    w = chain(Vector((0, p.y, 0)), pts[1:], [b for _, b in SPINE[2:]], 0.06)
    if p.y < 0.98:
        w = {'Hips': 1.0}
    sh = _ss((abs(p.x) - 0.09) / 0.08) * _ss((p.y - 1.22) / 0.1)
    if sh > 0:
        n = side_name(p.x)
        w = {k: v * (1 - sh) for k, v in w.items()}
        w[n + 'Shoulder'] = w.get(n + 'Shoulder', 0) + sh
    return w


def arm_w(p, s, L):
    n = side_name(s)
    m = lambda v: Vector((v.x * s, v.y, v.z))
    pts = [m(Vector((0.035, 1.335, 0.0))), m(L['SHOULDER']), m(L['ELBOW']), m(L['WRIST'])]
    return chain(p, pts, [n + 'Shoulder', n + 'UpperArm', n + 'LowerArm'], 0.05)


def leg_w(p, s, L):
    n = side_name(s)
    m = lambda v: Vector((v.x * s, v.y, v.z))
    pts = [m(L['HIP']), m(L['KNEE']), m(L['ANKLE_J'])]
    return chain(p, pts, [n + 'UpperLeg', n + 'LowerLeg'], 0.06)


def mix(a, b, f):
    out = {k: v * (1 - f) for k, v in a.items()}
    for k, v in b.items():
        out[k] = out.get(k, 0) + v * f
    return out


def _part_blend(p, trees, band=0.03):
    """Distance-based membership: {part: share}, the nearest part wins, a soft seam where parts meet."""
    d = {k: (t.find_nearest(p, 0.3)[3] or 0.3) for k, t in trees.items()}
    order = sorted(d, key=d.get)
    a, b = order[0], order[1]
    f = _ss(0.5 + (d[b] - d[a]) / band)                        # 1 deep in a, 0.5 on the seam
    return {a: f, b: 1 - f}


def weights_for(o, kind, L):
    """Per-vertex {bone: w} for one mesh object."""
    mw = o.matrix_world
    out = []
    for v in o.data.vertices:
        p = G(mw @ v.co)
        if kind == 'top':
            share = _part_blend(p, PARTS['top'])
            w = {}
            for part, f in share.items():
                pw = torso(p) if part == 'body' else arm_w(p, -1 if part == 'L' else 1, L)
                w = mix(w, pw, f) if w else {k: x * f for k, x in pw.items()}
        elif kind == 'pants':
            share = _part_blend(p, PARTS['pants'], 0.04)
            w = {}
            for part, f in share.items():
                pw = {'Hips': 1.0} if part == 'body' else leg_w(p, -1 if part == 'L' else 1, L)
                w = mix(w, pw, f) if w else {k: x * f for k, x in pw.items()}
        elif kind == 'torso':
            w = torso(p)
        elif kind == 'neck':
            w = chain(Vector((0, p.y, 0)), [Vector((0, y, 0)) for y in (1.24, 1.36, 1.47, 1.8)],
                      ['UpperChest', 'Neck', 'Head'], 0.035)
        elif kind == 'lowerarm':
            w = {side_name(p.x) + 'LowerArm': 1.0}
        elif kind == 'lowerleg':
            w = {side_name(p.x) + 'LowerLeg': 1.0}
        elif kind == 'foot':
            w = {side_name(p.x) + 'Foot': 1.0}
        else:
            raise ValueError(kind)
        out.append(w)
    return out


def smooth(o, ws, passes=4):
    """Average weights over mesh neighbours (soft joints), then keep the 4 largest and normalise."""
    me = o.data
    nb = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        nb[a].append(b)
        nb[b].append(a)
    for _ in range(passes):
        new = []
        for i, w in enumerate(ws):
            acc = dict(w)
            for j in nb[i]:
                for k, x in ws[j].items():
                    acc[k] = acc.get(k, 0) + x
            tot = sum(acc.values())
            new.append({k: x / tot for k, x in acc.items()})
        ws = new
    out = []
    for w in ws:
        top4 = sorted(w.items(), key=lambda kv: -kv[1])[:4]
        tot = sum(x for _, x in top4)
        out.append({k: x / tot for k, x in top4 if x / tot > 0.01})
    return out


def skin(o, ws, rig):
    for i, w in enumerate(ws):
        for k, x in w.items():
            g = o.vertex_groups.get(k) or o.vertex_groups.new(name=k)
            g.add([i], x, 'REPLACE')
    lib.set_parent(o, rig)
    o.modifiers.new('Armature', 'ARMATURE').object = rig


def attach(o, rig, bone):
    """Rigid child of a bone (exported under the joint; Godot makes a BoneAttachment3D)."""
    mw = o.matrix_world.copy()
    o.parent = rig
    o.parent_type = 'BONE'
    o.parent_bone = bone
    o.matrix_world = mw


# --- clips ---------------------------------------------------------------------------------------------------

def _key(rig, frame, rots):
    """rots: bone -> (x, y, z) degrees about the bone's own axes (Blender pose space)."""
    for pb in rig.pose.bones:
        if pb.name in rots:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = [math.radians(a) for a in rots[pb.name]]
            pb.keyframe_insert('rotation_euler', frame=frame)


def finger_pose(side, kind):
    n = side_name(side)
    r = {}
    for f in FINGERS:
        for i, sg in enumerate(SEG[f]):
            if kind == 'grip':      # closed round a ~2.5 cm handle
                a = {'Thumb': (-15, -35, -30)}.get(f, (-75, -85, -55))[i]
                spread = 0.0
            elif kind == 'spread':  # flailing: straight and fanned out
                a = 8.0 if f != 'Thumb' else 0.0
                spread = {'Index': 12, 'Middle': 0, 'Ring': -12, 'Thumb': 18}[f] if i == 0 else 0.0
            else:
                a, spread = 0.0, 0.0
            r[n + f + sg] = (a, 0.0, spread * side * (1 if f != 'Thumb' else -1))
    return r


def clips(rig):
    """NLA tracks (glTF exports one animation each): rest, idle, hand_{grip,relaxed,spread}_{L,R}."""
    bpy.context.scene.render.fps = FPS
    rig.animation_data_create()
    names = []

    def clip(name, frames):
        act = bpy.data.actions.new(name)
        rig.animation_data.action = act
        for f, rots in frames:
            _key(rig, f, rots)
        rig.animation_data.action = None
        tr = rig.animation_data.nla_tracks.new()
        tr.name = name
        tr.strips.new(name, 0, act)
        for pb in rig.pose.bones:
            pb.rotation_euler = (0, 0, 0)
        names.append(name)
    clip('rest', [(0, {'Hips': (0, 0, 0)}), (1, {'Hips': (0, 0, 0)})])
    idle = []
    for k in range(0, 91, 10):                                   # 3 s breathing loop
        a = math.sin(2 * math.pi * k / 90)
        idle.append((k, {'Chest': (-1.4 * a, 0, 0), 'UpperChest': (-1.0 * a, 0, 0), 'Head': (1.6 * a, 0, 0),
                         'LeftShoulder': (0, 0, 1.2 * a), 'RightShoulder': (0, 0, -1.2 * a)}))
    clip('idle', idle)
    for s in (-1, 1):
        for kind in ('grip', 'relaxed', 'spread'):
            p = finger_pose(s, kind)
            clip('hand_%s_%s' % (kind, 'L' if s < 0 else 'R'), [(0, p), (1, p)])
    return names


# --- markers and ragdoll (human_rig.json) -------------------------------------------------------------------

def markers(L):
    out = []
    for s in (-1, 1):
        n, sfx = side_name(s), ('L' if s < 0 else 'R')
        d = Vector((L['FORE'].x * s, L['FORE'].y, L['FORE'].z))
        back = Vector((s, 0, 0))
        back = (back - d * back.dot(d)).normalized()
        thumb = back.cross(d) if s > 0 else d.cross(back)        # out of the thumb side (forward at rest)
        if thumb.z > 0:
            thumb = -thumb
        x, y = thumb.normalized(), back
        z = x.cross(y)
        wr = Vector((L['WRIST'].x * s, L['WRIST'].y, L['WRIST'].z))
        out.append({'name': 'Grip_' + sfx, 'bone': n + 'Hand', 'pos': list(wr + d * 0.062 - back * 0.033),
                    'basis': [list(x), list(y), list(z)]})
        out.append({'name': 'Sole_' + sfx, 'bone': n + 'Foot', 'pos': [L['ANKLE'].x * s, 0.0, -0.05],
                    'basis': [[1, 0, 0], [0, 1, 0], [0, 0, 1]]})
    out.append({'name': 'EyeCam', 'bone': 'Head', 'pos': [0, L['EYE_Y'], -0.10], 'basis': [[1, 0, 0], [0, 1, 0], [0, 0, 1]]})
    out.append({'name': 'Foam', 'bone': 'Head', 'pos': [0, 1.525, -0.118], 'basis': [[1, 0, 0], [0, 1, 0], [0, 0, 1]]})
    return out


def ragdoll(table):
    """Bodies: capsule along the bone (or across, for the trunk), mass, joint at the bone head."""
    bt = {b[0]: b for b in table}
    spec = []

    def body(bone, mass, radius, joint, across=None, length=None, centre=None, **lim):
        _, h, t, up, par = bt[bone]
        axis = (t - h).normalized()
        ln = length or (t - h).length
        c = centre or (h + t) / 2
        cap_axis = Vector(across) if across else axis
        bend = Vector((1, 0, 0))                                 # hinge axis: lateral (elbows, knees)
        spec.append({'name': 'Physical Bone ' + bone, 'bone': bone, 'mass': mass, 'radius': radius,
                     'height': max(ln if across else ln + 1.2 * radius, 2 * radius + 0.01),   # across: total width
                     'centre': list(c), 'axis': list(cap_axis.normalized()),
                     'joint': dict(type=joint, pos=list(h), along=list(axis), bend=list(bend), **lim)})
    body('Hips', 11.0, 0.13, 'none', across=(1, 0, 0), length=0.36, centre=Vector((0, 0.88, 0)))
    body('Spine', 9.0, 0.13, 'cone', across=(1, 0, 0), length=0.38, centre=Vector((0, 1.04, -0.012)), swing=20, twist=15)
    body('Chest', 14.0, 0.135, 'cone', across=(1, 0, 0), length=0.42, centre=Vector((0, 1.25, 0)), swing=20, twist=15)
    body('Head', 6.0, 0.135, 'cone', length=0.06, centre=Vector((0, 1.62, 0.0)), swing=35, twist=40)
    for s in (-1, 1):
        n = side_name(s)
        body(n + 'UpperArm', 2.5, 0.062, 'cone', swing=75, twist=40)
        body(n + 'LowerArm', 1.6, 0.055, 'hinge', lower=-135, upper=0)
        body(n + 'Hand', 0.6, 0.042, 'cone', swing=40, twist=25)
        body(n + 'UpperLeg', 8.0, 0.083, 'cone', swing=45, twist=20)
        body(n + 'LowerLeg', 4.0, 0.074, 'hinge', lower=0, upper=125)
        _, h, t, _, _ = bt[n + 'Foot']
        body(n + 'Foot', 1.2, 0.05, 'cone', length=0.26, centre=Vector((h.x, 0.06, -0.05)), across=(0, 0, -1), swing=25,
             twist=10)
    return spec
