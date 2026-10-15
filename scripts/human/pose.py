"""Full-body pose solver for the Human's clips: a pose is the Hips placement, per-bone rotations in the character's
rest frame, two-bone IK limbs (target + pole) and world-oriented hands/feet. Godot coords in, Blender keys out.

Pose dict (all optional):
  hips   (pos, euler)        Hips head position and body rotation (Godot euler, degrees)
  rot    {bone: euler}       rotation at the bone's head in the rest frame, carried by the parent
  local  {bone: euler}       Blender bone-local XYZ euler (degrees) on top of the rest (finger poses)
                             (UpperArm is relative to the hanging design pose)
  ik     {limb: (target, pole)}  limb = LeftArm|RightArm|LeftLeg|RightLeg; target = wrist/ankle, pole = elbow/knee side
  world  {bone: euler|Matrix} bone orientation = rest orientation turned by this in world space (hands, feet)
  ground True                shift the Hips so the lowest visible vertex sits on the floor (+ `lift` m)
"""
import math

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

import lib
from lib import B, G

C = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))            # Godot -> Blender basis
LIMBS = {'LeftArm': ('LeftUpperArm', 'LeftLowerArm', -1), 'RightArm': ('RightUpperArm', 'RightLowerArm', -1),
         'LeftLeg': ('LeftUpperLeg', 'LeftLowerLeg', 1), 'RightLeg': ('RightUpperLeg', 'RightLowerLeg', 1)}
ARM_UP = 0.0                                             # set by the build (bind A-pose angle)
MARKERS = {}                                             # name -> marker dict (rig.markers), set by the build


def grot(deg):
    """Godot euler (or a Godot 3x3 Matrix) -> Blender 4x4."""
    m = deg if isinstance(deg, Matrix) else lib.rot(deg)
    return (C @ m @ C.inverted()).to_4x4()


def about(m4, pivot):
    return Matrix.Translation(pivot) @ m4 @ Matrix.Translation(-pivot)


def _order(rig):
    out = []

    def walk(b):
        out.append(b)
        for c in b.children:
            walk(c)
    for b in rig.data.bones:
        if b.parent is None:
            walk(b)
    return out


def _down(name):
    """The hanging design pose: upper arms rotated down from the A-pose bind about the body's forward axis."""
    if not name.endswith('UpperArm'):
        return Matrix.Identity(4)
    s = -1 if name.startswith('Left') else 1
    return Quaternion(B((0, 0, 1)), math.radians(-s * ARM_UP)).to_matrix().to_4x4()


def solve(rig, pose):
    """Armature-space matrices for every bone."""
    rot = pose.get('rot', {})
    ik = pose.get('ik', {})
    world = pose.get('world', {})
    local = pose.get('local', {})
    upper_ik = {LIMBS[k][0]: k for k in ik}
    P = {}
    for b in _order(rig):
        if b.name in P:
            continue
        R = b.matrix_local
        head = R.to_translation()
        carry = P[b.parent.name] @ b.parent.matrix_local.inverted() if b.parent else Matrix.Identity(4)
        D = grot(rot[b.name]) if b.name in rot else Matrix.Identity(4)
        D = D @ _down(b.name)
        if b.name == 'Hips' and 'hips' in pose:
            pos, e = pose['hips']                                 # e: Godot euler or 3x3 turn
            P[b.name] = Matrix.Translation(B(pos)) @ grot(e) @ Matrix.Translation(-head) @ R
            continue
        P[b.name] = carry @ about(D, head) @ R
        if b.name in local:
            P[b.name] = P[b.name] @ Euler([math.radians(a) for a in local[b.name]], 'XYZ').to_matrix().to_4x4()
        if b.name in upper_ik:
            _limb(rig, P, upper_ik[b.name], *ik[upper_ik[b.name]])
        if b.name in world:
            h = P[b.name].to_translation()
            P[b.name] = Matrix.Translation(h) @ grot(world[b.name]) @ R.to_3x3().to_4x4()
    return P


def _limb(rig, P, limb, target, pole):
    up, lo, sign = LIMBS[limb]
    bu, bl = rig.data.bones[up], rig.data.bones[lo]
    a = P[up].to_translation()
    l1, l2 = bu.length, bl.length
    t, p = B(target), B(pole)
    d_vec = t - a
    d = max(abs(l1 - l2) + 1e-3, min(d_vec.length, l1 + l2 - 1e-4))
    n = d_vec.normalized()
    pp = (p - a) - n * (p - a).dot(n)
    pp = pp.normalized()
    cos_a = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    sin_a = math.sqrt(max(0.0, 1 - cos_a * cos_a))
    elbow = a + n * l1 * cos_a + pp * l1 * sin_a
    wrist = a + n * d
    u = (elbow - a).normalized()
    f = (wrist - elbow).normalized()
    z = pp - u * pp.dot(u)
    z = (z.normalized() if z.length > 1e-6 else Vector((0, -1, 0))) * sign   # arms bend away from the pole
    x = u.cross(z).normalized()
    z = x.cross(u)
    P[up] = _frame(x, u, z, a)
    P[lo] = _frame(x, f, x.cross(f), elbow)


def _frame(x, y, z, o):
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = o
    return m


def apply(rig, P):
    for b in rig.data.bones:
        pb = rig.pose.bones[b.name]
        R = b.matrix_local
        if b.parent:
            Rp = b.parent.matrix_local
            mb = (Rp.inverted() @ R).inverted() @ P[b.parent.name].inverted() @ P[b.name]
        else:
            mb = R.inverted() @ P[b.name]
        pb.rotation_mode = 'QUATERNION'
        pb.matrix_basis = mb


def lowest(rig):
    """Lowest visible vertex (Godot y) of everything the rig carries, in the current pose."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    lo = 9.0
    for o in rig.children_recursive:
        if o.type != 'MESH' or o.get('hidden'):
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        lo = min(lo, min((mw @ v.co).z for v in me.vertices))
        ev.to_mesh_clear()
    return lo


def pose_at(rig, pose, dy=0.0):
    """Solve + apply, with the Hips moved up by dy (grounding is done by the caller, measured on the keyed frame)."""
    if dy:
        pos, e = pose.get('hips', (G(rig.data.bones['Hips'].head_local), (0, 0, 0)))
        pose = dict(pose, hips=(Vector(pos) + Vector((0, dy, 0)), e))
    P = solve(rig, pose)
    apply(rig, P)
    return P


def key(rig, frame, bones, prev):
    """Keyframe `bones` (rotation; Hips also location) at `frame`, keeping quaternions on one hemisphere."""
    for n in bones:
        pb = rig.pose.bones[n]
        q = pb.rotation_quaternion.copy()
        if n in prev and q.dot(prev[n]) < 0:
            q.negate()
        pb.rotation_quaternion = q
        prev[n] = q
        pb.keyframe_insert('rotation_quaternion', frame=frame)
        if n == 'Hips':
            pb.keyframe_insert('location', frame=frame)


def hips_info(P):
    """Hips head position (Godot), pitch (degrees, + = leaning back) and yaw (+ = turned left) for the json."""
    m = P['Hips']
    up = G(m.to_3x3() @ Vector((0, 1, 0)))
    fwd = G(m.to_3x3() @ Vector((0, 0, 1)))                # the Hips bone's Z is the body's forward at rest
    pitch = math.degrees(math.atan2(up.z, up.y))
    yaw = math.degrees(math.atan2(-fwd.x, -fwd.z))
    return {'pos': [round(x, 4) for x in G(m.to_translation())], 'pitch': round(pitch, 1), 'yaw': round(yaw, 1)}


def grip(rig, side, pos, basis):
    """IK target (wrist) and world turn for the hand so marker Grip_<L|R> lands at `pos` with `basis` (Godot 3x3,
    columns = marker X, Y, Z)."""
    n = 'Left' if side < 0 else 'Right'
    m = MARKERS['Grip_' + ('L' if side < 0 else 'R')]
    mk = Matrix([m['basis'][0], m['basis'][1], m['basis'][2]]).transposed()      # rest marker frame (Godot)
    rest_m = mk.to_4x4()
    rest_m.translation = Vector(m['pos'])
    want = Matrix(basis).to_4x4()
    want.translation = Vector(pos)
    Rh = rig.data.bones[n + 'Hand'].matrix_local
    Cm = C.to_4x4()
    hand = Cm @ want @ rest_m.inverted() @ Cm.inverted() @ Rh            # posed hand bone (Blender armature space)
    turn = C.inverted() @ (hand.to_3x3() @ Rh.to_3x3().inverted()) @ C
    return G(hand.to_translation()), turn


def penetration(rig, boxes, tol=0.01):
    """Visible vertices deeper than `tol` inside any box [(lo, hi) Godot]; returns (count, worst depth, per mesh+box)."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    n, worst, where = 0, 0.0, {}
    for o in rig.children_recursive:
        if o.type != 'MESH' or o.get('hidden'):
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        for v in me.vertices:
            p = G(mw @ v.co)
            for k, (lo, hi) in enumerate(boxes):
                d = min(min(p[i] - lo[i], hi[i] - p[i]) for i in range(3))
                if d > tol:
                    n += 1
                    worst = max(worst, d)
                    w = where.setdefault('%s@box%d' % (o.name, k), [0, 0.0, None])
                    w[0] += 1
                    if d > w[1]:
                        w[1], w[2] = d, [round(x, 2) for x in p]
        ev.to_mesh_clear()
    return n, worst, where


# --- in-betweens: blend the pose targets, not the joint rotations (planted hands/feet stay planted) --------

LIMB_BONES = {'LeftUpperArm', 'LeftLowerArm', 'RightUpperArm', 'RightLowerArm', 'LeftUpperLeg', 'LeftLowerLeg',
              'RightUpperLeg', 'RightLowerLeg', 'LeftHand', 'RightHand', 'LeftFoot', 'RightFoot'}


def _turn(rig, P, bone):
    R = rig.data.bones[bone].matrix_local
    return C.inverted() @ (P[bone].to_3x3() @ R.to_3x3().inverted()) @ C


def normalize(rig, pose, P):
    """The solved pose as targets: Hips placement, IK wrists/ankles + poles for all limbs, world hands/feet."""
    hips_r = rig.data.bones['Hips'].matrix_local
    head = hips_r.to_translation()
    turn = P['Hips'].to_3x3() @ hips_r.to_3x3().inverted()
    pos = G(P['Hips'].to_translation())
    ik = {}
    for limb, (up, lo, sign) in LIMBS.items():
        e = G(P[lo].to_translation())
        w = G(P[lo] @ Vector((0, rig.data.bones[lo].length, 0)))
        z = G(P[up].to_3x3() @ Vector((0, 0, 1)))                    # the bend plane, even for a straight limb
        ik[limb] = (w, e + z * (0.3 * sign))
    world = {b: _turn(rig, P, b) for b in ('LeftHand', 'RightHand', 'LeftFoot', 'RightFoot')}
    rot = {k: v for k, v in pose.get('rot', {}).items() if k not in LIMB_BONES}
    return {'hips': (pos, C.inverted() @ turn @ C), 'ik': ik, 'world': world, 'rot': rot,
            'local': dict(pose.get('local', {})), 'ground': pose.get('ground', False), 'lift': pose.get('lift', 0.0)}


def _cr(p0, p1, p2, p3, t):
    """Catmull-Rom between p1 and p2."""
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def _slerp(m0, m1, t):
    q0, q1 = m0.to_quaternion(), m1.to_quaternion()
    if q0.dot(q1) < 0:
        q1.negate()
    return q0.slerp(q1, t).to_matrix()


def between(n0, n1, n2, n3, t):
    """Targets at t in [0, 1] between normalized keys n1 and n2 (n0, n3: neighbours for the position spline)."""
    s = t * t * (3 - 2 * t)                                              # rotations ease
    pos = _cr(n0['hips'][0], n1['hips'][0], n2['hips'][0], n3['hips'][0], t)
    ik = {}
    for k in n1['ik']:
        w = _cr(n0['ik'][k][0], n1['ik'][k][0], n2['ik'][k][0], n3['ik'][k][0], t)
        move = (n2['ik'][k][0] - n1['ik'][k][0]).length
        if move < 0.03:                                                  # planted or shuffling: no spline overshoot
            w = n1['ik'][k][0].lerp(n2['ik'][k][0], s)
        if k.endswith('Leg') and move > 0.03:                            # a stepping foot clears the floor
            w = w + Vector((0, 4 * t * (1 - t) * min(0.09, 0.4 * move), 0))
        ik[k] = (w, n1['ik'][k][1].lerp(n2['ik'][k][1], s))
    world = {k: _slerp(n1['world'][k], n2['world'][k], s) for k in n1['world']}
    rot = {}
    for k in set(n1['rot']) | set(n2['rot']):
        a, b = Vector(n1['rot'].get(k, (0, 0, 0))), Vector(n2['rot'].get(k, (0, 0, 0)))
        rot[k] = tuple(a.lerp(b, s))
    local = {}
    for k in set(n1['local']) | set(n2['local']):
        a, b = Vector(n1['local'].get(k, (0, 0, 0))), Vector(n2['local'].get(k, (0, 0, 0)))
        local[k] = tuple(a.lerp(b, s))
    return {'hips': (pos, _slerp(n1['hips'][1], n2['hips'][1], s)), 'ik': ik, 'world': world, 'rot': rot,
            'local': local, 'ground': n1['ground'] and n2['ground'],
            'lift': n1['lift'] + (n2['lift'] - n1['lift']) * s}
