"""Character system phase 2 (coordination/character_system_plan.md, contract: interfaces.md "Characters").
One base body per run, built with the Human build (scripts/human/build.py, spec in env HUMAN_SPEC) in T-pose and
exported as separate pieces on the same skeleton:
  characters/<base>/art/<base>.glb (+ <base>_rig.json, character.json): rig v1 body, skin mannequin split into
      Body_<Region> meshes, hands, clips, ragdoll, markers
  characters/parts/<id>/art/<id>.glb (+ part.json): head (skinned neck + rigid face parts), hair (rigid), hoodie,
      joggers, sneakers (skinned, hide the regions they cover)
Blend shapes on the body and every outfit layer: Build_Slim, Build_Heavy (shared displacement fields, so layers move
together) and, on the female base, Chest_Size. Run: scripts/characters/build_char.sh <male|female>.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

BASE = os.environ.get('CHAR_BASE', 'male')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'human'))
import build as hb  # noqa: E402  (reads HUMAN_SPEC / HUMAN_ARM_UP set by build_char.sh)
import lib  # noqa: E402
import rig as R  # noqa: E402
from lib import B, G  # noqa: E402
from sculpt import meta, ell, cap, ball, solid, adopt  # noqa: E402

FEMALE = hb.FEMALE
ROOT = lib.ROOT
PARTS = {  # part id -> (slot, mesh name prefixes, hides)
    'hoodie': ('top', ('Top', 'Hem', 'Collar', 'Cuff', 'Pocket', 'String', 'Aglet'),
               ['Body_Torso', 'Body_UpperArmL', 'Body_UpperArmR', 'Body_LowerArmL', 'Body_LowerArmR']),
    'joggers': ('bottom', ('Pants', 'PantCuff'),
                ['Body_Hips', 'Body_UpperLegL', 'Body_UpperLegR', 'Body_LowerLegL', 'Body_LowerLegR']),
    'tshirt': ('top', ('Shirt',), ['Body_Torso']),
    'sneakers': ('shoes', ('Sole', 'Upper', 'Lace', 'Stripe'), ['Body_FootL', 'Body_FootR']),
}
SFX = '_f' if FEMALE else '_m'
HEAD_ID, HAIR_ID = ('head_female', 'hair_bun') if FEMALE else ('head_bernard', 'hair_bernard')
LAYERS = ('Top', 'Hem', 'Collar', 'Cuff', 'Pocket', 'String', 'Aglet', 'Pants', 'PantCuff')   # get the build keys


# --- the skin mannequin ---------------------------------------------------------------------------------------

def mannequin(parent):
    """A plain clay body under the clothes (hidden where an outfit covers it): torso, arms, legs, socked feet."""
    v = hb.TOP_VOL
    m = lambda s, x: hb.mirror(x, s)
    torso = meta('BodyTorso', 0.008)
    c = v['chest']
    bl = v['belly']
    pe = v['pelvis']
    if not FEMALE:                                     # female torso and legs: lofts (below)
        ell(torso, (0, 1.22, 0.0), (c[0] - 0.03, c[1] - 0.01, c[2] - 0.03))
        ell(torso, (0, 1.04, v['belly_z'] * 0.5), (bl[0] - 0.035, bl[1] - 0.01, bl[2] - 0.035))
        ell(torso, (0, 0.88, 0.004), (pe[0] - 0.02, pe[1] - 0.01, pe[2] - 0.02))
    cap(torso, (-0.15, 1.33, 0.004), (0.15, 1.33, 0.004), v['shoulder'] - 0.018)
    cap(torso, (0, 1.30, 0.008), (0, 1.43, 0.008), 0.048)                       # neck stub (into the head's neck)
    fams = [torso]
    for s, side in ((-1, 'L'), (1, 'R')):
        arm = meta('BodyArm' + side, 0.007)
        sh, el, wr = m(s, hb.SHOULDER), m(s, hb.ELBOW), m(s, hb.WRIST)
        cap(arm, sh, el, 0.046 * v['limb'])
        cap(arm, el, wr - m(s, hb.FORE) * 0.02, 0.038 * v['limb'])
        h, k, a = m(s, hb.HIP), m(s, hb.KNEE), m(s, hb.ANKLE_J)
        if not FEMALE:
            leg = meta('BodyLeg' + side, 0.008)
            cap(leg, h, k, 0.072 * v['leg'])
            cap(leg, k, a + Vector((0, 0.03, 0)), 0.055 * v['leg'])
            fams.append(leg)
        foot = meta('BodyFoot' + side, 0.006)
        cap(foot, a + Vector((0, -0.01, 0.03)), Vector((a.x, 0.035, -0.15)), 0.04)
        fams += [arm, foot]
    skin = lib.mat('Skin', hb.SKIN, 0.55)
    o = solid('BodySkin', fams, 0.006, 9000, skin)
    if FEMALE:                                         # torso + legs lofted under the cloth (cloth minus CLOTH)
        legs = [(y, cx, hw, zc, zf, zb) for y, cx, hw, zc, zf, zb in BODY_LEG] + \
               [(0.075, 0.13, 0.046, 0.0, 0.046, 0.046)]           # down into the sock
        torso_r = [r for r in PANTS_PELVIS if r[0] < 0.97] + [r for r in SHIRT_TORSO if r[0] > 1.0] + \
                  [(1.36, 0, 0.09, 0.008, 0.06, 0.07)]
        objs = [o, tube('BodyLoftTorso', torso_r, shrink=CLOTH, crease=True)]
        objs += [tube('BodyLoftLeg%d' % s, legs, s, shrink=CLOTH) for s in (-1, 1)]
        o = union('BodySkin', objs, 0.006, skin, 2)
    return adopt(o, parent, (0, 0.9, 0))


SHIRT = '#E8765E', '#C95F4A'          # coral tee + its crew neck / sleeve bands (user: not yellow or purple)


def tshirt(parent, rib):
    """Fitted T-shirt over the mannequin: short sleeves, crew neck, hem just over the joggers' waist. Weights and
    blend shapes come from the body (so it follows the chest springs and the build keys)."""
    v = hb.TOP_VOL
    m = lambda s, x: hb.mirror(x, s)
    t = meta('ShirtBody', 0.007)
    c, bl, pe = v['chest'], v['belly'], v['pelvis']
    if not FEMALE:                                         # female: the torso is a loft (SHIRT_TORSO, below)
        ell(t, (0, 1.22, 0.0), (c[0] - 0.018, c[1] - 0.006, c[2] - 0.018))
        ell(t, (0, 1.04, v['belly_z'] * 0.5), (bl[0] - 0.022, bl[1] - 0.006, bl[2] - 0.022))
        wy = lambda r: r * math.sqrt(max(0.0, 1 - ((0.95 - 0.86) / pe[1]) ** 2))    # joggers' half-width at y 0.95
        ell(t, (0, 0.95, v['belly_z'] * 0.3), (wy(pe[0]) + 0.012, 0.055, wy(pe[2]) + 0.016))   # hem over the waist
    cap(t, (-0.15, 1.335, 0.004), (0.15, 1.335, 0.004), v['shoulder'] - 0.008)
    fams = [t]
    for s in (-1, 1):
        sl = meta('ShirtSleeve%d' % s, 0.007)
        sh, el = m(s, hb.SHOULDER), m(s, hb.ELBOW)
        end = sh + (el - sh) * 0.5
        ax = (el - sh).normalized()
        ball(sl, sh + Vector((-s * 0.006, -0.008, 0)), 0.056 * v['limb'])
        cap(sl, sh, end - ax * 0.03, 0.058 * v['limb'])          # its rounded end stays inside the band
        fams.append(sl)
        r = 0.058 * v['limb'] * 1.04                  # a hair over the sleeve end: caps its edge cleanly
        hb.band('ShirtSleeve' + ('L' if s < 0 else 'R'), hb.frame_along(end, el - sh), r, r, 0.026, 0.06, rib, parent)
    mat = lib.mat('Shirt' + SHIRT[0][1:], SHIRT[0], 0.9)
    o = solid('Shirt', fams, 0.008, 10 ** 6, mat)
    if FEMALE:
        o = union('Shirt', [o, tube('ShirtLoft', SHIRT_TORSO)], 0.008, mat, 2)
    shirt = adopt(o, parent, (0, 1.1, 0))
    hb.band('ShirtCollar', hb.Frame((0, 1.405, 0.0)), 0.066, 0.062, 0.022, 0.12, rib, parent)
    return shirt


def body_weights(p):
    """Mannequin weights along the limb axes (not by nearest blob: in the T-pose bind the shoulder cap reaches into
    the arm), soft seams at the shoulders, hips and ankles."""
    L = hb.LANDMARKS
    s = -1 if p.x < 0 else 1
    w = R.torso(p)
    sh, el = hb.mirror(L['SHOULDER'], s), hb.mirror(L['ELBOW'], s)
    t = (p - sh).dot((el - sh).normalized())
    if p.y > 1.05 and t > -0.13:
        w = R.mix(w, R.arm_w(p, s, L), hb._ss((t + 0.07) / 0.06))
    elif p.y < L['HIP'].y + 0.08:
        w = R.mix(w, R.leg_w(p, s, L), hb._ss((L['HIP'].y + 0.03 - p.y) / 0.08) * hb._ss(abs(p.x) / 0.02))
        f = hb._ss((L['ANKLE_J'].y + 0.02 - p.y) / 0.04)
        if f > 0:
            w = R.mix(w, {R.side_name(s) + 'Foot': 1.0}, f)
    return w


def pants_weights(p):
    """Female loft joggers: hips above, thighs below the hip line; the crotch seam splits between both legs."""
    L = hb.LANDMARKS
    w = R.torso(p)
    f = hb._ss((L['HIP'].y + 0.03 - p.y) / 0.08)
    if f <= 0:
        return w
    k = hb._ss(0.5 + p.x / 0.06)
    legs = R.mix(R.leg_w(p, -1, L), R.leg_w(p, 1, L), k)
    w = R.mix(w, legs, f)
    a = hb._ss((L['ANKLE_J'].y + 0.02 - p.y) / 0.04)
    return R.mix(w, {R.side_name(p.x) + 'Foot': 1.0}, a) if a > 0 else w


# --- hair spring chains (pilot: hair_bun's face-framing curls) ------------------------------------------------

CURLS = []                # (side, top, bottom) in canonical head space: the ringlets of build.hair_bun
if hb.SPEC['hair'] == 'bun':
    for _s in (-1, 1):
        for _x, _z, _y0, _y1 in ((0.12, -0.072, 1.70, 1.49), (0.134, -0.025, 1.65, 1.47)):
            CURLS.append((_s, Vector((_s * _x, _y0 - 0.02, _z)), Vector((_s * _x, _y1, _z))))


def curl_bones():
    """Two bones per curl under Head: HairCurl<L|R><n>_1 (upper), _2 (lower)."""
    out = []
    for i, (s, top, bot) in enumerate(CURLS):
        n = 'HairCurl%s%d' % ('L' if s < 0 else 'R', i % 2)
        mid = (top + bot) / 2
        out += [(n + '_1', hb.head_xf(top), hb.head_xf(mid), Vector((0, 0, -1)), 'Head'),
                (n + '_2', hb.head_xf(mid), hb.head_xf(bot), Vector((0, 0, -1)), n + '_1')]
    return out


if CURLS:
    _rig_table = hb.rig_table
    hb.rig_table = lambda: _rig_table() + curl_bones()        # rig, rig json 'bones' and the export all see them


def curl_weights(q):
    """Hair vertex (canonical head space) -> weights: along a curl it rides its chain, fading in below the root."""
    for i, (s, top, bot) in enumerate(CURLS):
        if q.x * s <= 0 or math.hypot(q.x - top.x, q.z - top.z) > 0.03 or not bot.y - 0.025 < q.y < top.y + 0.02:
            continue
        n = 'HairCurl%s%d' % ('L' if s < 0 else 'R', i % 2)
        t = (top.y - q.y) / (top.y - bot.y)
        g = hb._ss(t / 0.12)
        lo = hb._ss((t - 0.4) / 0.2)
        w = {n + '_1': g * (1 - lo), n + '_2': g * lo}
        if g < 1:
            w['Head'] = 1 - g
        return {k: v for k, v in w.items() if v > 1e-4}
    return {'Head': 1.0}


def springs():
    return [{'kind': 'hair', 'root': b[0], 'end': c[0], 'radius': 0.012, 'tip': 0.03, 'stiffness': 0.8, 'drag': 0.3,
             'gravity': 0.4} for b, c in zip(curl_bones()[0::2], curl_bones()[1::2])]


# --- female lofts (art direction 2026-10-16: references/characters/anatomy_notes_female_lower.md) ----------------
# Rings in FINAL (warped) space: (y, cx, half-width, zc, front depth, back depth); legs per side (cx > 0 = right).
# Waist (narrowest, y 1.015) half-width 0.125; hip max 1.3x below the hem; thigh >= 1.3x calf; flat waistband;
# the side profile (butt) is today's joggers', front flattened. Body = cloth minus its offset.

PANTS_PELVIS = [(0.585, 0, 0.02, 0.0, 0.012, 0.014), (0.60, 0, 0.07, 0.0, 0.04, 0.046),   # rounded bottom
                (0.625, 0, 0.115, 0.0, 0.062, 0.068), (0.66, 0, 0.152, 0.0, 0.072, 0.082),
                (0.70, 0, 0.168, 0.0, 0.086, 0.110), (0.74, 0, 0.180, 0.0, 0.098, 0.168), (0.79, 0, 0.186, 0.0, 0.106, 0.180),
                (0.84, 0, 0.184, 0.0, 0.114, 0.166), (0.89, 0, 0.166, 0.0, 0.118, 0.142),
                (0.94, 0, 0.146, 0.0, 0.119, 0.118), (0.965, 0, 0.138, 0.0, 0.117, 0.110),
                (0.985, 0, 0.135, 0.0, 0.116, 0.106)]
PANTS_LEG = [(0.80, 0.075, 0.088, 0.0, 0.09, 0.094), (0.66, 0.080, 0.086, -0.002, 0.090, 0.094),   # loose joggers
             (0.525, 0.088, 0.082, -0.004, 0.084, 0.080), (0.437, 0.094, 0.079, -0.008, 0.078, 0.070),
             (0.30, 0.104, 0.077, -0.006, 0.074, 0.074), (0.20, 0.114, 0.077, -0.002, 0.074, 0.074),
             (0.135, 0.12, 0.078, 0.0, 0.076, 0.076)]
BODY_LEG = [(0.80, 0.075, 0.085, 0.0, 0.088, 0.09), (0.66, 0.078, 0.082, -0.002, 0.082, 0.086),    # the leg itself
            (0.525, 0.085, 0.080, -0.006, 0.080, 0.077), (0.437, 0.092, 0.062, -0.015, 0.068, 0.056),
            (0.30, 0.106, 0.062, -0.012, 0.058, 0.070), (0.20, 0.118, 0.061, -0.006, 0.058, 0.062),
            (0.135, 0.125, 0.060, 0.0, 0.058, 0.058)]
SHIRT_TORSO = [(0.915, 0, 0.168, 0.0, 0.127, 0.140), (0.94, 0, 0.157, -0.002, 0.125, 0.127),   # hem over the hips
               (0.97, 0, 0.145, -0.002, 0.122, 0.116), (1.0, 0, 0.138, -0.002, 0.120, 0.110),
               (1.04, 0, 0.134, -0.002, 0.117, 0.106), (1.10, 0, 0.142, -0.002, 0.112, 0.106),
               (1.15, 0, 0.152, 0.0, 0.108, 0.106), (1.22, 0, 0.158, 0.0, 0.104, 0.104),
               (1.27, 0, 0.152, 0.0, 0.098, 0.104), (1.31, 0, 0.130, 0.0, 0.090, 0.114),
               (1.335, 0, 0.088, 0.010, 0.060, 0.104)]                        # up to the collar, over the nape
CLOTH = 0.008                                             # body = cloth minus this


def inv_warp(pf):
    """Final (warped) point -> canonical (hb.warp inverse: y by bisection, the shoulder narrowing analytically)."""
    lo, hi = -0.5, 2.5
    for _ in range(40):
        mid = (lo + hi) / 2
        if hb.warp(Vector((0, mid, 0))).y < pf.y:
            lo = mid
        else:
            hi = mid
    y = (lo + hi) / 2
    x, nar = pf.x, hb.SPEC['narrow']
    if nar:
        t = hb._ss((y - 1.12) / 0.16)
        ax = abs(x)
        ax = ax + nar * t if ax > 0.2 - nar * t else ax / (1 - nar * t / 0.2)
        x = math.copysign(ax, x)
    return Vector((x, y, pf.z))


def _catmull(rings, step=0.008):
    """Smooth rings along the control rings (Catmull-Rom per parameter), about `step` apart in y."""
    out = []
    pts = [rings[0]] + rings + [rings[-1]]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1:i + 3]
        n = max(2, int(abs(p2[0] - p1[0]) / step))
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t +
                                    (-a + 3 * b - 3 * c + d) * t ** 3) for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(rings[-1])
    return out


def tube(name, rings, side=1, shrink=0.0, crease=False, n=48, e=2.4):
    """Closed loft through superellipse rings (final space -> canonical), as a Blender-space object at the origin."""
    import bmesh
    bm = bmesh.new()
    rows = []
    for y, cx, hw, zc, zf, zb in _catmull(rings):
        hw, zf, zb = hw - shrink, zf - shrink, zb - shrink
        row = []
        for k in range(n):
            a = 2 * math.pi * k / n
            sa, ca = math.sin(a), math.cos(a)
            x = cx * side + hw * math.copysign(abs(sa) ** (2 / e), sa)
            d = zf if ca > 0 else zb
            if crease and ca < 0:                                     # two soft lobes: a shallow crease, lower butt
                d *= 1 - 0.035 * math.exp(-(x / 0.02) ** 2) * hb._ss((0.80 - y) / 0.05) * hb._ss((y - 0.66) / 0.03)
            z = zc - math.copysign(abs(ca) ** (2 / e), ca) * d
            row.append(bm.verts.new(B(inv_warp(Vector((x, y, z))))))
        rows.append(row)
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(n):
            bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]))
    for row in (rows[0], rows[-1]):
        bm.faces.new(row)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def tree_of(o):
    from mathutils.bvhtree import BVHTree
    me = o.data
    me.calc_loop_triangles()
    return BVHTree.FromPolygons([G(o.matrix_world @ v.co) for v in me.vertices], [t.vertices for t in me.loop_triangles])


def union(name, objs, voxel, material, smooth_iter=3):
    """Mesh objects (Blender space) -> one voxel-union mesh, smoothed (like sculpt.solid, no decimation)."""
    import bmesh
    for x in bpy.data.objects:
        x.select_set(x in objs)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.data.remesh_voxel_size = voxel
    bpy.ops.object.voxel_remesh()
    bm = bmesh.new()
    bm.from_mesh(o.data)
    for _ in range(smooth_iter):
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()
    for f in o.data.polygons:
        f.use_smooth = True
    o.data.materials.clear()
    o.data.materials.append(material)
    o.name = o.data.name = name
    return o


def female_lower(body):
    """Replace the joggers and their cuffs with the lofted ones (art direction widths)."""
    old = bpy.data.objects['Pants']
    mat = old.data.materials[0]
    bpy.data.objects.remove(old, do_unlink=True)
    parts = {'body': tube('PantsPelvis', PANTS_PELVIS, crease=True)}
    for s, side in ((-1, 'L'), (1, 'R')):
        parts[side] = tube('PantsLeg' + side, PANTS_LEG, s)
    R.PARTS['pants'] = {k: tree_of(o) for k, o in parts.items()}
    adopt(union('Pants', list(parts.values()), 0.005, mat), body, (0, 0.5, 0))
    for s, side in ((-1, 'L'), (1, 'R')):
        o = bpy.data.objects['PantCuff' + side]
        cmat = o.data.materials[0]
        bpy.data.objects.remove(o, do_unlink=True)
        c = inv_warp(Vector((s * 0.12, 0.135, 0.0)))                  # rolled cuff over the loose leg end
        hb.band('PantCuff' + side, hb.Frame(c + Vector((0, -0.002, 0))), 0.086, 0.086, 0.05, 0.05, cmat, body)


# --- build keys# --- build keys -----------------------------------------------------------------------------------------------

def _gauss(x):
    return math.exp(-x * x)


def build_offset(p, heavy):
    """Build key displacement (canonical space) at p: radial from the nearest body axis, a belly in front (heavy) or
    a flatter middle (slim). Soft-min blended between axes so shoulders and hips don't crease."""
    L, m = hb.LANDMARKS, hb.mirror
    segs = [('torso', Vector((0, 0.84, 0)), Vector((0, 1.42, 0)))]
    for s in (-1, 1):
        segs += [('uarm', m(L['SHOULDER'], s), m(L['ELBOW'], s)), ('larm', m(L['ELBOW'], s), m(L['WRIST'], s)),
                 ('uleg', m(L['HIP'], s), m(L['KNEE'], s)), ('lleg', m(L['KNEE'], s), m(L['ANKLE_J'], s))]
    acc, tot = Vector(), 0.0
    for kind, a, b in segs:
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
        c = a + ab * t
        r = p - c
        if kind == 'torso':
            r.y = 0.0
        d = r.length
        if d < 1e-6:
            continue
        n = r / d
        if kind == 'torso':
            if heavy:
                amt = 0.012 + 0.012 * _gauss((p.y - 1.22) / 0.08) + 0.024 * _gauss((p.y - 0.9) / 0.08)
                amt += 0.05 * _gauss((p.y - 1.03) / 0.1) * max(0.0, -n.z)              # belly in front
            else:
                amt = -0.008 - 0.014 * _gauss((p.y - 1.03) / 0.1) * max(0.0, -n.z)
        else:
            amt = {'uarm': (0.014, -0.006), 'larm': (0.009, -0.004), 'uleg': (0.022, -0.008),
                   'lleg': (0.012, -0.005)}[kind][0 if heavy else 1]
        w = math.exp(-d / 0.03)
        acc += n * amt * w
        tot += w
    return acc / tot if tot else Vector()


# --- weights by transfer ------------------------------------------------------------------------------------

def transfer(o, src_pts, src_ws, tree):
    """Weights for an attachment (rib band, pocket, strings) from the nearest points of its layer, so it deforms
    exactly with the surface it sits on (no rubber rings, no pocket poking out)."""
    out = []
    for v in o.data.vertices:
        p = G(o.matrix_world @ v.co)
        near = tree.find_n(p, 4)
        w, tw = {}, 0.0
        for _, i, d in near:
            k = 1.0 / max(d, 1e-4)
            tw += k
            for b, x in src_ws[i].items():
                w[b] = w.get(b, 0.0) + x * k
        out.append({b: x / tw for b, x in w.items()})
    return out


def top4(w):
    best = sorted(w.items(), key=lambda kv: -kv[1])[:4]
    t = sum(x for _, x in best) or 1.0
    return {b: x / t for b, x in best}


# --- regions --------------------------------------------------------------------------------------------------

def region_at(p):
    """Body region of a canonical point (bind pose), by the limb axes: arms past the shoulder joint, legs below the
    crotch, hips below the waist, the rest torso (neck included)."""
    L = hb.LANDMARKS
    side = 'L' if p.x < 0 else 'R'
    s = -1 if p.x < 0 else 1
    sh, el = hb.mirror(L['SHOULDER'], s), hb.mirror(L['ELBOW'], s)
    ax = (el - sh).normalized()
    if (p - sh).dot(ax) > -0.02 and p.y > 1.0:
        return ('UpperArm' if (p - sh).dot(ax) < (el - sh).length else 'LowerArm') + side
    if p.y < L['HIP'].y - 0.03 and abs(p.x) > 0.004:
        if p.y < L['ANKLE_J'].y + 0.02:
            return 'Foot' + side
        return ('LowerLeg' if p.y < L['KNEE'].y else 'UpperLeg') + side
    return 'Hips' if p.y < 0.98 else 'Torso'


def split_regions(o, canon):
    """BodySkin -> Body_<Region> objects by region_at of each face's vertices (groups and shape keys come along).
    The region is a face attribute (face order changes with every separate), selected in face mode."""
    import bmesh
    dom = [region_at(c) for c in canon]
    names = sorted(set(dom))
    att = o.data.attributes.new('region', 'INT', 'FACE')
    for f in o.data.polygons:
        regs = [dom[i] for i in f.vertices]
        att.data[f.index].value = names.index(max(set(regs), key=regs.count))
    out = []
    for k, reg in enumerate(names):
        bpy.ops.object.mode_set(mode='OBJECT')
        for x in bpy.data.objects:
            x.select_set(x == o)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        bm = bmesh.from_edit_mesh(o.data)
        lay = bm.faces.layers.int['region']
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        n = 0
        for f in bm.faces:
            f.select = f[lay] == k
            n += f.select
        bm.select_flush_mode()
        bmesh.update_edit_mesh(o.data)
        if not n:
            continue
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        new = [x for x in bpy.context.selected_objects if x != o][0]
        new.name = 'Body_' + reg
        new.data.name = new.name
        new.data.attributes.remove(new.data.attributes['region'])
        out.append(new)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects.remove(o, do_unlink=True)
    return out


def ensure_uvs(o):
    """A simple cylindrical UV map (Godot needs UVs for tangents; the clay materials don't use them)."""
    if o.type != 'MESH' or o.data.uv_layers:
        return
    uv = o.data.uv_layers.new(name='UVMap')
    mw = o.matrix_world
    for loop in o.data.loops:
        p = G(mw @ o.data.vertices[loop.vertex_index].co)
        uv.data[loop.index].uv = (0.5 + math.atan2(p.x, -p.z) / (2 * math.pi), p.y / 2.0)


# --- build ----------------------------------------------------------------------------------------------------

def main():
    cw = hb.COLOURWAYS['A']
    lib.reset()
    root = lib.empty('Character', (0, 0, 0))
    body = lib.empty('Body', (0, 0, 0), root)
    head = hb.head_parts(root)
    hb.PANTS_TRIS = 9000                                    # denser joggers: no faceted streaks down the thighs
    hb.outfit(cw, 'A', body)
    img, nrm = hb.rib_texture('#FFFFFF')                    # neutral ribs: the 'rib' paint slot tints them
    rib = lib.mat('Rib', '#FFFFFF', 0.9, image=img, normal=nrm)
    for o in bpy.data.objects:
        if o.name.startswith(('Hem', 'Collar', 'Cuff')):
            o.data.materials[0] = rib
    hb.hands(body)
    mannequin(body)
    tshirt(body, rib)
    if FEMALE:
        female_lower(body)
    hb.matte()
    table = hb.rig_table()
    rig = R.armature(table, root)
    # weights from the canonical shape (layers first: the attachments copy them)
    canon, wts = {}, {}
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in meshes:
        canon[o.name] = [G(o.matrix_world @ v.co) for v in o.data.vertices]
    for o in meshes:
        if o.name.startswith(('Hand', 'Nails')):
            if o.name.startswith('Hand'):
                R.soften_knuckles(o, -1 if o.name.endswith('L') else 1)
            continue
        if o.name == 'BodySkin':
            wts[o.name] = R.smooth(o, [body_weights(p) for p in canon[o.name]], 4)
        elif o.name == 'Pants' and FEMALE:   # loft: lower butt follows the thighs (no hanging skirt in a squat)
            wts[o.name] = R.smooth(o, [pants_weights(p) for p in canon[o.name]], 6)
        elif o.name in ('Top', 'Pants'):
            kind = hb.SKIN_KIND[0 if o.name == 'Top' else 1]
            wts[o.name] = R.smooth(o, R.weights_for(o, kind[1], hb.LANDMARKS), kind[2])
        elif o.name == 'HeadSkin':
            wts[o.name] = R.smooth(o, R.weights_for(o, 'neck', hb.LANDMARKS), 3)
        elif o.name.startswith(('Sole', 'Upper', 'Lace', 'Stripe')):
            wts[o.name] = R.weights_for(o, 'foot', hb.LANDMARKS)
    if hb.SPEC['chest']:
        for n in ('Top', 'BodySkin'):
            wts[n] = [hb.chest_weights(p, w) for p, w in zip(canon[n], wts[n])]
    trees = {}
    for n in ('Top', 'Pants'):
        t = KDTree(len(canon[n]))
        for i, p in enumerate(canon[n]):
            t.insert(p, i)
        t.balance()
        trees[n] = t
    for o in meshes:
        if os.environ.get('CHAR_OLDBANDS') and o.name.startswith(('Hem', 'Collar', 'Pocket', 'String', 'Aglet', 'Cuff',
                                                                   'PantCuff')):
            kind = next((k, n) for pre, k, n in hb.SKIN_KIND if o.name.startswith(pre))  # the v1 band weights
            ws = R.weights_for(o, kind[0], hb.LANDMARKS)
            wts[o.name] = R.smooth(o, ws, kind[1]) if kind[1] else ws
        elif o.name.startswith(('Hem', 'Collar', 'Cuff', 'Pocket', 'String', 'Aglet')):
            wts[o.name] = [top4(w) for w in transfer(o, canon['Top'], wts['Top'], trees['Top'])]
        elif o.name.startswith('PantCuff'):
            wts[o.name] = [top4(w) for w in transfer(o, canon['Pants'], wts['Pants'], trees['Pants'])]
    for n in ('BodySkin',):
        t = KDTree(len(canon[n]))
        for i, p in enumerate(canon[n]):
            t.insert(p, i)
        t.balance()
        trees[n] = t
    shirt = bpy.data.objects['Shirt']
    wts['Shirt'] = R.smooth(shirt, [top4(w) for w in transfer(shirt, canon['BodySkin'], wts['BodySkin'],
                                                               trees['BodySkin'])], 2)
    t = KDTree(len(canon['Shirt']))
    for i, p in enumerate(canon['Shirt']):
        t.insert(p, i)
    t.balance()
    trees['Shirt'] = t
    for o in meshes:
        if o.name.startswith(('ShirtCollar', 'ShirtSleeve')):
            wts[o.name] = [top4(w) for w in transfer(o, canon['Shirt'], wts['Shirt'], trees['Shirt'])]
    # blend shapes: fields on the body and the layers; attachments copy their layer's offsets (they stay on it)
    fields = {'Build_Slim': lambda c: build_offset(c, False), 'Build_Heavy': lambda c: build_offset(c, True)}
    if hb.SPEC['chest']:
        fields['Chest_Size'] = lambda c: hb.bust(c)[1]
    own = {}
    for n in ('BodySkin', 'Top', 'Pants', 'Shirt'):            # smooth fields (a copy by nearest points ripples)
        fs = dict(fields, Chest_Size=lambda c: hb.bust(c, False)[1]) if n == 'BodySkin' and 'Chest_Size' in fields \
            else fields
        own[n] = {k: [f(c) for c in canon[n]] for k, f in fs.items()
                  if k != 'Chest_Size' or any(hb.bust(c)[0] > 0 for c in canon[n])}

    def relax(o, offs, passes=6):
        nb = [[] for _ in o.data.vertices]
        for e in o.data.edges:
            a, b = e.vertices
            nb[a].append(b)
            nb[b].append(a)
        for _ in range(passes):
            offs = [(offs[i] + sum((offs[j] for j in n), Vector()) / len(n)) / 2 if n else offs[i]
                    for i, n in enumerate(nb)]
        return offs

    if 'Chest_Size' in own['Shirt']:                         # dense voxel cloth: relax the key (no ripples)
        own['Shirt']['Chest_Size'] = relax(bpy.data.objects['Shirt'], own['Shirt']['Chest_Size'])

    def host_of(name):
        if name.startswith(('ShirtCollar', 'ShirtSleeve')):
            return 'Shirt'
        return 'Pants' if name.startswith('PantCuff') else 'Top' if name.startswith(LAYERS) else None

    def keys_for(name):
        if name in own:
            return own[name]
        host = host_of(name)
        if host is None:
            return {}
        out = {}
        for k, offs in keys_for(host).items():
            col = []
            for c in canon[name]:
                acc, tw = Vector(), 0.0
                for _, i, d in trees[host].find_n(c, 4):
                    acc += offs[i] / max(d, 1e-4)
                    tw += 1.0 / max(d, 1e-4)
                col.append(acc / tw)
            if any(v.length > 1e-5 for v in col):
                out[k] = col
        own[name] = out
        return out

    hair_skinned = bool(CURLS)
    if hair_skinned:                                         # curls ride spring bones: hair is a skinned part
        o = bpy.data.objects['Hair']
        inv, shift = o.matrix_world.inverted(), hb.warp(hb.NECK) - hb.NECK
        k = hb.SPEC['head']
        hw = [curl_weights(hb.HEAD_PIVOT + (c - hb.HEAD_PIVOT) / k) for c in canon['Hair']]
        for v, c in zip(o.data.vertices, canon['Hair']):
            v.co = inv @ B(c + shift)                        # the head's rigid move (the body warp would squash it)
        R.skin(o, R.smooth(o, hw, 1), rig)
    # warp to the spec, skin, blend shapes
    for o in meshes:
        mw = o.matrix_world.copy()
        inv = mw.inverted()
        if o.name.startswith(('Hand', 'Nails')):
            wr = hb.mirror(hb.WRIST, -1 if o.name.endswith('L') else 1)
            if not hb.IDENT:
                o.matrix_world = Matrix.Translation(B(hb.warp(wr) - wr)) @ mw
            R.skin(o, [], rig)
            continue
        if o.name not in wts:
            continue                                           # rigid head parts and hair
        for v, c in zip(o.data.vertices, canon[o.name]):
            v.co = inv @ B(hb.warp(c))
        R.skin(o, wts[o.name], rig)
        if keys_for(o.name):
            o.shape_key_add(name='Basis')
            for name, offs in keys_for(o.name).items():
                sk = o.shape_key_add(name=name)
                for i, c in enumerate(canon[o.name]):
                    sk.data[i].co = inv @ B(hb.warp(c + offs[i]))
    if not hb.IDENT:
        head.matrix_world = Matrix.Translation(B(hb.warp(hb.NECK) - hb.NECK)) @ head.matrix_world
        bpy.context.view_layer.update()
    regions = split_regions(bpy.data.objects['BodySkin'], canon['BodySkin'])
    for o in bpy.data.objects:
        ensure_uvs(o)
    # clips: the face rides the Head bone while baking (ground checks), then goes back to character space at rest
    face_mw = head.matrix_world.copy()
    R.attach(head, rig, 'Head')
    rig['clips'] = R.clips(rig, hb.ARM_UP, hb.LANDMARKS, full=hb.SPEC['clips'] == 'all', mock=hb.SPEC['mock'])
    if os.environ.get('CHAR_CHECK'):
        clearance(rig)
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    head.parent = None
    head.matrix_world = face_mw
    bpy.context.view_layer.update()                    # the hair's world matrix follows only after an update
    hair = bpy.data.objects['Hair']
    if not hair_skinned:
        hmw = hair.matrix_world.copy()
        hair.parent = None
        hair.matrix_world = hmw
    bpy.context.view_layer.update()
    export_all(rig, head, hair, regions, hair_skinned)


# --- clearance check (CHAR_CHECK=1) ---------------------------------------------------------------------------



BANDS = {'Shirt': ('ShirtCollar', 'ShirtSleeveL', 'ShirtSleeveR'), 'Top': ('Hem', 'Pocket', 'Collar', 'CuffL', 'CuffR', 'StringL', 'StringR'), 'Pants': ('PantCuffL', 'PantCuffR')}


def clearance(rig):
    """Bands and the pocket riding their layer: per vertex, the change of its distance to the Top/Pants surface from
    the base build at rest (to the same layer verts, paired at bind), for each build key (and chest size), at rest and through clip frames. A rubber ring or a
    pocket poking through shows as drift. Prints CLEAR <case> <band>: max drift mm (p99) per case."""
    from mathutils.bvhtree import BVHTree
    keyed = [o for o in bpy.data.objects if o.type == 'MESH' and o.data.shape_keys]
    cases = [('base', {}), ('slim', {'Build_Slim': 1}), ('heavy', {'Build_Heavy': 1})]
    if hb.SPEC['chest']:
        cases += [('chest1', {'Chest_Size': 1}), ('heavy_chest1', {'Build_Heavy': 1, 'Chest_Size': 1})]
    poses = [(None, 0)] + [(n, f) for n in ('squat', 'walk_loop', 'sit_tub', 'sit_floor', 'get_up_back', 'faceplant')
                           if n in bpy.data.actions for f in range(0, int(bpy.data.actions[n].frame_range[1]) + 1, 6)]
    ref, pairs = {}, {}
    for cname, vals in cases:
        for o in keyed:
            for kb in o.data.shape_keys.key_blocks[1:]:
                kb.value = vals.get(kb.name, 0.0)
        drift = {}
        for act, f in poses if os.environ.get('CHAR_CHECK') != '2' else poses[:1]:
            rig.animation_data.use_nla = act is None
            rig.animation_data.action = bpy.data.actions[act] if act else None
            if act is None:
                for pb in rig.pose.bones:
                    pb.rotation_quaternion, pb.location = (1, 0, 0, 0), (0, 0, 0)
            bpy.context.scene.frame_set(f)
            dg = bpy.context.evaluated_depsgraph_get()
            for host, bands in BANDS.items():
                co = bpy.data.objects[host].evaluated_get(dg)
                hv = [co.matrix_world @ v.co for v in co.to_mesh().vertices]
                co.to_mesh_clear()
                for bn in bands:
                    o = bpy.data.objects[bn]
                    ev = o.evaluated_get(dg)
                    pts = [o.matrix_world @ v.co for v in ev.to_mesh().vertices]
                    ev.to_mesh_clear()
                    if bn not in pairs:                  # fixed correspondences: the layer verts nearest at bind
                        h = bpy.data.objects[host]
                        t = KDTree(len(h.data.vertices))
                        for i, v in enumerate(h.data.vertices):
                            t.insert(h.matrix_world @ v.co, i)
                        t.balance()
                        pairs[bn] = [[i for _, i, _ in t.find_n(o.matrix_world @ v.co, 4)] for v in o.data.vertices]
                    d = [(x - sum((hv[i] for i in ids), Vector()) / len(ids)).length for x, ids in zip(pts, pairs[bn])]
                    if bn not in ref:
                        ref[bn] = d
                    if act is None and os.environ.get('CHAR_CHECK') == '2':
                        dd = [x - y for x, y in zip(d, ref[bn])]
                        i = max(range(len(dd)), key=lambda j: abs(dd[j]))
                        print('REST', cname, bn, '%.1fmm at y %.3f' % (dd[i] * 1000, G(pts[i]).y))
                    dd = sorted(abs(x - y) for x, y in zip(d, ref[bn]))
                    key = bn.rstrip('LR') if bn not in ('Hem', 'Pocket', 'Collar') else bn
                    m, p99 = dd[-1], dd[int(len(dd) * 0.99)]
                    old = drift.get(key, (0, 0, ''))
                    if m > old[0]:
                        drift[key] = (m, max(p99, old[1]), '%s@%d' % (act or 'rest', f))
                    else:
                        drift[key] = (old[0], max(p99, old[1]), old[2])
        print('CLEAR', cname, '  '.join('%s %.0fmm (p99 %.0f) %s' % (k, v[0] * 1000, v[1] * 1000, v[2])
                                       for k, v in sorted(drift.items())))
    for o in keyed:
        for kb in o.data.shape_keys.key_blocks[1:]:
            kb.value = 0.0
    rig.animation_data.use_nla = True


# --- export ---------------------------------------------------------------------------------------------------

def _export(path, objs, anims):
    bpy.context.scene.render.fps, bpy.context.scene.render.fps_base = R.FPS, 1.0
    for o in bpy.data.objects:
        o.select_set(o in objs)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kw = dict(export_animation_mode='NLA_TRACKS', export_force_sampling=True) if anims else dict(export_animations=False)
    lib.export_glb(filepath=path, export_format='GLB', export_yup=True, use_selection=True, export_cameras=False,
                   export_lights=False, export_extras=True, export_skins=True, export_morph=True,
                   export_morph_normal=os.environ.get('CHAR_MORPH_NORMAL', '1') == '1', **kw)


def _tscn(folder, name):
    path = os.path.join(folder, name + '.tscn')
    rel = os.path.relpath(os.path.join(folder, name + '.glb'), ROOT)
    with open(path, 'w') as f:
        f.write('[gd_scene format=3]\n\n[ext_resource type="PackedScene" path="res://%s" id="1"]\n\n'
                '[node name="%s" instance=ExtResource("1")]\n' % (rel, name))


def _json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=1)


def export_all(rig, head, hair, regions, hair_skinned=False):
    base = BASE + '_base'
    out = os.path.join(ROOT, 'characters', base, 'art')
    bodies = regions + [o for o in bpy.data.objects if o.name.startswith(('HandL', 'HandR', 'NailsL', 'NailsR'))]
    _export(os.path.join(out, base + '.glb'), [rig] + bodies, True)
    _tscn(out, base)
    face = [o for o in head.children_recursive if o != hair and o not in hair.children_recursive]
    face.append(bpy.data.objects['HeadSkin'])
    hidden = [o.name for o in face if o.get('hidden')]
    hb.rig_json(os.path.join(out, base + '_rig.json'), hidden)    # hidden + expressions: the default head's face parts
    rj = json.load(open(os.path.join(out, base + '_rig.json')))
    rj['first_person'] += ['Body_LowerArmL', 'Body_LowerArmR']      # bare forearms under a T-shirt
    _json(os.path.join(out, base + '_rig.json'), rj)
    parts = {'head': HEAD_ID, 'hair': HAIR_ID, 'top': ('tshirt' if FEMALE else 'hoodie') + SFX, 'bottom': 'joggers' + SFX, 'shoes': 'sneakers' + SFX}
    colors = dict(COLORS, top=SHIRT[0], rib=SHIRT[1]) if FEMALE else COLORS
    cj = {'parts': parts, 'paint': PAINT, 'colors': colors, 'shapes': {'Build_Slim': 0.0, 'Build_Heavy': 0.0}}
    if CURLS:
        cj['springs'] = springs()
    if hb.SPEC['chest']:
        cj['shapes']['Chest_Size'] = 0.7
        cj['chest'] = {'chains': [['LeftBreast', 'LeftBreast'], ['RightBreast', 'RightBreast']], 'radius': 0.05,
                       'tip_dir': [0, 0, -1], 'tip': 0.1}
    _json(os.path.join(out, 'character.json'), cj)
    pdir = lambda pid: os.path.join(ROOT, 'characters', 'parts', pid, 'art')
    # head: skinned neck (HeadSkin) + rigid face parts in character space at rest
    _export(os.path.join(pdir(HEAD_ID), HEAD_ID + '.glb'), [rig, head] + face, False)
    _tscn(pdir(HEAD_ID), HEAD_ID)
    _json(os.path.join(pdir(HEAD_ID), 'part.json'), {'slot': 'head', 'attach': 'Head', 'hidden': hidden,
                                                       'expressions': hb.EXPRESSIONS})
    _export(os.path.join(pdir(HAIR_ID), HAIR_ID + '.glb'), ([rig] if hair_skinned else []) + [hair], False)
    _tscn(pdir(HAIR_ID), HAIR_ID)
    _json(os.path.join(pdir(HAIR_ID), 'part.json'), {'slot': 'hair'} if hair_skinned else {'slot': 'hair', 'attach': 'Head'})
    for pid, (slot, prefixes, hides) in PARTS.items():
        objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(prefixes)]
        _export(os.path.join(pdir(pid + SFX), pid + SFX + '.glb'), [rig] + objs, False)
        _tscn(pdir(pid + SFX), pid + SFX)
        _json(os.path.join(pdir(pid + SFX), 'part.json'), {'slot': slot, 'hides': hides})
    print('CHAR_BUILT', base, len(regions), 'regions:', ' '.join(sorted(o.name for o in regions)))


PAINT = {'CK2_Shirt' + SHIRT[0][1:]: 'top', 'CK2_Rib': 'rib', 'CK2_Skin': 'skin', 'CK2_Hair': 'hair', 'CK2_Brow': 'hair*0.82', 'CK2_Pupil': 'eyes', 'CK2_Blush': 'blush'}
COLORS = {'skin': hb.SKIN, 'hair': hb.HAIR, 'eyes': '#2E2624', 'blush': 'auto'}
for _m, _slot in (('Top', 'top'), ('Pants', 'bottom'), ('PantCuff', 'bottom'), ('Shoe', 'shoes')):
    _key = {'Top': 'top', 'Pants': 'pants', 'PantCuff': 'pants', 'Shoe': 'shoe'}[_m]
    PAINT['CK2_' + _m + hb.COLOURWAYS['A'][_key][1:]] = _slot
COLORS.update(rib=hb.COLOURWAYS['A']['rib'], top=hb.COLOURWAYS['A']['top'], bottom=hb.COLOURWAYS['A']['pants'], shoes=hb.COLOURWAYS['A']['shoe'])

main()
