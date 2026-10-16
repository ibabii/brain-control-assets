"""The Human (the body the brain pilots): style blockout for approval. Brief: docs/human_brief.md.
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/human/build.py
Godot coords throughout (lib convention): feet at the origin, +Y up, faces -Z, the Human's right = +X.
Writes human/art/human.glb (colourway A) and previews/human/human_<id>.glb for every colourway.
Face parts move by node transforms and visibility only (art contract): eyes, lids, brows, mouth set, blush.
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cockpit_v2'))
import lib  # noqa: E402
from lib import B, G, Frame  # noqa: E402
from sculpt import (meta, ell, cap, ball, chain, solid, adopt, Surface, decal, on_curve,  # noqa: E402
                    godot_rot)
sys.path.insert(0, os.path.dirname(__file__))
import rig as R  # noqa: E402
SKIN, NAIL = '#F2A99A', '#F5BCAE'          # same skin as the brain's hands
HAIR, BROW = '#6A4636', '#573729'
INK, TONGUE, BLUSH = '#4E2629', '#D9787A', '#E58F86'
# Colourways: top, rib (cuffs/hem/collar), trousers, shoe upper, sole, laces/strings.
COLOURWAYS = {
    'A': dict(top='#D9A04C', rib='#C58E3F', pants='#2D5C5B', shoe='#F8F4EA', sole='#2D5C5B', lace='#2D5C5B'),
    'B': dict(top='#3F6F6C', rib='#355F5C', pants='#D8C7A8', shoe='#F8F4EA', sole='#454C48', lace='#D9A04C'),
    'C': dict(top='#A9584C', rib='#97493F', pants='#454C48', shoe='#F1E4CF', sole='#D9A04C', lace='#F8F4EA'),
}
# Character-system mock (2026-10-16, coordination/character_system_plan.md): a spec from env HUMAN_SPEC (json).
# The defaults rebuild the shipped Human exactly. look B = the ref style (bigger eyes, thick brows, blush, button nose,
# chunky hair, matte clay); head = head scale about the eye; sex/build = body volumes (build -1 slim .. +1 heavy);
# sy/narrow = height scale below the neck and shoulder narrowing (warp, after weights); chest = female chest key +
# spring bones; clips 'basic' = RESET/rest/idle/hands only (other bodies share the full set by retarget).
SPEC = dict(look='now', head=1.0, sex='male', build=0.0, sy=1.0, narrow=0.0, chest=False, clips='all', hair='short',
            mock=False, keep_eye=False)
SPEC.update(json.loads(os.environ.get('HUMAN_SPEC', '{}')))
LOOK_B = SPEC['look'] == 'B'
IDENT = SPEC['sy'] == 1.0 and not SPEC['narrow'] and SPEC['head'] == 1.0   # no warp: the shipped Human, untouched
FEMALE = SPEC['sex'] == 'female'
BUILD = SPEC['build']
HAND_SCALE = 1.12                          # on top of the brain hand's own 1.2

# Skeleton-ish landmarks (also the future rig joints).
EYE_Y = 1.625
NECK = Vector((0, 1.47, 0.0))
HEAD_PIVOT = Vector((0, EYE_Y, -0.1))                # look B head scale pivot (= the EyeCam marker)
SHOULDER = Vector((0.20, 1.31 if FEMALE else 1.355, 0.0))   # female: relaxed, lower shoulders (user)
# The arms are modelled and bound in an A-pose (ARM_UP more than they hang), so the voxel union can't fuse sleeve and
# torso; the `rest` and `idle` clips lower them to the hanging pose the design shows.
ARM_UP = float(os.environ.get('HUMAN_ARM_UP', 33.0))   # character-system mock: 78 = T-pose bind
_UP = Matrix.Rotation(math.radians(ARM_UP), 3, 'Z')                  # Godot Z: lifts the right arm outward
_HANG = Vector((math.sin(math.radians(12)), -math.cos(math.radians(12)), 0.0))
ELBOW = SHOULDER + _UP @ _HANG * 0.27
FORE = (_UP @ Vector((0.12, -1.0, -0.22))).normalized()
WRIST = ELBOW + FORE * 0.24
BACK = _UP @ Vector((1, 0, 0))                                         # back of the right hand at bind
HIP = Vector((0.10, 0.82, 0.0))
KNEE = Vector((0.118, 0.46, -0.02))                # a little forward: knees bend the right way for IK
ANKLE = Vector((0.135, 0.15, 0.0))                 # trouser cuff
ANKLE_J = Vector((0.135, 0.095, 0.0))              # ankle joint inside the shoe collar
LANDMARKS = dict(SHOULDER=SHOULDER, ELBOW=ELBOW, WRIST=WRIST, FORE=FORE, BACK=BACK, HIP=HIP, KNEE=KNEE,
                 ANKLE=ANKLE, ANKLE_J=ANKLE_J, EYE_Y=EYE_Y, ARM_UP=ARM_UP)


def mirror(v, s):
    return Vector((v.x * s, v.y, v.z))


# --- parts -------------------------------------------------------------------------------------------------

def head_skin():
    mb = meta('HeadSkin', 0.006)
    ell(mb, (0, 1.635, 0.0), (0.128, 0.145, 0.132))               # cranium (top 1.78)
    ell(mb, (0, 1.552 if FEMALE else 1.548, -0.028), (0.112, 0.074, 0.098) if FEMALE else (0.112, 0.082, 0.102))   # jaw
    if LOOK_B:                                                       # rounder cheeks, small button nose
        for s in (-1, 1):
            ell(mb, (s * 0.064, 1.56 if FEMALE else 1.562, -0.064), (0.064, 0.055, 0.06) if FEMALE else (0.062, 0.052, 0.06))
        ell(mb, (0, 1.582, -0.134), (0.016, 0.015, 0.017) if FEMALE else (0.021, 0.019, 0.021))
    else:
        for s in (-1, 1):
            ell(mb, (s * 0.062, 1.565, -0.062), (0.058, 0.048, 0.058))   # round cheeks
        ell(mb, (0, 1.586, -0.137), (0.029, 0.027, 0.027))            # bulb nose
    # Neck into the collar. Look B's bigger head reaches lower: a short neck stays under the hood when leaning.
    cap(mb, (0, 1.43 if LOOK_B else 1.36, 0.012), (0, 1.50, 0.0), 0.05 if LOOK_B else 0.054)
    ears = meta('Ears', 0.004)                                       # own family: a crease, not a cheek lump
    for s in (-1, 1):
        ell(ears, (s * 0.138, 1.604, 0.012), (0.018, 0.043, 0.031))
        ell(ears, (s * 0.154, 1.602, 0.006), (0.007, 0.026, 0.017), neg=True)    # bowl
    return solid('HeadSkin', [mb, ears], 0.0038, 4000, lib.mat('Skin', SKIN, 0.55))


def hairline(phi):
    """Hairline height by azimuth (0 = front, pi = back)."""
    pts = [(0.0, 1.708), (0.6, 1.700), (1.1, 1.664), (1.45, 1.672), (1.8, 1.600), (2.4, 1.555), (math.pi, 1.540)]
    a = abs(phi)
    for (a0, y0), (a1, y1) in zip(pts, pts[1:]):
        if a <= a1:
            t = (a - a0) / (a1 - a0)
            t = t * t * (3 - 2 * t)
            return y0 + (y1 - y0) * t
    return pts[-1][1]


def hair(head):
    """Chunky hair: balls on the scalp above the hairline (scalloped edge = clumps), swept fringe, cowlick."""
    if SPEC['hair'] == 'bun':
        return hair_bun(head)
    if LOOK_B:
        return hair_chunky(head)
    surf = Surface(head)
    mb = meta('Hair', 0.0055)
    k = 1.4 if LOOK_B else 1.0                                       # look B: bigger sculpted chunks
    placed = []
    for v, n in zip(surf.verts, surf.normals):
        phi = math.atan2(v.x, -v.z)
        if v.y < hairline(phi) or v.y < 1.45:
            continue
        if abs(v.x) > 0.105 and 1.55 < v.y < 1.66 and -0.03 < v.z < 0.045:           # leave the ears out
            continue
        if any((v - p).length < 0.017 * k for p in placed):
            continue
        placed.append(v)
        ball(mb, v + n * (0.009 if LOOK_B else 0.0045), 0.019 * k)
    # Fringe: clumps from the crown sweeping forward and to the Human's right, tips above the brows.
    for pts, r0, r1 in (
            ([(-0.07, 1.775, -0.04), (-0.01, 1.752, -0.105), (0.045, 1.725, -0.128), (0.085, 1.706, -0.112)], 0.030, 0.015),
            ([(-0.10, 1.755, -0.015), (-0.075, 1.736, -0.095), (-0.035, 1.712, -0.132)], 0.028, 0.014),
            ([(0.02, 1.785, -0.03), (0.075, 1.75, -0.09), (0.112, 1.712, -0.075)], 0.028, 0.014),
            ([(-0.11, 1.735, -0.02), (-0.122, 1.70, -0.075)], 0.022, 0.012)):
        if LOOK_B:                                                   # tips lifted off the brows
            pts = [(x, y + 0.012 * i / (len(pts) - 1), z) for i, (x, y, z) in enumerate(pts)]
        chain(mb, pts, r0 * k, r1 * k)
    # Bedhead cowlick at the back of the crown.
    for tip in ((-0.03, 1.835, 0.09), (0.0, 1.85, 0.075), (0.032, 1.83, 0.095)):     # soft three-tuft cowlick
        chain(mb, [(0.0, 1.77, 0.06), tip], 0.022 * k, 0.011 * k)
    return solid('Hair', [mb], 0.0045, 4500, lib.mat('Hair', HAIR, 0.72))


CRANIUM = Vector((0, 1.64, 0.0))


def scalp(surf, d, lift):
    """Point on the head along direction d from the cranium centre, lifted off the skin along the normal."""
    d = Vector(d).normalized()
    loc, n = surf.hit(CRANIUM + d * 0.4, -d)
    return loc + n * lift


def scalp_dir(phi, y):
    """Direction from the cranium centre toward azimuth phi (0 = front, + = the Human's right) at height y."""
    el = math.asin(max(-0.95, min(0.95, (y - CRANIUM.y) / 0.15)))
    return Vector((math.cos(el) * math.sin(phi), math.sin(el), -math.cos(el) * math.cos(phi)))


def strand(mb, surf, d0, d1, r0, r1, lift0, lift1, n=10, rise=0.0):
    """A sculpted clump: tapered balls along the scalp from direction d0 to d1."""
    d0, d1 = Vector(d0).normalized(), Vector(d1).normalized()
    pts = []
    for i in range(n + 1):
        t = i / n
        p = scalp(surf, d0.slerp(d1, t), lift0 + (lift1 - lift0) * t)
        pts.append(p + Vector((0, rise * t * t, 0)))
    chain(mb, pts, r0, r1, step=0.005)


def scalp_cap(surf, mb, drop=0.0, spacing=0.016, r=0.016, lift=0.004, front=0.0):
    """Smooth under-layer: no skin shows between the clumps. drop lowers the sides/back, front raises the front."""
    placed = []
    for v, n in zip(surf.verts, surf.normals):
        phi = math.atan2(v.x, -v.z)
        edge = hairline(phi) - (drop if abs(phi) > 1.2 else 0.0) + front * _ss(1 - abs(phi) / 0.9)
        if v.y < edge or v.y < 1.45:
            continue
        if abs(v.x) > 0.105 and 1.55 < v.y < 1.66 and -0.03 < v.z < 0.045:
            continue
        if any((v - p).length < spacing for p in placed):
            continue
        placed.append(v)
        ball(mb, v + n * lift, r)


def lock(mb, surf, pts, r0, r1):
    """One clay lock: tapered balls through (azimuth, height, lift) control points projected onto the scalp."""
    cps = [scalp(surf, scalp_dir(phi, y), lift) for phi, y, lift in pts]
    path = []
    for a, b in zip(cps, cps[1:]):                                  # densify, re-projecting so it hugs the head
        for i in range(6):
            path.append(a.lerp(b, i / 6))
    path.append(cps[-1])
    chain(mb, path, r0, r1, step=0.004)


def scalp_shell(head, edge, lift=0.003, thick=0.01):
    """Smooth hair cap: the head surface above edge(phi) (a clean hairline), lifted and solidified."""
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.transform(head.matrix_world)
    gone = []
    for v in bm.verts:
        g = G(v.co)
        if g.y < edge(math.atan2(g.x, -g.z)) or g.y < 1.45 or (abs(g.x) > 0.105 and 1.55 < g.y < 1.66 and -0.03 < g.z < 0.045):
            gone.append(v)
    bmesh.ops.delete(bm, geom=gone, context='VERTS')
    for _ in range(4):                                               # drop one-face-wide slivers left by the cut
        thin = [f for f in bm.faces if all(v.is_boundary for v in f.verts)]
        if not thin:
            break
        bmesh.ops.delete(bm, geom=thin, context='FACES')
    bm.faces.index_update()
    islands, seen = [], set()                                         # keep the biggest piece only
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, isl = [f], []
        seen.add(f.index)
        while stack:
            x = stack.pop()
            isl.append(x)
            for e in x.edges:
                for y in e.link_faces:
                    if y.index not in seen:
                        seen.add(y.index)
                        stack.append(y)
        islands.append(isl)
    for isl in sorted(islands, key=len)[:-1]:
        bmesh.ops.delete(bm, geom=isl, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    for _ in range(8):                                               # smooth the hairline (cut triangles are jagged)
        edge_v = [v for v in bm.verts if v.is_boundary]
        new = {}
        for v in edge_v:
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2:
                new[v] = v.co * 0.5 + (nb[0].co + nb[1].co) * 0.25
        for v, c in new.items():
            v.co = c
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * lift
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thick)
    me = bpy.data.meshes.new('HairShell')
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new('HairShell', me)
    bpy.context.scene.collection.objects.link(o)
    return o


def union_shell(hair_obj, shell, voxel, tris):
    """Voxel-union the shell into the sculpted hair, decimate, smooth (keeps the Hair object and material)."""
    shell.data.materials.append(hair_obj.data.materials[0])        # one slot: the join keeps a single material
    for x in bpy.data.objects:
        x.select_set(x in (hair_obj, shell))
    bpy.context.view_layer.objects.active = hair_obj
    bpy.ops.object.join()
    hair_obj.data.remesh_voxel_size = voxel
    bpy.ops.object.voxel_remesh()
    m = hair_obj.modifiers.new('Dec', 'DECIMATE')
    m.ratio = min(1.0, tris / max(1, 2 * len(hair_obj.data.polygons)))
    bpy.ops.object.modifier_apply(modifier='Dec')
    bm = bmesh.new()
    bm.from_mesh(hair_obj.data)
    for _ in range(3):
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.4, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(hair_obj.data)
    bm.free()
    for f in hair_obj.data.polygons:
        f.use_smooth = True
        f.material_index = 0
    while len(hair_obj.data.materials) > 1:
        hair_obj.data.materials.pop()
    return hair_obj


def hair_chunky(head):
    """Look B (art director, crops/hair_locks_male.png): a few big separate clay locks with deep gaps (each lock its
    own metaball family, so the union keeps a crease), fringe and crown tips lifting off the scalp, over a thin cap."""
    surf = Surface(head)
    shell = scalp_shell(head, lambda phi: hairline(phi) + 0.02 * (abs(phi) > 1.2) + 0.055 * _ss(1 - abs(phi) / 0.9))
    fams = []
    locks = [  # (azimuth, height, lift) ..., r0, r1: volume on top, fringe sweeps right and curls up off the forehead
        ([(-0.3, 1.83, 0.03), (-0.05, 1.80, 0.032), (0.18, 1.778, 0.04)], 0.046, 0.016),
        ([(0.35, 1.825, 0.03), (0.6, 1.795, 0.032), (0.82, 1.762, 0.04)], 0.042, 0.015),
        ([(-0.8, 1.82, 0.03), (-0.62, 1.80, 0.032), (-0.45, 1.79, 0.04)], 0.04, 0.015),
        ([(-1.15, 1.795, 0.024), (-1.4, 1.755, 0.026), (-1.52, 1.715, 0.03)], 0.04, 0.02),
        ([(1.2, 1.795, 0.024), (1.42, 1.755, 0.026), (1.52, 1.718, 0.03)], 0.04, 0.02),
        ([(-2.2, 1.81, 0.026), (-2.45, 1.74, 0.026), (-2.55, 1.665, 0.03)], 0.042, 0.022),
        ([(2.2, 1.81, 0.026), (2.45, 1.74, 0.026), (2.55, 1.665, 0.03)], 0.042, 0.022),
        ([(3.14, 1.83, 0.026), (3.14, 1.74, 0.026), (3.14, 1.645, 0.028)], 0.042, 0.022),
    ]
    for i, (pts, r0, r1) in enumerate(locks):
        mb = meta('Lock%d' % i, 0.0055)
        lock(mb, surf, pts, r0, r1)
        fams.append(mb)
    mb = meta('Crown', 0.0055)                                       # crown tufts lifting off
    for tip in ((-0.035, 1.87, 0.085), (0.03, 1.885, 0.07)):
        chain(mb, [(0.0, 1.79, 0.05), tip], 0.03, 0.014)
    fams.append(mb)
    return union_shell(solid('Hair', fams, 0.0035, 7000, lib.mat('Hair', HAIR, 0.72)), shell, 0.0035, 7500)


def hair_bun(head):
    """Female base (art director, crops/female_head_body.png): wavy locks pulled up into a messy curly bun, a soft
    side-swept fringe and loose face-framing curls; each lock and curl its own family (creases between them)."""
    surf = Surface(head)
    shell = scalp_shell(head, lambda phi: hairline(phi) - 0.03 * (abs(phi) > 1.2) + 0.012 * _ss(1 - abs(phi) / 0.9))
    fams = []
    for i in range(9):                                               # wavy locks from the hairline up to the bun
        phi = 0.95 + i * (2 * math.pi - 1.9) / 8
        phi = phi if phi <= math.pi else phi - 2 * math.pi
        y0 = hairline(phi) - (0.03 if abs(phi) > 1.2 else 0.0)
        pts = [(phi + 0.08 * math.sin(k * 1.9), y0 + (1.86 - y0) * k / 4, 0.012 + 0.006 * (k % 2)) for k in range(5)]
        mb = meta('Lock%d' % i, 0.0055)
        lock(mb, surf, pts, 0.024, 0.02)
        fams.append(mb)
    bun = Vector((0, 1.845, 0.05))
    for i in range(7):                                               # messy bun: curl loops round a core
        mb = meta('Curl%d' % i, 0.0045)
        a0 = i * 2 * math.pi / 7
        c = bun + Vector((0.03 * math.cos(a0), 0.012 * math.sin(3 * a0) + (0.02 if i % 3 == 0 else 0), 0.03 * math.sin(a0)))
        n = Vector((math.cos(a0), 0.6, math.sin(a0))).normalized()
        u = n.cross(Vector((0, 1, 0)) if abs(n.y) < 0.9 else Vector((1, 0, 0))).normalized()
        v = n.cross(u)
        pts = [c + (u * math.cos(t) + v * math.sin(t)) * 0.027 + n * 0.006 * t / 6
               for t in [k * 2 * math.pi * 1.1 / 16 for k in range(17)]]
        chain(mb, pts, 0.016, 0.012, step=0.004)
        fams.append(mb)
    core = meta('BunCore', 0.0055)
    ball(core, bun, 0.048)
    ball(core, bun + Vector((0, -0.035, 0.0)), 0.045)                 # seat it on the crown
    fams.append(core)
    for k, (x0, x1, y1, r) in enumerate(((0.05, -0.05, 1.724, 0.024), (0.04, -0.1, 1.71, 0.02))):
        mb = meta('Fringe%d' % k, 0.0055)
        lock(mb, surf, [(math.atan2(x0, 0.1), 1.8, 0.012), (math.asin(max(-1, min(1, (x0 + x1) / 0.26))), 1.76, 0.014),
                        (math.asin(max(-1, min(1, x1 / 0.13))), y1, 0.012)], r, r * 0.6)
        fams.append(mb)
    for s in (-1, 1):                                                # loose curls: temple, cheek, behind the ear
        for k, (x, z, y0, y1, rr) in enumerate(((0.12, -0.072, 1.70, 1.49, 0.02), (0.134, -0.025, 1.65, 1.47, 0.018))):
            mb = meta('Ringlet%d%d' % (s + 1, k), 0.0035)
            turns = 1.7 + 0.3 * k
            pts = [Vector((s * (x + rr * math.cos(t)), y0 + (y1 - y0) * t / (turns * 2 * math.pi), z + rr * math.sin(t)))
                   for t in [turns * 2 * math.pi * i / 30 for i in range(31)]]
            chain(mb, pts, 0.0125, 0.008, step=0.003)
            fams.append(mb)
    return union_shell(solid('Hair', fams, 0.003, 8000, lib.mat('Hair', HAIR, 0.72)), shell, 0.003, 8500)


def volumes():
    """Torso/limb volumes for the spec: the shipped Human at sex male, build 0."""
    b, f = BUILD, FEMALE
    v = dict(chest=(0.185, 0.17, 0.126), belly=(0.192, 0.15, 0.142), belly_z=-0.018, flare=(0.196, 0.07, 0.136),
             shoulder=0.066, limb=1.0, pelvis=(0.178, 0.125, 0.126), leg=1.0)
    if f:                                                         # narrower waist, wider hips, softer shoulders
        v.update(chest=(0.168, 0.165, 0.122), belly=(0.152, 0.15, 0.124), flare=(0.228, 0.078, 0.146), shoulder=0.058,
                 limb=1.0, pelvis=(0.216, 0.13, 0.142), leg=1.05)
    c, bl, fl, pe = v['chest'], v['belly'], v['flare'], v['pelvis']
    v.update(chest=(c[0] * (1 + 0.1 * b), c[1], c[2] * (1 + 0.14 * b)),
             belly=(bl[0] + 0.045 * b, bl[1] + 0.01 * max(b, 0), bl[2] + 0.055 * b), belly_z=v['belly_z'] - 0.02 * b,
             flare=(fl[0] + 0.035 * b, fl[1], fl[2] + 0.035 * b), shoulder=v['shoulder'] + 0.008 * b,
             limb=v['limb'] * (1 + 0.13 * b), pelvis=(pe[0] + 0.03 * b, pe[1], pe[2] + 0.03 * b),
             leg=v['leg'] * (1 + 0.13 * b))
    return v


TOP_VOL = volumes()


def top(cw):
    """Sweatshirt: torso + hood family, one family per sleeve (no webbing to the body), unioned."""
    body = meta('TopBody', 0.008)
    v = TOP_VOL
    ell(body, (0, 1.22, 0.0), v['chest'])                         # chest
    ell(body, (0, 1.035, v['belly_z']), v['belly'])               # soft belly
    ell(body, (0, 0.925, 0.0), v['flare'])                        # loose hem flare
    cap(body, (-0.15, 1.342, 0.006), (0.15, 1.342, 0.006), v['shoulder'])    # sloped shoulders
    ell(body, (0, 1.425, 0.085), (0.15, 0.07, 0.08))              # bunched hood behind the neck
    fams = [body]
    for s in (-1, 1):
        sl = meta('Sleeve%d' % s, 0.008)
        sh, el, wr = mirror(SHOULDER, s), mirror(ELBOW, s), mirror(WRIST, s)
        ball(sl, sh + Vector((-s * 0.008, -0.01, 0)), 0.064 * v['limb'])
        cap(sl, sh, el, 0.063 * v['limb'])
        cap(sl, el, wr - mirror(FORE, s) * 0.105, 0.058 * v['limb'])            # rounded end stops short of the cuff
        fams.append(sl)
    R.PARTS['top'] = {'body': R.meta_tree(body), 'L': R.meta_tree(fams[1]), 'R': R.meta_tree(fams[2])}
    return solid('Top', fams, 0.006, 5000, lib.mat('Top' + cw['top'][1:], cw['top'], 0.9))


PANTS_TRIS = 3500                                   # the character builds raise it (smoother thighs)


def pants(cw):
    pel = meta('Pelvis', 0.008)
    ell(pel, (0, 0.86, 0.004), TOP_VOL['pelvis'])
    fams = [pel]
    for s in (-1, 1):
        lg = meta('Leg%d' % s, 0.008)
        h, k, a = mirror(HIP, s), mirror(KNEE, s), mirror(ANKLE, s)
        cap(lg, h, k, 0.084 * TOP_VOL['leg'])
        cap(lg, k, a + Vector((0, 0.07, 0)), 0.076 * TOP_VOL['leg'])                # rounded end hides inside the cuff
        fams.append(lg)
    R.PARTS['pants'] = {'body': R.meta_tree(pel), 'L': R.meta_tree(fams[1]), 'R': R.meta_tree(fams[2])}
    return solid('Pants', fams, 0.006, PANTS_TRIS, lib.mat('Pants' + cw['pants'][1:], cw['pants'], 0.88))


def rib_texture(color):
    """Vertical ribs (cuffs, hem, collar) as a tileable albedo + normal (same idea as the brain's knit cuff)."""
    import numpy as np
    h, w = 32, 64
    x = np.mgrid[0:h, 0:w][1].astype(float)
    shape = 0.5 + 0.5 * np.cos((x % 8) / 8.0 * 2 * math.pi)
    rgb = np.array([lib.linear(c) for c in lib.srgb(color)]) ** (1 / 2.2)
    img = rgb[None, None, :] * (0.82 + 0.22 * shape[..., None])
    gx = (np.roll(shape, -1, 1) - np.roll(shape, 1, 1)) * 1.2
    nrm = np.stack([-gx, np.zeros_like(gx), np.ones_like(gx)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    name = 'Rib' + color[1:]
    return (lib.image_from_array(name, np.clip(img, 0, 1)),
            lib.image_from_array(name + 'N', nrm * 0.5 + 0.5, non_color=True))


def band(name, frame, rx, rz, height, bulge, material, parent, seg=32, rows=5, ribs=24, lift=None):
    """Ribbed ring (cuff, hem, collar): lathe around frame +Y, rounded profile, UVs for the rib texture."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    ring = []
    for j in range(rows + 1):
        t = j / rows
        y = (t - 0.5) * height
        s = 1.0 + bulge * math.sin(t * math.pi)
        row = []
        for k in range(seg):
            a = k / seg * 2 * math.pi
            dy = lift(a) if lift else 0.0
            row.append(bm.verts.new(frame.at((math.sin(a) * rx * s, y + dy, -math.cos(a) * rz * s))))
        ring.append(row)
    for j in range(rows):
        for k in range(seg):
            q = (ring[j][k], ring[j][(k + 1) % seg], ring[j + 1][(k + 1) % seg], ring[j + 1][k])
            f = bm.faces.new(q)
            for l, (jj, kk) in zip(f.loops, ((j, k), (j, k + 1), (j + 1, k + 1), (j + 1, k))):
                l[uv].uv = (kk / seg * ribs / 8 * 8 / 8, jj / rows)
    # caps: inner lip closes the ring so no see-through edge
    for j, sign in ((0, -1), (rows, 1)):
        c = bm.verts.new(frame.at((0, (j / rows - 0.5) * height + (lift(0) if lift else 0), 0)))
        for k in range(seg):
            bm.faces.new((ring[j][k], ring[j][(k + 1) % seg], c) if sign < 0 else (ring[j][(k + 1) % seg], ring[j][k], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return lib.from_bmesh(name, bm, material, parent, frame.o)


def frame_along(origin, axis):
    """Frame whose +Y is `axis`."""
    y = Vector(axis).normalized()
    ref = Vector((0, 0, -1)) if abs(y.z) < 0.9 else Vector((1, 0, 0))
    x = ref.cross(y).normalized()
    z = x.cross(y)
    f = Frame(origin)
    f.m = Matrix((x, y, z)).transposed()
    return f


def shoes(cw, parent):
    upper_m = lib.mat('Shoe' + cw['shoe'][1:], cw['shoe'], 0.62)
    sole_m = lib.mat('Sole' + cw['sole'][1:], cw['sole'], 0.8)
    lace_m = lib.mat('Lace' + cw['lace'][1:], cw['lace'], 0.85)
    out = []
    for s, side in ((-1, 'L'), (1, 'R')):
        x = ANKLE.x * s
        f = Frame((x, 0.0, -0.05), (-90, s * -6, 0))              # toes out a little
        sole = lib.slab('Sole' + side, lib.rrect(0.128, 0.305, 0.06, 6), 0.036, 0.012, sole_m, f, parent)
        mb = meta('Upper' + side, 0.0045)
        # frame: local y = toward the toe, z = up; semis are world (x, up, length)
        ell(mb, f.at((0, 0.07, 0.06)), (0.058, 0.044, 0.088))       # toe box
        ell(mb, f.at((0, -0.05, 0.072)), (0.057, 0.06, 0.07))       # heel
        ball(mb, f.at((0, -0.04, 0.118)), 0.05)                     # ankle collar
        up = adopt(solid('Upper' + side, [mb], 0.004, 1600, upper_m), parent, f.o)
        up.name = 'Upper' + side
        surf = Surface(up)
        for i, (yy, w) in enumerate(((-0.035, 0.034), (-0.06, 0.036), (-0.085, 0.034))):
            pts = on_curve(surf, [(-w, yy + 0.03), (0, yy + 0.027), (w, yy + 0.03)],
                           Frame(f.at((0, 0, 0.3)), (90, s * -6, 0)), 0.003)       # local z = down, y = heel
            lib.tube('Lace%s%d' % (side, i), pts, 0.0042, lace_m, parent, res=4, bevel_res=1)
        for k, rot in enumerate((-90, 90)):                         # side stripes, outer and inner
            fo = f.at((0, 0, 0))
            decal('Stripe%s%d' % (side, k), surf, [(x_, y_ + 0.062) for x_, y_ in lib.rrect(0.13, 0.016, 0.008, 3)],
                  Frame((fo.x, 0.0, fo.z), (0, rot, 0)), lace_m, parent, offset=0.0012, rings=2)
        out += [sole, up]
    return out


def hands(parent):
    """The brain's hand (relaxed pose) baked from hands/art, skin only, hanging at the wrists."""
    skin = lib.mat('Skin', SKIN, 0.55)
    nail = lib.mat('Nail', NAIL, 0.35)
    out = []
    for s, side in ((1, 'r'), (-1, 'l')):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(lib.ROOT, 'hands', 'art', 'hand_%s.glb' % side))
        new = [o for o in bpy.data.objects if o not in before]
        bpy.context.scene.frame_set(0)
        dg = bpy.context.evaluated_depsgraph_get()
        d = mirror(FORE, s)
        o_ = mirror(BACK, s)
        o_ = (o_ - d * o_.dot(d)).normalized()                          # back of the hand faces out
        M = Matrix((o_.cross(-d), o_, -d)).transposed()                 # columns: local x, y (back), z (sleeve)
        wr = mirror(WRIST, s)
        place = lambda v: wr + M @ (G(v) * HAND_SCALE)
        # Finger bones from the brain hand's relaxed pose (the mesh is baked in the same pose).
        arm = next(x for x in new if x.type == 'ARMATURE')
        aw = arm.matrix_world
        side_n = R.side_name(s)
        R.HAND_BONES[s] = []
        for pb in arm.pose.bones:
            hname = R.BRAIN_TO_HUMAN.get(pb.name)
            if hname is None or pb.name in ('forearm', 'wrist'):
                continue
            up = M @ G(aw.to_3x3() @ (pb.matrix.to_3x3() @ Vector((0, 0, 1))))
            R.HAND_BONES[s].append((hname, place(aw @ pb.head), place(aw @ pb.tail), up.normalized(), None))
        for src, m, nm in (('Hand', skin, 'Hand'), ('Nails', nail, 'Nails')):
            o = next(x for x in new if x.name.startswith(src))
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
            bm = bmesh.new()
            bm.from_mesh(me)
            dl = bm.verts.layers.deform.active
            gnames = [g.name for g in o.vertex_groups]
            ws = []
            for v in bm.verts:
                w = {}
                for gi, x in (v[dl].items() if dl else []):
                    hn = side_n + R.BRAIN_TO_HUMAN.get(gnames[gi], 'Hand')
                    w[hn] = w.get(hn, 0) + x
                ws.append(w or {side_n + 'Hand': 1.0})
                v.co = place(o.matrix_world @ v.co)
            if dl:                                                     # old group indices would alias the new groups
                bm.verts.layers.deform.remove(dl)
            h = lib.from_bmesh(nm + side.upper(), bm, m, parent, wr)
            for i, w in enumerate(ws):                                 # groups before decimation (it keeps them)
                tot = sum(w.values())
                for k, x in w.items():
                    g = h.vertex_groups.get(k) or h.vertex_groups.new(name=k)
                    g.add([i], x / tot, 'REPLACE')
            if src == 'Hand':                                         # 6k -> 3k: small at mirror/reveal range
                dec = h.modifiers.new('Dec', 'DECIMATE')
                dec.ratio = 0.5
                for x in bpy.data.objects:
                    x.select_set(x == h)
                bpy.context.view_layer.objects.active = h
                bpy.ops.object.modifier_apply(modifier='Dec')
            out.append(h)
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
    return out


# --- face ---------------------------------------------------------------------------------------------------

def ellipse(a, b, n=24, cx=0.0, cy=0.0):
    return [(cx + a * math.cos(2 * math.pi * i / n), cy + b * math.sin(2 * math.pi * i / n)) for i in range(n)]


def soft_blush():
    """Blush: white with a radial alpha fade (soft edge, ~0.7 at the centre), times the colour (the 'blush' paint
    slot; default #EE9488 as the base colour factor)."""
    import numpy as np
    m = bpy.data.materials.get('CK2_Blush')
    if m:
        return m
    n = 64
    yy, xx = np.mgrid[0:n, 0:n] / (n - 1) * 2 - 1
    r = np.sqrt(xx * xx + yy * yy)
    a = 0.7 * np.clip(1 - r, 0, 1) ** 1.6
    img = lib.image_from_array('BlushFade', np.dstack([np.ones_like(r)] * 3 + [a]))
    m = lib.mat('Blush', '#EE9488', 0.9, image=img)
    nt = m.node_tree
    bsdf = next(x for x in nt.nodes if x.type == 'BSDF_PRINCIPLED')
    tex = next(x for x in nt.nodes if x.type == 'TEX_IMAGE')
    mix = nt.nodes.new('ShaderNodeMix')                      # texture x colour: glTF exports the colour as the factor
    mix.data_type, mix.blend_type = 'RGBA', 'MULTIPLY'
    mix.inputs['Factor'].default_value = 1.0
    nt.links.new(tex.outputs['Color'], mix.inputs['A'])
    mix.inputs['B'].default_value = bsdf.inputs['Base Color'].default_value[:]
    nt.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    nt.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
    m.surface_render_method = 'BLENDED'
    return m


def face(head_node, skin_obj):
    surf = Surface(skin_obj)
    white = lib.mat('EyeWhite', '#F8F4EA', 0.3)
    pupil = lib.mat('Pupil', '#2E2624', 0.3)
    glint = lib.mat('Glint', '#FFFFFF', 0.2)
    skin = lib.mat('Skin', SKIN, 0.55)
    ink = lib.mat('Mouth', INK, 0.7)
    front = Frame((0, 0, 0))                                         # projection along +Z (from the front)
    for s, side in ((-1, 'L'), (1, 'R')):
        ex = 0.052 if LOOK_B else 0.05
        hit, _ = surf.front(s * ex, EYE_Y)
        e = Vector((s * ex, EYE_Y, hit.z + 0.011))
        eye = lib.empty('Eye' + side, e, head_node)
        semi = ((0.035, 0.039, 0.025) if FEMALE else (0.032, 0.04, 0.025)) if LOOK_B else (0.029, 0.037, 0.024)
        w = lib.sphere('White' + side, 1.0, white, Frame(e), eye, scale=semi, seg=24, rings=14)
        look = lib.empty('Look' + side, e, eye)                       # rotate for gaze
        wsurf = Surface(w)
        pr = (0.0195, 0.0235) if LOOK_B else (0.0145, 0.018)          # look B: big dark eyes, bright highlight
        p = decal('Pupil' + side, wsurf, ellipse(pr[0], pr[1], 20, -s * 0.003, -0.002), Frame((e.x, e.y, 0)),
                  pupil, look, offset=0.0009)
        gr = 0.0062 if LOOK_B else 0.0045
        go = (0.007, 0.009) if LOOK_B else (0.006, 0.008)
        g = decal('Glint' + side, wsurf, ellipse(gr, gr, 10, -s * 0.003 + go[0], go[1]), Frame((e.x, e.y, 0)),
                  glint, look, offset=0.0018)
        if LOOK_B:
            decal('Glint2' + side, wsurf, ellipse(0.0026, 0.0026, 8, -s * 0.003 - 0.006, -0.009),
                  Frame((e.x, e.y, 0)), glint, look, offset=0.0018)
        # Upper lid: closed half-ellipsoid shell around the eye; rotation about X opens (+) / closes (-).
        # LidHalf: the same lid baked half-closed (dazed), hidden.
        for lname, ang in (('Lid', 45), ('LidHalf', -8)):
            bm = lib.sphere_bm(1.0, Frame(), tuple(c * 1.13 for c in semi), seg=24, rings=14)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0),
                                   plane_no=(0, 1, 0), clear_inner=True)
            edge = [ed for ed in bm.edges if ed.is_boundary]
            bmesh.ops.contextual_create(bm, geom=edge)
            lib.transform_bm(bm, Frame(e))
            lid = lib.from_bmesh(lname + side, bm, skin, eye, e)
            godot_rot(lid, (ang, 0, 0))
            if lname == 'LidHalf':
                lid['hidden'] = True
        # Brow: chunky clump on the forehead.
        if LOOK_B:                                                  # thick, short, rounded brows (tapered clay)
            pts = on_curve(surf, [(s * 0.028, 1.683), (s * 0.052, 1.693), (s * 0.075, 1.686)], front, 0.008)
            if FEMALE:                                              # lighter: thinner, softer colour, a gentle arch
                pts = on_curve(surf, [(s * 0.03, 1.688), (s * 0.055, 1.699), (s * 0.08, 1.69)], front, 0.007)
            mb = meta('Brow' + side, 0.0025)
            chain(mb, pts, *((0.0072, 0.0052) if FEMALE else (0.0128, 0.0098)), step=0.003)
            adopt(solid('Brow' + side, [mb], 0.0012, 900, lib.mat('Brow', '#86583F' if FEMALE else BROW, 0.75)),
                  head_node, pts[1])
        else:
            pts = on_curve(surf, [(s * 0.022, 1.676), (s * 0.05, 1.688), (s * 0.08, 1.678)], front, 0.006)
            lib.tube('Brow' + side, pts, 0.0095, lib.mat('Brow', BROW, 0.75), head_node, res=6, bevel_res=2)
        if LOOK_B:                                                  # warm cheeks, always on, soft-edged
            bl = decal('Blush' + side, surf, ellipse(0.036, 0.022, 18, s * 0.086, 1.56), front, soft_blush(),
                       head_node, offset=0.0015)
            uv = bl.data.uv_layers.new(name='UVMap')                # planar: the alpha fade is radial
            for loop in bl.data.loops:
                q = G(bl.matrix_world @ bl.data.vertices[loop.vertex_index].co)
                uv.data[loop.index].uv = (0.5 + (q.x - s * 0.086) / 0.072, 0.5 + (q.y - 1.56) / 0.044)
        else:
            bl = decal('Blush' + side, surf, ellipse(0.026, 0.016, 18, s * 0.083, 1.567), front,
                       lib.mat('Blush', BLUSH, 0.7), head_node, offset=0.0015)
            bl['hidden'] = True
        if FEMALE:                                                  # upper lash line along the lid edge + a wing
            mb = meta('Lash' + side, 0.002)
            arc = []
            for i in range(9):
                a = math.radians(150 - 125 * i / 8) if s > 0 else math.radians(30 + 125 * i / 8)
                q = Vector((math.cos(a) * semi[0], math.sin(a) * semi[1] * 0.97, 0))
                arc.append(e + q + Vector((0, 0, -0.008)))                # on the white's rim, just in front
            chain(mb, arc, 0.0026, 0.0034, step=0.0015)
            c = arc[-1]
            for a, l in ((0.25, 0.012), (0.6, 0.009)):
                tip = c + Vector((s * l * math.cos(a), l * math.sin(a), 0.002))
                chain(mb, [c, tip], 0.003, 0.0016, step=0.0012)
            adopt(solid('Lash' + side, [mb], 0.0009, 700, lib.mat('Lash', '#3A2420', 0.75)), head_node, e)
    mouth = lib.empty('Mouth', (0, 1.522, -0.11), head_node)
    smile = on_curve(surf, [(-0.036, 1.531), (-0.018, 1.521), (0, 1.518), (0.018, 1.521), (0.036, 1.531)], front, 0.002)
    lib.tube('Smile', smile, 0.0042, ink, mouth, res=8, bevel_res=2)
    d_shape = [(0.038 * math.cos(a), 1.531 - 0.034 * math.sin(a)) for a in [math.pi * i / 16 for i in range(17)]]
    d_shape += [(x, 1.531 + 0.004 * (1 - (x / 0.038) ** 2)) for x in [-0.038 + 0.076 * i / 8 for i in range(1, 8)]]
    op = decal('Open', surf, d_shape, front, ink, mouth, offset=0.0016)
    op['hidden'] = True
    tg = decal('Tongue', surf, ellipse(0.02, 0.011, 18, 0.0, 1.508), front, lib.mat('Tongue', TONGUE, 0.6), mouth,
               offset=0.0024)
    tg['hidden'] = True
    tw = decal('Teeth', surf, [(x, y + 1.5265) for x, y in lib.rrect(0.054, 0.009, 0.0035, 3)], front,
               lib.mat('Teeth', '#F8F4EA', 0.4), mouth, offset=0.0022, rings=2)
    tw['hidden'] = True
    gr = decal('Grimace', surf, [(0.038 * math.cos(a), 1.524 + 0.015 * math.sin(a)) for a in
                                 [i * 2 * math.pi / 24 for i in range(24)]], front, lib.mat('Teeth', '#F8F4EA', 0.4),
               mouth, offset=0.0017)
    gr['hidden'] = True
    line = on_curve(surf, [(-0.036, 1.524), (0, 1.5235), (0.036, 1.524)], front, 0.0026)
    gl = lib.tube('GrimaceLine', line, 0.0019, ink, mouth, res=4, bevel_res=1)
    gl['hidden'] = True
    oo = decal('O', surf, ellipse(0.016, 0.021, 20, 0.0, 1.517), front, ink, mouth, offset=0.0016)   # alarm
    oo['hidden'] = True
    wob = on_curve(surf, [(-0.034 + 0.068 * i / 8, 1.522 + 0.0035 * math.sin(i * math.pi / 2) - 0.002 * (i in (0, 8)))
                          for i in range(9)], front, 0.0024)
    wb = lib.tube('Wobble', wob, 0.0034, ink, mouth, res=6, bevel_res=2)   # dazed
    wb['hidden'] = True
    flat = on_curve(surf, [(-0.024, 1.523), (0, 1.522), (0.024, 1.523)], front, 0.0024)
    fl = lib.tube('Flat', flat, 0.0038, ink, mouth, res=6, bevel_res=2)     # neutral, no smile
    fl['hidden'] = True


# Expressions (game contract, json "expressions"): transforms and visibility only, applied over the rest face.
# show/hide: parts to toggle (Smile hides when another mouth shows); brow: BrowL/R (raise m, tilt deg about Z,
# + = inner end up; a raise past ~2 mm tucks them under the fringe); pupil: Pupil/Glint X/Y scale; look: per-eye LookL/R gaze [[yaw, pitch], [yaw, pitch]] or null
# (game's gaze); lid: LidL/R X rotation (deg, rest 45, + = open, -100 = shut), one value or [L, R]; mouth: Open/Tongue scale.
EXPRESSIONS = {
    'rest': {'show': [], 'brow': [0.0, 0.0], 'pupil': 1.0, 'look': None},
    'alarm': {'show': ['O'], 'hide': ['LidL', 'LidR'], 'brow': [0.0, 18.0], 'pupil': 0.62, 'look': None},
    'dazed': {'show': ['LidHalfL', 'LidHalfR', 'Wobble'], 'hide': ['LidL', 'LidR'], 'brow': [0.002, 8.0],
              'pupil': 1.0, 'look': [[9.0, -4.0], [-9.0, 3.0]]},
    'neutral': {'show': ['Flat'], 'brow': [0.0, 0.0], 'pupil': 1.0, 'look': None},
    'happy': {'lid': 30.0, 'brow': [0.010, -8.0], 'look': [[0.0, 4.0]] * 2, 'pupil': 1.08, 'show': ['Open', 'Tongue']},
    'panic': {'lid': 75.0, 'brow': [0.009, 18.0], 'look': None, 'pupil': 0.74, 'show': ['Open'], 'mouth': 1.35},
    'sleepy': {'lid': -22.0, 'brow': [-0.006, -4.0], 'look': [[0.0, -6.0]] * 2, 'pupil': 1.0, 'show': []},
    'embarrassed': {'lid': 20.0, 'brow': [0.008, 20.0], 'look': [[-16.0, -8.0]] * 2, 'pupil': 1.0,
                    'show': ['Grimace', 'GrimaceLine', 'BlushL', 'BlushR']},
    'wink': {'show': ['LidR'], 'lid': [45.0, -100.0], 'brow': [0.0, -6.0], 'pupil': 1.0, 'look': None},   # -100 = shut
    'surprised': {'show': ['O'], 'brow': [0.002, 6.0], 'pupil': 0.85, 'look': None},
}


# --- assembly -------------------------------------------------------------------------------------------------

def head_parts(root):
    """Head skin, hair and face under a 'Face' empty at the neck (look B: scaled about the eye)."""
    head = lib.empty('Face', NECK, root)          # head parts (not 'Head': that is the bone)
    skin = adopt(head_skin(), head, NECK)
    adopt(hair(skin), head, NECK)
    face(head, skin)
    k = SPEC['head']
    if k != 1.0:                                  # bigger head, scaled about the eye so the eye camera stays put
        new = HEAD_PIVOT + (NECK - HEAD_PIVOT) * k
        head.matrix_world = Matrix.Translation(B(new)) @ Matrix.Scale(k, 4)
        bpy.context.view_layer.update()
    return head


def outfit(cw, cw_id, body):
    """Outfit 1: hoodie (Top + rib bands, strings, pocket), joggers (Pants + cuffs), sneakers."""
    adopt(top(cw), body, (0, 1.1, 0))
    adopt(pants(cw), body, (0, 0.5, 0))
    rib_img = rib_texture(cw['rib'])
    rib = lib.mat('Rib' + cw['rib'][1:], cw['rib'], 0.9, image=rib_img[0], normal=rib_img[1])
    fl = TOP_VOL['flare']
    band('Hem', Frame((0, 0.875, 0.0)), fl[0] - 0.008, fl[2] - 0.004, 0.05, 0.04, rib, body)
    top_obj = bpy.data.objects['Top']
    tsurf = Surface(top_obj)

    def collar_lift(a, r=0.082):                                  # sit the collar on the shoulder line
        loc, _ = tsurf.hit((math.sin(a) * r, 1.7, -math.cos(a) * r * 0.95 - 0.004), (0, -1, 0))
        return loc.y - 1.40
    band('Collar', Frame((0, 1.40, -0.004)), 0.076, 0.072, 0.03, 0.16, rib, body, lift=collar_lift)
    for s, side in ((-1, 'L'), (1, 'R')):
        wr = mirror(WRIST, s)
        d = mirror(FORE, s)
        lr = 0.046 * TOP_VOL['limb']
        band('Cuff' + side, frame_along(wr - d * 0.042, d), lr, lr, 0.05, 0.1, rib, body)
        pr = 0.083 * TOP_VOL['leg']
        band('PantCuff' + side, Frame(mirror(ANKLE, s) + Vector((0, -0.002, 0))), pr, pr, 0.05, 0.05,
             lib.mat('PantCuff' + cw['pants'][1:], cw['pants'], 0.88), body)
    lace_m = lib.mat('Lace' + cw['lace'][1:], cw['lace'], 0.85)
    for s in (-1, 1):
        pts = on_curve(tsurf, [(s * 0.034, 1.37), (s * 0.038, 1.30), (s * 0.04, 1.24)], Frame(), 0.006)
        lib.tube('String%s' % ('L' if s < 0 else 'R'), pts, 0.0045, lace_m, body, res=6, bevel_res=1)
        tip = pts[-1]
        lib.tube('Aglet%s' % ('L' if s < 0 else 'R'), [tip, tip + Vector((0, -0.022, -0.002))], 0.0058,
                 lib.mat('Aglet', '#D9A04C' if cw_id != 'B' else '#F8F4EA', 0.5), body, res=2, bevel_res=1)
    pocket = [(-0.11, 1.075), (0.11, 1.075), (0.15, 0.94), (-0.15, 0.94)]
    pocket = [p for a, b in zip(pocket, pocket[1:] + pocket[:1]) for p in
              [(a[0] + (b[0] - a[0]) * t / 6, a[1] + (b[1] - a[1]) * t / 6) for t in range(6)]]
    decal('Pocket', tsurf, pocket, Frame(), lib.mat('Top' + cw['top'][1:], cw['top'], 0.9), body, offset=0.005,
          rings=5, depth=0.006)
    shoes(cw, body)


def matte():
    """Look B: matte clay, no sheen except the eyes."""
    for m in bpy.data.materials:
        if m.node_tree and not any(x in m.name for x in ('Eye', 'Pupil', 'Glint', 'Teeth', 'Tongue')):
            for n in m.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    n.inputs['Roughness'].default_value = max(n.inputs['Roughness'].default_value, 0.92)


def build(cw_id):
    cw = COLOURWAYS[cw_id]
    lib.reset()
    root = lib.empty('Human', (0, 0, 0))
    body = lib.empty('Body', (0, 0, 0), root)
    head = head_parts(root)
    outfit(cw, cw_id, body)
    hands(body)
    if LOOK_B:
        matte()
    rig_up(root, head)
    lib.count_tris()
    return root


SKIN_KIND = [('Top', 'top', 4), ('Pants', 'pants', 4), ('HeadSkin', 'neck', 3), ('Hem', 'torso', 1),
             ('Collar', 'torso', 1), ('Pocket', 'torso', 1), ('String', 'torso', 1), ('Aglet', 'torso', 0),
             ('Cuff', 'lowerarm', 0), ('PantCuff', 'lowerleg', 0), ('Sole', 'foot', 0), ('Upper', 'foot', 0),
             ('Lace', 'foot', 0), ('Stripe', 'foot', 0)]


def rig_up(root, head):
    """Humanoid skeleton, weights, head parts on the Head bone, clips (contract: interfaces.md "Human rig").
    Weights come from the canonical (shipped male) shape; the spec warp then moves vertices and bones together."""
    table = rig_table()
    rig = R.armature(table, root)
    for o in [x for x in bpy.data.objects if x.type == 'MESH']:
        if o.name.startswith(('Hand', 'Nails')):
            if o.name.startswith('Hand'):
                R.soften_knuckles(o, -1 if o.name.endswith('L') else 1)
            wr = mirror(WRIST, -1 if o.name.endswith('L') else 1)
            if not IDENT:
                o.matrix_world = Matrix.Translation(B(warp(wr) - wr)) @ o.matrix_world   # rigid with the wrist
            R.skin(o, [], rig)                                        # vertex groups already set in hands()
            continue
        kind = next(((k, n) for pre, k, n in SKIN_KIND if o.name.startswith(pre)), None)
        if kind is None:                                              # hair and face parts ride the Head bone
            continue
        ws = R.weights_for(o, kind[0], LANDMARKS)
        ws = R.smooth(o, ws, kind[1]) if kind[1] else ws
        mw = o.matrix_world.copy()
        canon = [G(mw @ v.co) for v in o.data.vertices]
        if SPEC['chest'] and kind[0] in ('top', 'torso'):
            ws = [chest_weights(c, w) for c, w in zip(canon, ws)]
        inv = mw.inverted()
        for v, c in zip(o.data.vertices, canon if not IDENT else ()):
            v.co = inv @ B(warp(c))
        R.skin(o, ws, rig)
        if SPEC['chest'] and kind[0] in ('top', 'torso') and any(bust(c)[0] > 0 for c in canon):
            o.shape_key_add(name='Basis')
            sk = o.shape_key_add(name='Chest_Size')                   # 0 flat .. 1 full (contract: interfaces.md Characters)
            for i, c in enumerate(canon):
                sk.data[i].co = inv @ B(warp(c + bust(c)[1]))
    if not IDENT:
        head.matrix_world = Matrix.Translation(B(warp(NECK) - NECK)) @ head.matrix_world   # hair and face: rigid
        bpy.context.view_layer.update()
    R.attach(head, rig, 'Head')
    rig['clips'] = R.clips(rig, ARM_UP, LANDMARKS, full=SPEC['clips'] == 'all', mock=SPEC['mock'])
    body = bpy.data.objects.get('Body')
    if body and not body.children:
        bpy.data.objects.remove(body, do_unlink=True)
    return rig


def spec_markers():
    if IDENT:
        return R.markers(LANDMARKS)
    out = []
    for m in R.markers(LANDMARKS):
        p = Vector(m['pos'])
        if m['bone'] == 'Head':
            p = head_xf(p)
        elif m['name'].startswith('Grip'):
            wr = mirror(WRIST, -1 if m['name'].endswith('L') else 1)
            p = p + warp(wr) - wr
        else:
            p = warp(p)
        out.append(dict(m, pos=list(p)))
    return out


def spec_ragdoll():
    """Canonical ragdoll through the warp (vertical bodies shorten with sy; the head scales with the head)."""
    if IDENT:
        return R.ragdoll(R.bone_table(LANDMARKS))
    out = []
    for b in R.ragdoll(R.bone_table(LANDMARKS)):
        b = dict(b, joint=dict(b['joint']))
        if b['bone'] == 'Head':
            b['centre'] = list(head_xf(b['centre']))
            b['radius'] = b['radius'] * SPEC['head']
            b['height'] = b['height'] * SPEC['head']
        else:
            b['centre'] = list(warp(b['centre']))
            if abs(b['axis'][1]) > 0.7:
                b['height'] = b['height'] * SPEC['sy']
        b['joint']['pos'] = list(warp(b['joint']['pos']))
        out.append(b)
    return out


# --- spec warp and chest (character-system mock) --------------------------------------------------------------

def _ss(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def warp(p):
    """Canonical (shipped male) body -> the spec: height scale below the neck (head carried rigidly), narrower
    shoulders (arms shift in, the upper torso narrows). Identity for the shipped Human."""
    if IDENT:
        return p
    p = Vector(p)
    sy, nar = SPEC['sy'], SPEC['narrow']
    if SPEC['keep_eye']:                          # the head stays put (eye camera); the neck takes up the difference
        y = p.y * (sy + (1 - sy) * _ss((p.y - 1.30) / 0.14))
    else:
        y = p.y * sy if p.y <= NECK.y else p.y + NECK.y * (sy - 1)
    x = p.x
    if nar:
        t = _ss((p.y - 1.12) / 0.16)
        ax = abs(x)
        ax = ax - nar * t if ax > 0.2 else ax * (1 - nar * t / 0.2)
        x = math.copysign(ax, x)
    return Vector((x, y, p.z))


def head_xf(p):
    """Where a canonical head point ends up: scaled about the eye (look B), then shifted with the neck."""
    if IDENT:
        return p
    p = Vector(p)
    return HEAD_PIVOT + (p - HEAD_PIVOT) * SPEC['head'] + (warp(NECK) - NECK)


BUST = Vector((0.088, 1.235, -0.1))               # high, about armpit level (art director 2026-10-16)


BUST_A, BUST_H = 0.095, 0.09                     # footprint radius, height at size 1


def _cap(r):
    """Spherical cap of footprint BUST_A and height BUST_H at distance r (a ball, not a cone), soft at the rim."""
    rb = (BUST_A ** 2 + BUST_H ** 2) / (2 * BUST_H)
    r = r * 0.92                                       # footprint a little wider than A: the rim fades out
    return max(0.0, math.sqrt(max(0.0, rb * rb - r * r)) - (rb - BUST_H)) * _ss((BUST_A + 0.02 - r) / 0.06)


def _smax(a, b, k=0.012):
    """Smooth max (no crease where two shapes meet)."""
    h = max(0.0, min(1.0, 0.5 + 0.5 * (a - b) / k))
    return b + (a - b) * h + k * h * (1 - h) * 0.5


def bust(p, bridge=True):
    """Chest key in canonical space: (influence 0..1, offset at size 1). A round cap per side, a little fuller below
    the centre. With `bridge` (clothes): the cloth stretches across between them at full height (one smooth shape,
    no centre line) and tucks back underneath with a short drape; the bare body keeps its round underside. Shapes join by a smooth max (no crease).
    User 2026-10-16: bigger, rounder, less peaky; front view must show two rounds, not a wide torso."""
    if p.z > -0.02:
        return 0.0, Vector()
    dy = p.y - BUST.y
    ry = dy * 0.8 if dy >= 0 else dy * 0.85                          # long gentle upper slope: no shelf on top
    h, lat = 0.0, 0.0
    for s in (-1, 1):
        dx = p.x - s * BUST.x
        c = _cap(math.hypot(dx, ry))
        if bridge and ry < 0:                                         # cloth follows the underside partway
            c = _smax(c, 0.5 * _cap(abs(dx)) * _ss(1 + ry / 0.10))
        h = _smax(h, c)
        lat += 0.25 * c * s * max(0.0, s * dx) / BUST_A              # spreads outward only: no fold in the middle
    if bridge and abs(p.x) < BUST.x:                                  # cloth stretches across: no dip, no line
        c = _cap(abs(ry))
        if ry < 0:
            c = _smax(c, 0.7 * _cap(0.0) * _ss(1 + ry / 0.13))
        h = _smax(h, c)
    k = _ss((-0.02 - p.z) / 0.06)
    h, lat = h * k, lat * k
    return h / BUST_H, Vector((lat, 0.0, -h))


def chest_weights(p, w):
    """Blend the bust region onto the Left/RightBreast spring bones."""
    out = dict(w)
    for s in (-1, 1):
        if p.z > -0.02:
            break
        g = _ss(1 - abs(abs(p.x) - BUST.x) / 0.09) * _ss(1 - abs(p.y - BUST.y) / 0.12) if p.x * s > 0 else 0.0
        g *= _ss((-0.02 - p.z) / 0.06) * 0.85
        if g > 0:
            out = {k: v * (1 - g) for k, v in out.items()}
            out[R.side_name(s) + 'Breast'] = g
    return out


def rig_table():
    """The bone table for this spec: canonical joints through the warp, head bones with the head, chest bones."""
    t = []
    for name, h, tl, up, par in R.bone_table(LANDMARKS):
        if IDENT:
            t.append((name, h, tl, up, par))
            continue
        f = head_xf if name == 'Head' else warp
        t.append((name, warp(h), f(tl), up, par))
    if SPEC['chest']:
        for s in (-1, 1):
            c = Vector((BUST.x * s, BUST.y, -0.03))
            t.append((R.side_name(s) + 'Breast', warp(c), warp(c + Vector((0, 0, -0.1))), Vector((0, 1, 0)), 'Chest'))
    return t


def export(root, path):
    hidden = [o.name for o in bpy.data.objects if o.get('hidden')]
    bpy.context.scene.render.fps, bpy.context.scene.render.fps_base = R.FPS, 1.0
    for o in bpy.data.objects:                       # without the root empty: the scene root is the Human
        o.select_set(o in root.children_recursive)
    lib.export_glb(filepath=path, export_format='GLB', export_yup=True, use_selection=True, export_cameras=False,
                   export_lights=False, export_extras=True, export_skins=True, export_animation_mode='NLA_TRACKS',
                   export_force_sampling=True)
    return hidden


def rig_json(path, hidden):
    import json
    table = rig_table()
    s = lambda v: [round(x, 5) for x in v]
    data = {'markers': spec_markers(), 'ragdoll': spec_ragdoll(), 'hidden': hidden, 'expressions': EXPRESSIONS, 'loops': R.LOOPS,
            'clips': R.CLIPS,
            'first_person': ['HandL', 'HandR', 'NailsL', 'NailsR', 'CuffL', 'CuffR'],   # meshes the player's own camera sees
            'look': {'neck': 'Neck', 'head': 'Head', 'share': [0.35, 0.65], 'yaw': 70, 'pitch': [-40, 30],
                     'eyes': ['LookL', 'LookR'], 'eye_yaw': 25, 'eye_pitch': 15},
            'render_layer': 2, 'ragdoll_layer': 2, 'ragdoll_mask': 1,
            'ik': {side: {'arm': [side + 'UpperArm', side + 'LowerArm', side + 'Hand'],
                          'leg': [side + 'UpperLeg', side + 'LowerLeg', side + 'Foot'],
                          'elbow_pole': s(warp(mirror(ELBOW, -1 if side == 'Left' else 1)) + Vector((0, 0, 0.35))),
                          'knee_pole': s(warp(mirror(KNEE, -1 if side == 'Left' else 1)) + Vector((0, 0, -0.45)))}
                   for side in ('Left', 'Right')},
            'bones': [b[0] for b in table]}
    if SPEC['mock']:                              # shared clips: Hips position tracks normalised by the hip height
        data['motion'] = {'hips_height': round(warp(Vector((0, 0.84, 0))).y, 5)}
    with open(path, 'w') as f:
        json.dump(data, f, indent=1)


def char_json(path, cw):
    """character.json (contract: interfaces.md "Characters"): colour slots for the shared materials, the chest."""
    paint = {'CK2_Skin': 'skin', 'CK2_Hair': 'hair', 'CK2_Brow': 'hair*0.82', 'CK2_Pupil': 'eyes', 'CK2_Blush': 'blush',
             'CK2_Top' + cw['top'][1:]: 'top', 'CK2_Pants' + cw['pants'][1:]: 'bottom',
             'CK2_PantCuff' + cw['pants'][1:]: 'bottom', 'CK2_Shoe' + cw['shoe'][1:]: 'shoes'}
    colors = {'skin': SKIN, 'hair': HAIR, 'eyes': '#2E2624', 'blush': '#EE9488' if LOOK_B else BLUSH,
              'top': cw['top'], 'bottom': cw['pants'], 'shoes': cw['shoe']}
    data = {'paint': paint, 'colors': colors}
    if SPEC['chest']:
        data['shapes'] = {'Chest_Size': 0.8}
        data['chest'] = {'chains': [['LeftBreast', 'LeftBreast'], ['RightBreast', 'RightBreast']], 'radius': 0.05}
    with open(path, 'w') as f:
        json.dump(data, f, indent=1)


def main():
    only = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out_art = os.environ.get('HUMAN_OUT') or os.path.join(lib.ROOT, 'human', 'art')     # mock builds go elsewhere
    name = os.environ.get('HUMAN_NAME', 'human')                                         # <name>.glb + <name>_rig.json
    out_prev = os.environ.get('HUMAN_OUT') or os.path.join(lib.ROOT, 'previews', 'human')
    os.makedirs(out_art, exist_ok=True)
    os.makedirs(out_prev, exist_ok=True)
    for cw_id in COLOURWAYS:
        if only and cw_id not in only:
            continue
        root = build(cw_id)
        export(root, os.path.join(out_prev, 'human_%s.glb' % cw_id))
        print('HUMAN %s tris=%d' % (cw_id, lib.count_tris()))
        if cw_id == 'A':
            hidden = export(root, os.path.join(out_art, name + '.glb'))
            rig_json(os.path.join(out_art, name + '_rig.json'), hidden)
            char_json(os.path.join(out_art, 'character.json'), COLOURWAYS['A'])
            os.makedirs(os.path.join(lib.ROOT, 'source', 'human'), exist_ok=True)
            if not os.environ.get('HUMAN_OUT'):
                bpy.ops.wm.save_as_mainfile(filepath=os.path.join(lib.ROOT, 'source', 'human', 'human.blend'))
    print('HUMAN_BUILT')


if __name__ == '__main__':
    main()
