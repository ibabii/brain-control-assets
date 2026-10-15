"""Full-body pose solver for the Human's clips: a pose is the Hips placement, per-bone rotations in the character's
rest frame, two-bone IK limbs (target + pole) and world-oriented hands/feet. Godot coords in, Blender keys out.

Pose dict (all optional):
  hips   (pos, euler)        Hips head position and body rotation (Godot euler, degrees)
  rot    {bone: euler}       rotation at the bone's head in the rest frame, carried by the parent
                             (UpperArm is relative to the hanging design pose)
  ik     {limb: (target, pole)}  limb = LeftArm|RightArm|LeftLeg|RightLeg; target = wrist/ankle, pole = elbow/knee side
  world  {bone: euler|Matrix} bone orientation = rest orientation turned by this in world space (hands, feet)
  ground True                shift the Hips so the lowest visible vertex sits on the floor (+ `lift` m)
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

import lib
from lib import B, G

C = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))            # Godot -> Blender basis
LIMBS = {'LeftArm': ('LeftUpperArm', 'LeftLowerArm', -1), 'RightArm': ('RightUpperArm', 'RightLowerArm', -1),
         'LeftLeg': ('LeftUpperLeg', 'LeftLowerLeg', 1), 'RightLeg': ('RightUpperLeg', 'RightLowerLeg', 1)}
ARM_UP = 0.0                                             # set by the build (bind A-pose angle)


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
            pos, e = pose['hips']
            P[b.name] = Matrix.Translation(B(pos)) @ grot(e) @ Matrix.Translation(-head) @ R
            continue
        P[b.name] = carry @ about(D, head) @ R
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
    """Hips head position (Godot) and pitch (degrees, + = leaning back) for the json."""
    m = P['Hips']
    up = G(m.to_3x3() @ Vector((0, 1, 0)))
    pitch = math.degrees(math.atan2(up.z, up.y))
    return {'pos': [round(x, 4) for x in G(m.to_translation())], 'pitch': round(pitch, 1)}


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
