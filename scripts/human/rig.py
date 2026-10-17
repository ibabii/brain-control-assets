"""The Human's rig: SkeletonProfileHumanoid bone names, skin weights, finger/idle clips, markers and the ragdoll spec
(contract: coordination/interfaces.md "Human rig"). Godot coords in (lib convention), Blender bones out.
"""
import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
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


def soften_knuckles(o, side, passes=4):
    """The skin between the fingers is weighted to the palm, so spread or curled fingers stretch it into a web.
    Smooth weights in a band around the knuckles (+-2 cm) so that skin follows the fingers on both sides."""
    n = side_name(side)
    hb = {b[0]: b for b in HAND_BONES[side]}
    knuckles = [hb[f + 'Proximal'][1] for f in ('Index', 'Middle', 'Ring')]
    k0 = sum(knuckles, Vector()) / 3
    axis = (hb['Hand'][2] - hb['Hand'][1]).normalized()
    mw = o.matrix_world
    me = o.data
    idx = {g.index: g.name for g in o.vertex_groups}
    ws = [{idx[g.group]: g.weight for g in v.groups} for v in me.vertices]
    band = [abs((G(mw @ v.co) - k0).dot(axis)) < 0.02 for v in me.vertices]
    nb = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        nb[a].append(b)
        nb[b].append(a)
    for _ in range(passes):
        new = list(ws)
        for i in range(len(ws)):
            if not band[i]:
                continue
            acc = dict(ws[i])
            for j in nb[i]:
                for k, x in ws[j].items():
                    acc[k] = acc.get(k, 0) + x
            tot = sum(acc.values())
            new[i] = {k: x / tot for k, x in acc.items()}
        ws = new
    for g in list(o.vertex_groups):
        o.vertex_groups.remove(g)
    for i, w in enumerate(ws):
        top4 = sorted(w.items(), key=lambda kv: -kv[1])[:4]
        tot = sum(x for _, x in top4)
        for k, x in top4:
            g = o.vertex_groups.get(k) or o.vertex_groups.new(name=k)
            g.add([i], x / tot, 'REPLACE')


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
            pb.rotation_mode = 'QUATERNION'                       # one mode for every clip (body clips bake quaternions)
            pb.rotation_quaternion = Euler([math.radians(a) for a in rots[pb.name]], 'XYZ').to_quaternion()
            pb.keyframe_insert('rotation_quaternion', frame=frame)


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
                spread = {'Index': 6, 'Middle': 0, 'Ring': -6, 'Thumb': 12}[f] if i == 0 else 0.0
            else:
                a, spread = 0.0, 0.0
            r[n + f + sg] = (a, 0.0, spread * side * (1 if f != 'Thumb' else -1))
    return r


def squeeze(side):
    """Grip -> clench (fingers curl in, thumb presses, wrist flexes) -> hold -> back to grip, 0.8 s."""
    n = side_name(side)
    g = finger_pose(side, 'grip')
    tight = {}
    for b, (x, y, z) in g.items():
        tight[b] = (x - (6 if 'Thumb' in b else 12), y, z)
    tight[n + 'ThumbDistal'] = (g[n + 'ThumbDistal'][0] - 20, 0, 0)
    tight[n + 'Hand'] = (-12, 0, 0)
    rest_hand = {n + 'Hand': (0, 0, 0)}
    return [(0, dict(g, **rest_hand)), (6, tight), (16, tight), (24, dict(g, **rest_hand))]


def _arms_down(rig, arm_up, frame):
    """Key the upper arms from the bind A-pose down to the hanging pose (rotation about the body's forward axis)."""
    from mathutils import Quaternion
    for s, n in ((-1, 'Left'), (1, 'Right')):
        pb = rig.pose.bones[n + 'UpperArm']
        rest = rig.data.bones[n + 'UpperArm'].matrix_local.to_quaternion()
        q = Quaternion(B((0, 0, 1)), math.radians(-s * arm_up))
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = rest.inverted() @ q @ rest
        pb.keyframe_insert('rotation_quaternion', frame=frame)


CLIPS = {}          # clip -> {'layer': full|upper|hand, 'bones': [...]} (human_rig.json; the import trims to these)
LOOPS = ['idle']


def is_finger(b):
    return any(f in b for f in FINGERS)


def clip_bones(rig, layer, side=None, wrist=False):
    names = [b.name for b in rig.data.bones]
    if layer == 'all':
        return names
    if layer == 'full':
        return [b for b in names if not is_finger(b) and b != 'Root']
    if layer == 'neck':                                      # head tilts over any arms (phone wedged on the shoulder)
        return [b for b in names if b in ('UpperChest', 'Neck', 'Head') or 'Shoulder' in b]
    if layer == 'torso':                                     # gestures over any lower body (standing, seated)
        return [b for b in names if b in ('Spine', 'Chest', 'UpperChest', 'Neck', 'Head') or 'Shoulder' in b
                or 'Arm' in b or 'Hand' in b or is_finger(b)]
    n = side_name(side)
    if layer == 'upper':
        return [b for b in names if b.startswith(n) and ('Shoulder' in b or 'Arm' in b or 'Hand' in b or is_finger(b))]
    return [b for b in names if b.startswith(n) and is_finger(b)] + ([n + 'Hand'] if wrist else [])


def clips(rig, arm_up, landmarks, full=True, mock=False):
    """NLA tracks (glTF exports one animation each): RESET/rest, idle (arms hanging), hand_{grip,relaxed,spread}_{L,R}."""
    bpy.context.scene.render.fps = FPS
    rig.animation_data_create()
    names = []

    def clip(name, frames, arms=False, layer='full', side=None, wrist=False):
        CLIPS[name] = {'layer': layer, 'bones': clip_bones(rig, layer, side, wrist)}
        act = bpy.data.actions.new(name)
        rig.animation_data.action = act
        for f, rots in frames:
            _key(rig, f, rots)
            if arms:
                _arms_down(rig, arm_up, f)
        rig.animation_data.action = None
        for pb in rig.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0)
        tr = rig.animation_data.nla_tracks.new()
        tr.name = name
        tr.strips.new(name, 0, act)
        for pb in rig.pose.bones:
            pb.rotation_euler = (0, 0, 0)
        names.append(name)
    for n in ('RESET', 'rest'):                                  # the design pose (arms hanging), every bone
        clip(n, [(0, {'Hips': (0, 0, 0)}), (1, {'Hips': (0, 0, 0)})], arms=True, layer='all')
    idle = []
    for k in range(0, 91, 10):                                   # 3 s breathing loop
        a = math.sin(2 * math.pi * k / 90)
        idle.append((k, {'Chest': (-1.4 * a, 0, 0), 'UpperChest': (-1.0 * a, 0, 0), 'Head': (1.6 * a, 0, 0),
                         'LeftShoulder': (0, 0, 1.2 * a), 'RightShoulder': (0, 0, -1.2 * a)}))
    clip('idle', idle, arms=True)
    import body_clips
    import pose as PZ
    PZ.ARM_UP = arm_up
    PZ.MARKERS = {m['name']: m for m in markers(landmarks)}
    full_set = dict(body_clips.FULL, **(body_clips.MOCK if mock else {})) if full else {}
    for name, fn in full_set.items():               # other bodies share these by retarget (character mock)
        names.append(body_clip(rig, name, fn(), boxes=body_clips.BOXES.get(name)))
    for name, (fn, side) in (body_clips.UPPER.items() if full else ()):
        names.append(body_clip(rig, name, fn(rig), layer='upper', side=side))
    for name, fn in (body_clips.TORSO.items() if full else ()):
        names.append(body_clip(rig, name, fn(), layer='torso'))
    for name, (fn, side) in (body_clips.HOLDS.items() if full else ()):
        names.append(body_clip(rig, name, fn(rig), layer='upper', side=side))
    for name, fn in (body_clips.NECK.items() if full else ()):
        names.append(body_clip(rig, name, fn(), layer='neck'))
    LOOPS.extend(n for n in body_clips.LOOPS if n not in LOOPS)
    for s in (-1, 1):
        for kind in ('grip', 'relaxed', 'spread'):
            p = finger_pose(s, kind)
            clip('hand_%s_%s' % (kind, 'L' if s < 0 else 'R'), [(0, p), (1, p)], layer='hand', side=s)
        clip('squeeze_%s' % ('L' if s < 0 else 'R'), squeeze(s), layer='hand', side=s, wrist=True)
    return names


def body_clip(rig, name, keys, layer='full', side=None, boxes=None):
    """Bake pose keys (body_clips.py) into an NLA track; the json records the bones and the Hips at both ends."""
    import pose as PZ
    act = bpy.data.actions.new(name)
    rig.animation_data.action = act
    rig.animation_data.use_nla = False                       # only this action while measuring
    bones = clip_bones(rig, layer, side)
    prev, ends = {}, []
    scene = bpy.context.scene
    norms = []
    for f, p in keys:                       # 1: the keys, grounded and measured on the keyed frame
        P = PZ.pose_at(rig, p)
        PZ.key(rig, f, bones, prev)
        scene.frame_set(f)
        if p.get('ground'):
            P = PZ.pose_at(rig, p, p.get('lift', 0.0) - PZ.lowest(rig))
            PZ.key(rig, f, bones, prev)
            scene.frame_set(f)
        low = PZ.lowest(rig)
        hit = PZ.penetration(rig, boxes or [((-5, -1, -5), (5, 0, 5))])
        print('CLIP %s f%d lowest %.3f inside %d (%.3f m) %s' % (name, f, low, hit[0], hit[1], hit[2] or ''))
        ends.append(PZ.hips_info(P))
        norms.append(PZ.normalize(rig, p, P))
    for i in range(len(keys) - 1):          # 2: in-betweens every 2 frames from the blended targets
        f1, f2 = keys[i][0], keys[i + 1][0]
        n0, n3 = norms[max(i - 1, 0)], norms[min(i + 2, len(keys) - 1)]
        for f in range(f1 + 2, f2 - 1, 2):
            q = PZ.between(n0, norms[i], norms[i + 1], n3, (f - f1) / (f2 - f1))
            PZ.pose_at(rig, q)
            PZ.key(rig, f, bones, prev)
            if q['ground']:
                scene.frame_set(f)
                PZ.pose_at(rig, q, q['lift'] - PZ.lowest(rig))
                PZ.key(rig, f, bones, prev)
    worst = (0, 0.0, -1, {})                                 # in-betweens too: every second frame
    for f in range(0, keys[-1][0] + 1, 2):
        scene.frame_set(f)
        n, d, where = PZ.penetration(rig, boxes or [((-5, -1, -5), (5, 0, 5))])
        if d > 0.02:
            print('CLIP %s f%d %.3f m %s' % (name, f, d, {k: round(v[1], 3) for k, v in where.items()}))
        if d > worst[1]:
            worst = (n, d, f, where)
    print('CLIP %s sampled worst %.3f m (%d verts) at f%d' % (name, worst[1], worst[0], worst[2]))
    rig.animation_data.action = None
    rig.animation_data.use_nla = True
    scene.frame_set(0)
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    tr = rig.animation_data.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, 0, act)
    CLIPS[name] = {'layer': layer, 'bones': bones, 'start': ends[0], 'end': ends[-1],
                   'length': round(keys[-1][0] / FPS, 3)}
    import body_clips
    if name == 'walk_loop':
        CLIPS[name]['locomotion'] = dict(body_clips.WALK)
    return name


# --- markers and ragdoll (human_rig.json) -------------------------------------------------------------------

def markers(L):
    out = []
    for s in (-1, 1):
        n, sfx = side_name(s), ('L' if s < 0 else 'R')
        d = Vector((L['FORE'].x * s, L['FORE'].y, L['FORE'].z))
        back = Vector((L['BACK'].x * s, L['BACK'].y, L['BACK'].z))
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
    # Bite: a slice clamped by a corner in the teeth (expression bite), hanging face-on; the basis tilts it 35 deg
    # forward off the chin and turns it 10 deg (props/toast_bitten: origin at the clamped corner)
    from mathutils import Euler
    m = Euler((math.radians(35), math.radians(-10), 0), 'YXZ').to_matrix()
    out.append({'name': 'Bite', 'bone': 'Head', 'pos': [0.004, 1.5225, -0.112],
                'basis': [list(m.col[0]), list(m.col[1]), list(m.col[2])]})
    # PhoneEar: the phone (props/phone, centre pivot, long axis X, screen +Y) flat against the right ear, screen to
    # the ear, speaker end back by the ear and the mic end down toward the mouth (phone_wedge)
    x = Vector((0, -0.45, -0.89)).normalized()
    y = Vector((-1, 0, 0))
    out.append({'name': 'PhoneEar', 'bone': 'Head', 'pos': [0.162, 1.585, -0.02], 'basis': [list(x), list(y), list(x.cross(y))]})
    return out


def ragdoll(table):
    """Bodies: capsule along the bone (or across, for the trunk), mass, joint at the bone head."""
    bt = {b[0]: b for b in table}
    spec = []

    def body(bone, mass, radius, joint, across=None, length=None, centre=None, shape='capsule', **lim):
        _, h, t, up, par = bt[bone]
        axis = (t - h).normalized()
        ln = length or (t - h).length
        c = centre or (h + t) / 2
        cap_axis = Vector(across) if across else axis
        bend = Vector((1, 0, 0))                                 # hinge axis: lateral (elbows, knees)
        spec.append({'name': 'Physical Bone ' + bone, 'bone': bone, 'mass': mass, 'shape': shape, 'radius': radius,
                     'height': max(ln if across else ln + 1.2 * radius, 2 * radius + 0.01),   # across: total width
                     'centre': list(c), 'axis': list(cap_axis.normalized()),
                     'joint': dict(type=joint, pos=list(h), along=list(axis), bend=list(bend), **lim)})
    body('Hips', 11.0, 0.13, 'none', across=(1, 0, 0), length=0.36, centre=Vector((0, 0.88, 0)))
    body('Spine', 9.0, 0.13, 'cone', across=(1, 0, 0), length=0.38, centre=Vector((0, 1.04, -0.012)), swing=25, twist=25)   # active ragdoll: torso twist (2026-10-16)
    body('Chest', 14.0, 0.135, 'cone', across=(1, 0, 0), length=0.42, centre=Vector((0, 1.25, 0)), swing=25, twist=25)
    body('Head', 6.0, 0.135, 'cone', length=0.06, centre=Vector((0, 1.62, 0.0)), swing=35, twist=40,
         shape='sphere')   # near-round capsules sink into boxes under Jolt
    for s in (-1, 1):
        n = side_name(s)
        body(n + 'UpperArm', 2.5, 0.062, 'cone', swing=100, twist=40)   # arms over the head when flailing
        body(n + 'LowerArm', 1.6, 0.055, 'hinge', lower=-135, upper=0)
        body(n + 'Hand', 0.6, 0.042, 'cone', swing=40, twist=25, shape='sphere')
        body(n + 'UpperLeg', 8.0, 0.083, 'cone', swing=45, twist=20)
        body(n + 'LowerLeg', 4.0, 0.074, 'hinge', lower=0, upper=125)
        _, h, t, _, _ = bt[n + 'Foot']
        body(n + 'Foot', 1.2, 0.05, 'cone', length=0.26, centre=Vector((h.x, 0.06, -0.05)), across=(0, 0, -1), swing=25,
             twist=10)
    return spec
