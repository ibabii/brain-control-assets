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
from sculpt import meta, ell, cap, ball, chain, solid, adopt, Surface, decal  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import accessories as acc  # noqa: E402

hb.ACCESSORY_HOOK = acc.build

FEMALE = hb.FEMALE
ROOT = lib.ROOT
PARTS = {  # part id -> (slot, mesh name prefixes, hides)
    'hoodie': ('top', ('Top', 'Hem', 'Collar', 'Cuff', 'Pocket', 'String', 'Aglet'),
               ['Body_Torso', 'Body_UpperArmL', 'Body_UpperArmR', 'Body_LowerArmL', 'Body_LowerArmR']),
    'joggers': ('bottom', ('Pants', 'PantCuff'),
                ['Body_Hips', 'Body_UpperLegL', 'Body_UpperLegR', 'Body_LowerLegL', 'Body_LowerLegR']),
    'tshirt': ('top', ('Shirt',), ['Body_Torso']),
    'sneakers': ('shoes', ('Sole', 'Upper', 'Lace', 'Stripe'), ['Body_FootL', 'Body_FootR']),
    'overshirt': ('outer', ('Overshirt', 'Os'), ['Body_UpperArmL', 'Body_UpperArmR']),   # rolled: forearms show
    'cardigan': ('outer', ('Cardigan', 'Cg'), ['Body_UpperArmL', 'Body_UpperArmR', 'Body_LowerArmL', 'Body_LowerArmR']),
    'slippers': ('shoes', ('Slipper',), ['Body_FootL', 'Body_FootR']),
    'stain_coffee': ('stain', ('Stain',), []),
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
    if not FEMALE:                                     # female: a soft neck-to-arm slope (torso loft), no shoulder bar
        cap(torso, (-0.15, 1.33, 0.004), (0.15, 1.33, 0.004), v['shoulder'] - 0.018)
    cap(torso, (0, 1.30, 0.008), (0, 1.43, 0.008), 0.048)                       # neck stub (into the head's neck)
    fams = [torso]
    for s, side in ((-1, 'L'), (1, 'R')):
        arm = meta('BodyArm' + side, 0.007)
        sh, el, wr = m(s, hb.SHOULDER), m(s, hb.ELBOW), m(s, hb.WRIST)
        cap(arm, sh, el, 0.046 * v['limb'])
        if FEMALE:                                     # soft forearm: full below the elbow, easing to a slim wrist
            end = wr - m(s, hb.FORE) * 0.02
            pts = [el.lerp(end, i / 12) for i in range(13)]
            for i, p_ in enumerate(pts):
                t = i / 12
                ball(arm, p_, (0.044 - 0.013 * t * t * (3 - 2 * t) + 0.003 * math.sin(math.pi * min(1, t * 2.2))) * v['limb'])
        else:
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
    if not FEMALE:
        cap(t, (-0.15, 1.335, 0.004), (0.15, 1.335, 0.004), v['shoulder'] - 0.008)
    fams = [t]
    for s in (-1, 1):
        sl = meta('ShirtSleeve%d' % s, 0.007)
        sh, el = m(s, hb.SHOULDER), m(s, hb.ELBOW)
        end = sh + (el - sh) * 0.5
        ax = (el - sh).normalized()
        if FEMALE:                                     # relaxed shoulder: small low cap, sleeve tube starts down the arm
            ball(sl, sh, 0.055 * v['limb'])
            cap(sl, sh + ax * 0.04, end - ax * 0.03, 0.058 * v['limb'])
        else:
            ball(sl, sh + Vector((-s * 0.006, -0.008, 0)), 0.056 * v['limb'])
            cap(sl, sh, end - ax * 0.03, 0.058 * v['limb'])      # its rounded end stays inside the band
        fams.append(sl)
        r = 0.058 * v['limb'] * 1.04                  # a hair over the sleeve end: caps its edge cleanly
        hb.band('ShirtSleeve' + ('L' if s < 0 else 'R'), hb.frame_along(end, el - sh), r, r, 0.026, 0.06, rib, parent)
    mat = lib.mat('Shirt' + SHIRT[0][1:], SHIRT[0], 0.9)
    o = solid('Shirt', fams, 0.008, 10 ** 6, mat)
    if FEMALE:
        o = union('Shirt', [o, tube('ShirtLoft', SHIRT_TORSO)], 0.008, mat, 2)
    shirt = adopt(o, parent, (0, 1.1, 0))
    if FEMALE:
        cat_print(shirt, parent)
    hb.band('ShirtCollar', hb.Frame((0, 1.405, 0.0)), 0.066, 0.062, 0.022, 0.12, rib, parent)
    return shirt


OVERSHIRT = '#26324A'                  # the roommate's ink-navy overshirt (paint slot `outer`)


def overshirt(parent):
    """Open button-up overshirt worn over a T-shirt (the roommate, s1 cast): a loose hip-length shell a little over
    the tee, cut open down the front, with plackets, buttons on the right panel, a folded collar, a chest pocket
    and wrist cuffs. Male base (slot `outer`)."""
    import bmesh
    from sculpt import Surface, decal
    v = hb.TOP_VOL
    m = lambda s, x: hb.mirror(x, s)
    c, bl, fl = v['chest'], v['belly'], v['flare']
    b = meta('OsBody', 0.008)
    ell(b, (0, 1.22, 0.0), (c[0] - 0.008, c[1], c[2] - 0.008))          # light cotton, ~1 cm over the tee
    ell(b, (0, 1.04, v['belly_z'] * 0.6), (bl[0] - 0.012, bl[1], bl[2] - 0.014))
    ell(b, (0, 0.92, 0.0), (fl[0] - 0.018, 0.08, fl[2] - 0.016))
    cap(b, (-0.15, 1.34, 0.006), (0.15, 1.34, 0.006), v['shoulder'] - 0.008)
    ell(b, (0, 1.40, 0.04), (0.085, 0.05, 0.07))                       # the back of the neck under the collar
    fams = [b]
    for s_ in (-1, 1):
        sl = meta('OsSleeve%d' % s_, 0.008)
        sh, el, wr = m(s_, hb.SHOULDER), m(s_, hb.ELBOW), m(s_, hb.WRIST)
        ball(sl, sh + Vector((-s_ * 0.006, -0.012, 0)), 0.061 * v['limb'])
        cap(sl, sh, sh + (el - sh) * 0.5, 0.0615 * v['limb'])         # just over the tee's sleeve bands
        cap(sl, sh + (el - sh) * 0.5, el, 0.055 * v['limb'])           # light cotton: tapers to the elbow
        cap(sl, el, el + (wr - el) * ROLL, 0.05 * v['limb'])           # rolled up to mid-forearm (ends in the roll)
        fams.append(sl)
    mat = lib.mat('Overshirt', OVERSHIRT, 0.9)
    o = solid('Overshirt', fams, 0.006, 9000, mat)
    cx, cz = c[0] - 0.008, c[2] - 0.008
    for vt in o.data.vertices:                                        # flat front panels: hang straight from the chest
        q = G(o.matrix_world @ vt.co)
        if q.z < 0 and q.y < 1.26:
            zc = -cz * math.sqrt(max(0.0, 1 - (q.x / cx) ** 2))
            wgt = hb._ss((1.26 - q.y) / 0.1) * hb._ss((cx - abs(q.x)) / 0.05)
            q.z = q.z + (min(q.z, zc) - q.z) * wgt
            vt.co = o.matrix_world.inverted() @ B(q)
    width = lambda y: 0.058 + 0.022 * hb._ss((1.25 - y) / 0.35) + 0.03 * hb._ss((y - 1.29) / 0.09)   # opener panels
    bm = bmesh.new()                                                  # cut the front open and the bottom off
    bm.from_mesh(o.data)
    cut = [f for f in bm.faces if (lambda q: q.y < 0.865 or (q.z < -0.03 and abs(q.x) < width(q.y) and q.y < 1.47))(
        G(f.calc_center_median()))]
    bmesh.ops.delete(bm, geom=cut, context='FACES')
    for vt in bm.verts:                                               # clean edges: snap the cut onto its curves
        if not vt.is_boundary:
            continue
        q = G(vt.co)
        if q.y < 0.885:
            q.y = 0.865
        elif q.z < -0.0 and q.y < 1.47:
            q.x = math.copysign(width(q.y), q.x)
        vt.co = B(q)
    bm.to_mesh(o.data)
    bm.free()
    sol = o.modifiers.new('Cloth', 'SOLIDIFY')                       # a real cloth edge (no see-through rim)
    sol.thickness, sol.offset = 0.004, -1.0
    for x in bpy.data.objects:
        x.select_set(x == o)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier='Cloth')
    shirt = adopt(o, parent, (0, 1.1, 0))
    surf = Surface(shirt)
    trim = lib.mat('Overshirt', OVERSHIRT, 0.9)
    for s_ in (-1, 1):                                                # plackets down both edges
        pts = []
        for i in range(25):
            y = 0.87 + (1.31 - 0.87) * i / 24
            x = s_ * (width(y) + 0.006)
            loc, nrm = surf.hit((x, y, -0.4), (0, 0, 1))
            pts.append(loc + nrm * 0.002)
        lib.tube('OsPlacket%s' % ('L' if s_ < 0 else 'R'), pts, 0.0065, trim, parent, res=6, bevel_res=2)
    btn = lib.mat('OsButton', '#E9E1D2', 0.5)
    for k in range(6):                                                # buttons on the wearer's right panel
        y = 0.93 + 0.072 * k
        loc, nrm = surf.hit((width(y) + 0.02, y, -0.4), (0, 0, 1))
        lib.tube('OsButton%d' % k, [loc, loc + nrm * 0.004], 0.0065, btn, parent, res=3, bevel_res=1)
    col = meta('OsCollar', 0.003)                                     # folded collar: round the neck, points down
    ring = []
    for i in range(41):
        phi = 0.62 + (2 * math.pi - 1.24) * i / 40
        ring.append(Vector((0.086 * math.sin(phi), 1.402 + 0.016 * (1 - math.cos(phi)) / 2, -0.082 * math.cos(phi))))
    chain(col, ring, 0.013, 0.013, step=0.003)
    for s_, end in ((1, ring[0]), (-1, ring[-1])):
        chain(col, [end, end + Vector((s_ * 0.012, -0.035, -0.022)), end + Vector((s_ * 0.022, -0.07, -0.03))],
              0.013, 0.006, step=0.003)
    adopt(solid('OsCollar', [col], 0.0025, 3000, trim), parent, (0, 1.4, 0))
    decal('OsPocket', surf, [(-0.125, 1.17), (-0.06, 1.17), (-0.058, 1.245), (-0.127, 1.245)], hb.Frame(), trim,
          parent, offset=0.002, rings=3, depth=0.004)
    for s_, side in ((-1, 'L'), (1, 'R')):                            # rolled sleeve: two soft turns, not a cuff
        el, wr = m(s_, hb.ELBOW), m(s_, hb.WRIST)
        end, d = el + (wr - el) * ROLL, (wr - el).normalized()
        lr = 0.053 * v['limb']
        hb.band('OsRoll' + side, hb.frame_along(end - d * 0.012, d), lr, lr, 0.03, 0.12, trim, parent)
        hb.band('OsRoll2' + side, hb.frame_along(end - d * 0.036, d), lr * 1.02, lr * 1.02, 0.022, 0.1, trim, parent)
    return shirt


def cardigan(parent):
    """Knit cardigan over a top (Mom, female base, slot `outer`): hip length, V-neck, a knit front band round the
    neck with buttons below the V, patch pockets, knit hem and cuffs. Material CK2_Overshirt / CK2_CgRib -> `outer`."""
    import bmesh
    v = hb.TOP_VOL
    m = lambda s, x: hb.mirror(x, s)
    c, bl, fl = v['chest'], v['belly'], v['flare']
    b = meta('CgBody', 0.008)
    ell(b, (0, 1.22, 0.0), (c[0] + 0.012, c[1] + 0.01, c[2] + 0.018))   # roomy over the female tee's loft
    ell(b, (0, 1.04, v['belly_z'] * 0.6), (bl[0] + 0.01, bl[1], bl[2] + 0.01))
    ell(b, (0, 0.92, 0.0), (fl[0] - 0.004, 0.08, fl[2]))
    cap(b, (-0.14, 1.345, 0.008), (0.14, 1.345, 0.008), v['shoulder'] + 0.01)
    ell(b, (0, 1.39, 0.04), (0.095, 0.06, 0.08))
    fams = [b]
    for s_ in (-1, 1):
        sl = meta('CgSleeve%d' % s_, 0.008)
        sh, el, wr = m(s_, hb.SHOULDER), m(s_, hb.ELBOW), m(s_, hb.WRIST)
        ball(sl, sh + Vector((-s_ * 0.006, -0.01, 0)), 0.068 * v['limb'])
        cap(sl, sh, sh + (el - sh) * 0.6, 0.066 * v['limb'])
        cap(sl, sh + (el - sh) * 0.6, el, 0.059 * v['limb'])
        cap(sl, el, wr - m(s_, hb.FORE) * 0.08, 0.05 * v['limb'])      # ends inside the knit cuff
        fams.append(sl)
    mat = lib.mat('Overshirt', OVERSHIRT, 0.9)
    o = solid('Cardigan', fams, 0.006, 9000, mat)
    width = lambda y: 0.022 + 0.012 * hb._ss((1.0 - y) / 0.12) + 0.075 * hb._ss((y - 1.13) / 0.25)   # the V
    bm = bmesh.new()
    bm.from_mesh(o.data)
    cut = [f for f in bm.faces if (lambda q: q.y < 0.865 or (q.z < -0.03 and abs(q.x) < width(q.y) and q.y < 1.47))(
        G(f.calc_center_median()))]
    bmesh.ops.delete(bm, geom=cut, context='FACES')
    for vt in bm.verts:                                               # clean edges: snap the cut onto its curves
        if not vt.is_boundary:
            continue
        q = G(vt.co)
        if q.y < 0.885:
            q.y = 0.865
        elif q.z < 0.0 and q.y < 1.47:
            q.x = math.copysign(width(q.y), q.x)
        vt.co = B(q)
    bm.to_mesh(o.data)
    bm.free()
    sol = o.modifiers.new('Cloth', 'SOLIDIFY')
    sol.thickness, sol.offset = 0.005, -1.0
    for x in bpy.data.objects:
        x.select_set(x == o)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier='Cloth')
    shirt = adopt(o, parent, (0, 1.1, 0))
    surf = Surface(shirt)
    img, nrm = hb.rib_texture('#FFFFFF')
    rib = lib.mat('CgRib', '#FFFFFF', 0.9, image=img, normal=nrm)     # knit bands tinted by the `outer` paint
    edge = []                                                         # front band: hem -> up the V -> round the neck
    for s_ in (-1, 1):
        pts = []
        for i in range(26):
            y = 0.87 + (1.37 - 0.87) * i / 25
            loc, nrm_ = surf.hit((s_ * (width(y) + 0.004), y, -0.4), (0, 0, 1))
            pts.append(loc + nrm_ * 0.002)
        edge.append(pts)
    band_pts = edge[0] + [Vector((-0.08, 1.4, -0.02)), Vector((-0.06, 1.425, 0.04)), Vector((0, 1.435, 0.07)),
                          Vector((0.06, 1.425, 0.04)), Vector((0.08, 1.4, -0.02))] + edge[1][::-1]
    lib.tube('CgBand', band_pts, 0.009, rib, parent, res=8, bevel_res=2)
    btn = lib.mat('CgButton', '#E9E1D2', 0.6)
    for k in range(4):                                                # buttons on the wearer's right band, below the V
        y = 0.93 + 0.06 * k
        loc, nrm_ = surf.hit((width(y) + 0.008, y, -0.4), (0, 0, 1))
        lib.tube('CgButton%d' % k, [loc + nrm_ * 0.006, loc + nrm_ * 0.011], 0.0062, btn, parent, res=3, bevel_res=1)
    for s_ in (-1, 1):                                                # patch pockets at the hips
        x0 = s_ * 0.075
        decal('CgPocket%d' % (s_ + 1), surf, [(x0 - 0.04, 0.9), (x0 + 0.04, 0.9), (x0 + 0.042, 0.98),
                                              (x0 - 0.042, 0.98)], hb.Frame(), mat, parent, offset=0.002, rings=3,
              depth=0.004)
    fl_ = v['flare']
    hb.band('CgHem', hb.Frame((0, 0.875, 0.0)), fl_[0] - 0.006, fl_[2] - 0.004, 0.035, 0.05, rib, parent)
    for s_, side in ((-1, 'L'), (1, 'R')):
        wr, d = m(s_, hb.WRIST), m(s_, hb.FORE)
        lr = 0.05 * v['limb']
        hb.band('CgCuff' + side, hb.frame_along(wr - d * 0.05, d), lr, lr, 0.05, 0.08, rib, parent)
    return shirt


ROLL = 0.45                            # overshirt sleeves end this far down the forearm (elbow 0 -> wrist 1)


PRINT = '#F8F4EA', '#4E2629'          # cat print + its ink (user: helps the chest read); paint slots print/print_ink


def slippers(parent):
    """E01 punchline slippers: fuzzy peach (boucle bumps), porcelain cuff, tiny ears, a cartoon face. Same
    footprint as the sneakers (they replace them in the shoes slot)."""
    fuzz = lib.mat('SlipperFuzz', '#EFA58C', 0.95)                  # peach, a touch pinker than the floor terracotta
    cuff = lib.mat('SlipperCuff', '#A85E4E', 0.95)                  # darker clay inner/cuff + sole: reads on any floor
    sole = lib.mat('SlipperSole', '#8E4F42', 0.9)
    ink_m = lib.mat('SlipperInk', '#2E2624', 0.7)
    blush = lib.mat('SlipperBlush', '#D97F6E', 0.9)
    rng = __import__('random').Random(7)
    for s, side in ((-1, 'L'), (1, 'R')):
        x = hb.ANKLE.x * s
        f = hb.Frame((x, 0.0, -0.05), (-90, s * -6, 0))            # local y = toward the toe, z = up
        lib.slab('SlipperSole' + side, lib.rrect(0.142, 0.312, 0.065, 6), 0.026, 0.009, sole, f, parent)
        toe, toe_s = (0, 0.07, 0.06), (0.068, 0.056, 0.105)          # world semis (x, up, length)
        heel, heel_s = (0, -0.06, 0.06), (0.064, 0.056, 0.075)
        mb = meta('SlipperMeta' + side, 0.0045)
        ell(mb, f.at(toe), toe_s)
        ell(mb, f.at(heel), heel_s)
        for _ in range(70):                                          # boucle fuzz: little bumps on the top half
            u, v = rng.uniform(0, 2 * math.pi), rng.uniform(0.15, 1.0)
            c, sm = (toe, toe_s) if rng.random() < 0.6 else (heel, heel_s)
            d = Vector((math.cos(u) * math.sqrt(1 - v * v), math.sin(u) * math.sqrt(1 - v * v), v))
            if c is toe and d.y > 0.45 and v < 0.75:                 # keep the face (toe front) smooth
                continue
            p = Vector(c) + Vector((d.x * sm[0], d.y * sm[2], d.z * sm[1])) * 0.92
            ball(mb, f.at(p), 0.011)
        up = adopt(solid('SlipperBody' + side, [mb], 0.004, 2600, fuzz), parent, f.o)
        up.name = 'SlipperBody' + side
        ring = [f.at((math.cos(t) * 0.052, -0.05 + math.sin(t) * 0.045, 0.118)) for t in
                [2 * math.pi * k / 24 for k in range(25)]]
        lib.tube('SlipperCuff' + side, ring, 0.014, cuff, parent, res=6, bevel_res=2)
        top = Vector(toe) + Vector((0, toe_s[2] * 0.35, toe_s[1] * 0.95))
        for e in (-1, 1):                                            # ears on top of the toe, inner cuff colour
            lib.sphere('SlipperEar%s%d' % (side, e), 0.022, fuzz, hb.Frame(f.at(top + Vector((e * 0.035, -0.01, 0.012))),
                       (-20, s * -6, e * 25)), parent, scale=(1, 1.1, 0.45), seg=16, rings=8)
            lib.sphere('SlipperEarIn%s%d' % (side, e), 0.013, cuff, hb.Frame(f.at(top + Vector((e * 0.035, -0.006, 0.014))),
                       (-20, s * -6, e * 25)), parent, scale=(1, 1.1, 0.45), seg=12, rings=6)
        surf = Surface(up)
        back = f.dir((0, -1, -0.3)).normalized()                     # look back (and a bit down) at the toe front
        for name, off, r, m in (('EyeL', (-0.021, 0.1), 0.0105, ink_m), ('EyeR', (0.021, 0.1), 0.0105, ink_m),
                                ('Nose', (0.0, 0.085), 0.006, cuff), ('BlushL', (-0.037, 0.08), 0.009, blush),
                                ('BlushR', (0.037, 0.08), 0.009, blush)):
            start = f.at((off[0], 0.4, off[1] + 0.07))
            loc, n = surf.hit(start, back)
            sink = 0.55 if name.startswith(('Eye', 'Nose')) else 0.85                # blush sits nearly flush
            lib.sphere('Slipper%s%s' % (name, side), r, m, hb.Frame(tuple(loc - n * r * sink)), parent, seg=12, rings=6)


def coffee_stain(parent):
    """E01 hoodie coffee splash on his left chest (palm size, darker edge ring, three drops): decals on the hoodie,
    exported as the `stain_coffee` part (slot `stain`), skinned like the hoodie."""
    surf = Surface(bpy.data.objects['Top'])
    ring_m = lib.mat('StainRing', '#6E4528', 0.85)
    fill_m = lib.mat('StainFill', '#966442', 0.85)
    cx, cy = -0.095, STAIN_Y

    def blob(r0, seed, drip=True):
        out = []
        for k in range(36):
            t = 2 * math.pi * k / 36
            r = r0 * (1 + 0.16 * math.sin(3 * t + seed) + 0.08 * math.sin(7 * t + 2 * seed))
            if drip:
                r += r0 * 0.55 * math.exp(-((t - 4.45) / 0.18) ** 2) + r0 * 0.35 * math.exp(-((t - 5.0) / 0.15) ** 2)
            out.append((cx + math.cos(t) * r, cy + math.sin(t) * r))
        return out
    fr = hb.Frame((0, 0, -0.6))
    decal('StainRing', surf, blob(0.047, 0.4), fr, ring_m, parent, offset=0.0014, rings=4)
    decal('StainFill', surf, [(cx + (x - cx) * 0.8, cy + (y - cy) * 0.8 + 0.002) for x, y in blob(0.047, 0.4)], fr,
          fill_m, parent, offset=0.0024, rings=4)
    for i, (dx, dy, r) in enumerate(((0.06, 0.035, 0.008), (-0.055, -0.04, 0.006), (0.045, -0.055, 0.005))):
        decal('StainDrop%d' % i, surf, [(cx + dx + math.cos(t) * r, cy + dy + math.sin(t) * r)
                                        for t in [2 * math.pi * k / 12 for k in range(12)]], fr, ring_m, parent,
              offset=0.0016, rings=2)


STAIN_Y = 1.2


def _inside(pt, poly):
    x, y = pt
    c = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def cat_print(shirt, parent):
    """Cute cat face across the chest, painted INTO the tee: its chest faces are subdivided (~2.7 mm) and take the
    print materials by a front projection, so the print is the tee surface and can never tear when the chest moves.
    A cream head with pointy ears, ink eyes with glints, nose and a 'w' mouth."""
    import bmesh
    cy, hw, hh = 1.195, 0.086, 0.055                              # on the bust plateau: moves as one
    head = []
    for i in range(192):
        t = 2 * math.pi * i / 192
        r = 1.0
        for ta in (math.radians(50), math.radians(130)):                  # ears: sharp bumps up and out
            d = abs((t - ta + math.pi) % (2 * math.pi) - math.pi)
            r += 0.6 * max(0.0, 1 - d / 0.3) ** 1.6
        head.append((hw * r * math.cos(t), cy + hh * r * math.sin(t)))
    ink = [hb.ellipse(0.011, 0.014, 24, sx * 0.033, cy + 0.007) for sx in (-1, 1)]
    ink.append([(0.0, cy - 0.019), (-0.01, cy - 0.009), (0.01, cy - 0.009)])                   # nose
    xs = [-0.022 + 0.044 * i / 24 for i in range(25)]
    top = [(x, cy - 0.025 - 0.008 * abs(math.sin(math.pi * (x + 0.022) / 0.022))) for x in xs]
    ink.append(top + [(x, y - 0.006) for x, y in reversed(top)])       # 'w' mouth
    glints = [hb.ellipse(0.0038, 0.0038, 12, sx * 0.033 + 0.0036, cy + 0.0128) for sx in (-1, 1)]
    me = shirt.data
    mats = [lib.mat('Print', PRINT[0], 0.85), lib.mat('PrintInk', PRINT[1], 0.8)]
    for m in mats:
        me.materials.append(m)
    ip, ii = len(me.materials) - 2, len(me.materials) - 1
    mw = shirt.matrix_world
    bm = bmesh.new()
    bm.from_mesh(me)
    near = lambda f: (lambda c: c.z < 0 and abs(c.x) < 0.13 and cy - 0.08 < c.y < cy + 0.11)(G(mw @ f.calc_center_median()))
    for _ in range(2):                                                   # two halvings: ~2.7 mm faces under the print
        edges = list({e for f in bm.faces if near(f) for e in f.edges})
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
    for f in bm.faces:
        if not near(f):
            continue
        c = G(mw @ f.calc_center_median())
        q = (c.x, c.y)
        if any(_inside(q, g) for g in glints):
            f.material_index = ip
        elif any(_inside(q, g) for g in ink):
            f.material_index = ii
        elif _inside(q, head):
            f.material_index = ip
    # snap the print's edge vertices onto the outlines (smooth edges instead of 2.7 mm stair-steps); xy only, tiny
    def seg_near(q, poly):
        best, bd = None, 1e9
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            dx, dy = x1 - x0, y1 - y0
            t = max(0.0, min(1.0, ((q[0] - x0) * dx + (q[1] - y0) * dy) / max(dx * dx + dy * dy, 1e-12)))
            c = (x0 + t * dx, y0 + t * dy)
            d = (c[0] - q[0]) ** 2 + (c[1] - q[1]) ** 2
            if d < bd:
                best, bd = c, d
        return best, bd
    inv = mw.inverted()
    for v in bm.verts:
        ms = {f.material_index for f in v.link_faces}
        if len(ms) < 2:
            continue
        g = G(mw @ v.co)
        polys = (glints + ink) if ii in ms or (ms - {0, ip}) else [head]
        if ms == {0, ip}:
            polys = [head]
        c, d = min((seg_near((g.x, g.y), poly) for poly in polys), key=lambda r: r[1])
        if d < 0.003 ** 2:
            v.co = inv @ B(Vector((c[0], c[1], g.z)))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()


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


def curl_name(i, s):
    return '%s_Curl%s%d' % (HAIR_ID, 'L' if s < 0 else 'R', i % 2)    # part bones carry the part id


CURL_SEGS = 4              # bones per ringlet (cheek curls swing without shearing into the face)
BUN_CURLS = ((0.5, 0.1), (2.7, -0.15), (4.3, 0.3))   # build.hair_bun's loose curls (azimuth, rise)


def bun_curl_axis(j, t):
    """Centre line of build.hair_bun's loose curl j (no helix), t 0 (bun surface) .. 1 (tip)."""
    az, up = BUN_CURLS[j]
    o = Vector((math.cos(az), up, math.sin(az))).normalized()
    return hb.BUN + o * (0.045 * hb.BUN_S + 0.045 * t) + Vector((0, -0.03 * t * t, 0))


def curl_bones():
    """Ringlet chains under Head: <part>_Curl<L|R><n>_1.._4 (top to bottom), and the bun's loose curls
    <part>_BunCurl<j>_1.._3 under the bun bone. Declared by the hair part (part.json `bones`), not the base."""
    out = []
    for i, (s, top, bot) in enumerate(CURLS):
        n = curl_name(i, s)
        for k in range(CURL_SEGS):
            a, b = top + (bot - top) * k / CURL_SEGS, top + (bot - top) * (k + 1) / CURL_SEGS
            out.append(('%s_%d' % (n, k + 1), hb.head_xf(a), hb.head_xf(b), Vector((0, 0, -1)),
                        'Head' if k == 0 else '%s_%d' % (n, k)))
    return out


def bun_curl_bones():
    out = []
    for j in range(len(BUN_CURLS)):
        n = '%s_BunCurl%d' % (HAIR_ID, j)
        for k in range(3):
            a, b = bun_curl_axis(j, k / 3 - (0.12 if k == 0 else 0)), bun_curl_axis(j, (k + 1) / 3)
            out.append(('%s_%d' % (n, k + 1), hb.head_xf(a), hb.head_xf(b), Vector((0, 0, -1)),
                        HAIR_ID + '_Bun' if k == 0 else '%s_%d' % (n, k)))
    return out


def part_bones():
    """The hair part's bones: the ringlet chains, one bun bone (a spring, so the bun bobs), the bun's curl chains."""
    z = hb.BUN_S
    return curl_bones() + [(HAIR_ID + '_Bun', hb.head_xf(hb.BUN - Vector((0, 0.035 * z, 0))),
                            hb.head_xf(hb.BUN + Vector((0, 0.06 * z, 0))), Vector((0, 0, -1)), 'Head')] + \
        bun_curl_bones()


if CURLS:
    _rig_table = hb.rig_table
    hb.rig_table = lambda: _rig_table() + part_bones()        # rig, rig json 'bones' and the export all see them


def _chain_w(prefix, t, n):
    """Smooth weights along an n-bone chain at t 0..1 (each bone peaks at its middle)."""
    w = {'%s_%d' % (prefix, k + 1): max(0.0, 1 - abs(t * n - (k + 0.5))) for k in range(n)}
    if t * n < 0.5:
        w['%s_1' % prefix] = 1.0
    if t * n > n - 0.5:
        w['%s_%d' % (prefix, n)] = 1.0
    tot = sum(w.values())
    return {k: v / tot for k, v in w.items() if v > 1e-4}


def curl_weights(q):
    """Hair vertex (canonical head space) -> weights. Bun curls ride their chains (fading into the bun at the
    root), the bun rides its bone (fading in from the crown), ringlets ride their whole chain (only a short fade
    into Head at the root, so the swing never drags the cheek); the rest is Head."""
    z = hb.BUN_S
    for j in range(len(BUN_CURLS)):                            # closest point on the curl's centre line
        best = min(((q - bun_curl_axis(j, t / 20)).length, t / 20) for t in range(-2, 21))
        if best[0] < 0.022 and best[1] > -0.05:
            t = max(0.0, best[1])
            g = hb._ss(t / 0.15)
            w = {k: v * g for k, v in _chain_w('%s_BunCurl%d' % (HAIR_ID, j), t, 3).items()}
            if g < 1:
                w[HAIR_ID + '_Bun'] = 1 - g
            return {k: v for k, v in w.items() if v > 1e-4}
    d = q - hb.BUN
    if d.y > -0.05 * z and Vector((d.x, 0, d.z)).length < 0.075 * z + 0.02 and d.length < 0.11 * z + 0.03:
        g = hb._ss((d.y + 0.05 * z) / (0.03 * z))
        return {k: v for k, v in ((HAIR_ID + '_Bun', g), ('Head', 1 - g)) if v > 1e-4}
    for i, (s, top, bot) in enumerate(CURLS):
        if q.x * s <= 0 or math.hypot(q.x - top.x, q.z - top.z) > 0.042 or not bot.y - 0.025 < q.y < top.y + 0.02:
            continue
        t = max(0.0, min(1.0, (top.y - q.y) / (top.y - bot.y)))
        g = hb._ss(t / 0.06)
        w = {k: v * g for k, v in _chain_w(curl_name(i, s), t, CURL_SEGS).items()}
        if g < 1:
            w['Head'] = 1 - g
        return {k: v for k, v in w.items() if v > 1e-4}
    return {'Head': 1.0}


def springs():
    cb, bc = curl_bones(), bun_curl_bones()
    out = [{'kind': 'hair', 'root': cb[i][0], 'end': cb[i + CURL_SEGS - 1][0], 'radius': 0.012, 'tip': 0.03,
            'stiffness': 0.8, 'drag': 0.3, 'gravity': 0.4} for i in range(0, len(cb), CURL_SEGS)]
    out.append({'kind': 'hair', 'root': HAIR_ID + '_Bun', 'end': HAIR_ID + '_Bun', 'radius': 0.05, 'tip': 0.03,
                'stiffness': 1.4, 'drag': 0.45, 'gravity': 0.15})
    out += [{'kind': 'hair', 'root': bc[i][0], 'end': bc[i + 2][0], 'radius': 0.008, 'tip': 0.02, 'stiffness': 0.9,
             'drag': 0.35, 'gravity': 0.3} for i in range(0, len(bc), 3)]   # ~20 deg of swing on a walk (tune)
    return out


def drape_field(pts):
    """Chest_Size offsets for a loose top: the bust key, and below the bust the front falls straight to the hem from
    the bust tip (no under-bust pinch), tucking a little into the rib. Needs the top's own front profile: the cloth
    already standing forward (pocket, belly) only moves as far as the tip line."""
    bins = {}
    for c in pts:                                              # the top's front z at bust height, per 1 cm of x
        if abs(c.y - hb.BUST.y) < 0.012 and c.z < 0:
            k = round(c.x * 100)
            bins[k] = min(bins.get(k, 0.0), c.z)

    def apex_z(x):
        ks = [k for k in bins if abs(k - x * 100) <= 1]
        return min(bins[k] for k in ks) if ks else None

    def tip_h(x):                                              # the bust height at the tip row for this column
        return hb.bust(Vector((x, hb.BUST.y, -0.2)))[1].length

    def f(c):
        off = hb.bust(c)[1]
        if c.z > -0.02 or c.y >= hb.BUST.y:
            return off
        az = apex_z(c.x)
        if az is None:
            return off
        need = c.z - (az - tip_h(c.x))                         # how far behind the tip line this point sits
        fall = hb._ss((c.y - 0.90) / 0.07) * (1 - 0.25 * hb._ss((0.99 - c.y) / 0.06))   # rib tucks in a little
        h = hb._smax(-off.z, max(0.0, need) * fall * hb._ss((-0.02 - c.z) / 0.06))
        return Vector((off.x, 0.0, -h))
    return f


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
               (1.27, 0, 0.150, 0.0, 0.098, 0.104), (1.295, 0, 0.136, 0.0, 0.094, 0.110),   # neck-to-arm slope
               (1.316, 0, 0.114, 0.0, 0.088, 0.114),
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
    if not FEMALE:
        overshirt(body)
        coffee_stain(body)
    else:
        cardigan(body)
    slippers(body)
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
        elif o.name in ('Overshirt', 'Cardigan'):                               # loose like the hoodie: the top weights
            wts[o.name] = R.smooth(o, R.weights_for(o, 'top', hb.LANDMARKS), 4)
        elif o.name in ('Top', 'Pants'):
            kind = hb.SKIN_KIND[0 if o.name == 'Top' else 1]
            wts[o.name] = R.smooth(o, R.weights_for(o, kind[1], hb.LANDMARKS), kind[2])
        elif o.name == 'HeadSkin':
            wts[o.name] = R.smooth(o, R.weights_for(o, 'neck', hb.LANDMARKS), 3)
        elif o.name.startswith(('Sole', 'Upper', 'Lace', 'Stripe', 'Slipper')):
            wts[o.name] = R.weights_for(o, 'foot', hb.LANDMARKS)
    if hb.SPEC['chest']:
        for n in ('Top', 'BodySkin'):
            wts[n] = [hb.chest_weights(p, w) for p, w in zip(canon[n], wts[n])]
    if FEMALE:                                     # hoodie torso rides the body's own weights (no skin through the back
        t = KDTree(len(canon['BodySkin']))         # when the arms come down); the sleeves keep the rig weights
        for i, p in enumerate(canon['BodySkin']):
            t.insert(p, i)
        t.balance()
        top = bpy.data.objects['Top']
        body_w = transfer(top, canon['BodySkin'], wts['BodySkin'], t)
        mixed = []
        for p, w0, w1 in zip(canon['Top'], wts['Top'], body_w):
            k = hb._ss((0.17 - abs(p.x)) / 0.05)
            m_ = {b: v * (1 - k) for b, v in w0.items()}
            for b, v in w1.items():
                m_[b] = m_.get(b, 0.0) + v * k
            mixed.append(top4(m_))
        wts['Top'] = R.smooth(top, mixed, 2)
    trees = {}
    for n in [x for x in ('Top', 'Pants', 'Overshirt', 'Cardigan') if x in canon]:
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
        elif o.name.startswith(('Hem', 'Collar', 'Cuff', 'Pocket', 'String', 'Aglet', 'Stain')):
            wts[o.name] = [top4(w) for w in transfer(o, canon['Top'], wts['Top'], trees['Top'])]
        elif o.name.startswith('PantCuff'):
            wts[o.name] = [top4(w) for w in transfer(o, canon['Pants'], wts['Pants'], trees['Pants'])]
        elif o.name.startswith('Os'):                                 # overshirt trims ride the overshirt
            wts[o.name] = [top4(w) for w in transfer(o, canon['Overshirt'], wts['Overshirt'], trees['Overshirt'])]
        elif o.name.startswith('Cg'):                                 # cardigan bands, buttons, pockets
            wts[o.name] = [top4(w) for w in transfer(o, canon['Cardigan'], wts['Cardigan'], trees['Cardigan'])]
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
        for _k in hb.CHEST_MOTION:
            fields[_k] = lambda c, _k=_k: hb.chest_motion(c, _k)
    own = {}
    for n in [x for x in ('BodySkin', 'Top', 'Pants', 'Shirt', 'Overshirt', 'Cardigan') if x in canon]:   # smooth fields
        fs = fields
        if n == 'BodySkin' and 'Chest_Size' in fields:                 # bare body: round underside (no bridge)
            fs = dict(fields, Chest_Size=lambda c: hb.bust(c, False)[1],
                      **{k: (lambda c, k=k: hb.chest_motion(c, k, False)) for k in hb.CHEST_MOTION})
        if n == 'Top' and 'Chest_Size' in fields:                      # loose top: falls straight from the bust
            fs = dict(fs, Chest_Size=drape_field(canon[n]))
        chesty = any(hb.bust(c)[0] > 0 for c in canon[n])
        own[n] = {k: [f(c) for c in canon[n]] for k, f in fs.items()
                  if (k != 'Chest_Size' and k not in hb.CHEST_MOTION) or chesty}

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

    for k in ('Chest_Size',) + hb.CHEST_MOTION:               # dense voxel cloth: relax the chest keys (no ripples)
        if k in own['Shirt']:
            own['Shirt'][k] = relax(bpy.data.objects['Shirt'], own['Shirt'][k])
    if 'Chest_Size' in own['Top']:                            # soft round top on the hoodie
        own['Top']['Chest_Size'] = relax(bpy.data.objects['Top'], own['Top']['Chest_Size'], 3)

    def host_of(name):
        if name.startswith(('ShirtCollar', 'ShirtSleeve')):
            return 'Shirt'
        if name.startswith('Os'):
            return 'Overshirt'
        if name.startswith('Cg'):
            return 'Cardigan'
        if name.startswith('Stain'):
            return 'Top'
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
    for _, objs in acc.ACC.values():                    # accessories: rigid parts in character space at rest
        for o in objs:
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
    bpy.context.view_layer.update()
    hat_keys(hair)
    for slot, objs in acc.ACC.values():                  # library hair parts take the hat keys too
        for o in objs:
            if slot == 'hair':
                hat_keys(o, check=False)
    export_all(rig, head, hair, regions, hair_skinned)
    for pid, variant in HEAD_VARIANTS['female' if FEMALE else 'male']:
        head = variant_head(rig, head, pid, variant)


HEAD_VARIANTS = {'male': [('head_roommate', {'jaw': 'square', 'brow': 'straight', 'eye': 0.9, 'smile': 'half'})],
                 'female': [('head_mom', {'jaw': 'round', 'eye': 0.92, 'lines': True})]}


def variant_head(rig, head, pid, variant):
    """Another head part on the same rig from hb.FACE flags (face shape, brows, eyes, mouth): the default head's
    objects are freed first so every face part keeps its contract name (all expressions work unchanged)."""
    root = bpy.data.objects['Character']
    old = [o for o in head.children_recursive if not o.name.startswith(('Hair', 'Acc_'))] + [head]
    old += [o for o in bpy.data.objects if o.name.startswith('HeadSkin') and o not in old]   # skinned: under the rig
    for o in old:
        bpy.data.objects.remove(o, do_unlink=True)
    hb.FACE.clear()
    hb.FACE.update(variant)
    h2 = lib.empty('Face', hb.NECK, root)
    skin = adopt(hb.head_skin(), h2, hb.NECK)
    hb.face(h2, skin)
    k = hb.SPEC['head']
    if k > 1.22:                                         # same neck taper and eye-pivot scale as hb.head_parts
        for v in skin.data.vertices:
            p = G(v.co) + hb.NECK
            g = (1.0 + 0.22 * hb._ss((p.y - 1.43) / 0.07)) / k
            f = g + (1 - g) * hb._ss((p.y - 1.50) / 0.07)
            v.co = B(Vector((p.x * f, p.y, p.z * f)) - hb.NECK)
    if k != 1.0:
        new = hb.HEAD_PIVOT + (hb.NECK - hb.HEAD_PIVOT) * k
        h2.matrix_world = Matrix.Translation(B(new)) @ Matrix.Scale(k, 4)
        bpy.context.view_layer.update()
    hb.matte()
    canon = [G(skin.matrix_world @ v.co) for v in skin.data.vertices]
    w = R.smooth(skin, R.weights_for(skin, 'neck', hb.LANDMARKS), 3)
    inv = skin.matrix_world.inverted()
    for v, c in zip(skin.data.vertices, canon):
        v.co = inv @ B(hb.warp(c))
    R.skin(skin, w, rig)
    if not hb.IDENT:
        h2.matrix_world = Matrix.Translation(B(hb.warp(hb.NECK) - hb.NECK)) @ h2.matrix_world
        bpy.context.view_layer.update()
    for o in list(h2.children_recursive) + [skin]:
        ensure_uvs(o)
    face = list(h2.children_recursive)
    if skin not in face:                                 # skinning parents HeadSkin to the rig
        face.append(skin)
    hidden = [o.name for o in face if o.get('hidden')]
    pdir = os.path.join(ROOT, 'characters', 'parts', pid, 'art')
    _export(os.path.join(pdir, pid + '.glb'), [rig, h2] + face, False)
    _tscn(pdir, pid)
    _json(os.path.join(pdir, 'part.json'), {'slot': 'head', 'attach': 'Head', 'hidden': hidden, 'face': variant,
                                             'expressions': hb.EXPRESSIONS, 'mouths': hb.MOUTHS, 'shut': hb.SHUT})
    hb.FACE.clear()
    print('CHAR_HEAD', pid, variant)
    return h2


def hat_keys(hair, check=True):
    """One hair key per hat (accessories.HATS): hair above that hat's band lies down to `press` off the scalp, so
    the hat (part.json shapes {key: 1}) sits on it; the cap's brim also tucks the fringe. Final space: the head
    scale and neck shift undone for the band test. Then a 3D check per hat: band-to-hair gap and hair poking out."""
    from sculpt import Surface
    skin = Surface(bpy.data.objects['HeadSkin'])
    k, shift = hb.SPEC['head'], hb.warp(hb.NECK) - hb.NECK
    cran = hb.head_xf(hb.CRANIUM)
    mw = hair.matrix_world
    inv = mw.inverted()
    if not hair.data.shape_keys:
        hair.shape_key_add(name='Basis')
    base = [G(mw @ v.co) for v in hair.data.vertices]
    for key, hat in acc.HATS.items():
        sk = hair.shape_key_add(name=key)
        moved = []
        for i, p in enumerate(base):
            c = hb.HEAD_PIVOT + (p - shift - hb.HEAD_PIVOT) / k
            phi = math.atan2(c.x, -c.z)
            low = 0.055 * hb._ss(1 - abs(phi) / 0.9) if key == 'Hair_Hat' else 0.0   # the fringe tucks under the brim
            w = hb._ss((c.y - (acc.band_y(hat, phi) - 0.012 - low)) / 0.03)
            q = p
            if w > 0:
                d = (p - cran).normalized()
                try:
                    loc, nrm = skin.hit(cran + d * 0.5, -d)
                    target = loc + nrm * hat['press'] * k
                    if (p - cran).length > (target - cran).length:
                        q = p.lerp(target, w)
                        sk.data[i].co = inv @ B(q)
                except ValueError:
                    pass
            moved.append((q, w))
        if check:
            hat_check(key, moved, cran)


def hat_check(key, moved, cran):
    """3D proof for a hat (art review rule): hair (keyed) poking out through the hat, and the gap between the band and
    the hair just under it, per azimuth. Prints CLEAR HAT <key> poke N (max mm) gap max mm."""
    from mathutils.bvhtree import BVHTree
    stem = 'cap_driver' if key == 'Hair_Hat' else 'beret'
    objs = acc.ACC[stem][1]
    trees = []
    for o in objs:                                                   # world space (the parts carry a pivot offset)
        o.data.calc_loop_triangles()
        trees.append(BVHTree.FromPolygons([o.matrix_world @ v.co for v in o.data.vertices],
                                          [t.vertices for t in o.data.loop_triangles]))
    pokes, where = [], []
    for q, w in moved:                                               # covered hair: an outward ray meets the hat
        if w < 0.5:
            continue
        d = (q - cran).normalized()
        if not any(t.ray_cast(B(q + d * 0.0005), B(d), 0.3)[0] is not None for t in trees):
            pokes.append(q)
    if os.environ.get('HAT_DEBUG'):
        for q in pokes[:: max(1, len(pokes) // 10)]:
            print('CLEAR POKE %s y %.3f phi %.0f' % (key, q.y, math.degrees(math.atan2(q.x - cran.x, -(q.z - cran.z)))))
    band = [o for o in objs if o.name.endswith(('Band', 'CapBand', 'BeretBand'))]
    gaps = []
    if band:
        bv = [G(band[0].matrix_world @ v.co) for v in band[0].data.vertices]
        hv = [q for q, w in moved]
        from mathutils.kdtree import KDTree
        t = KDTree(len(hv))
        for i, q in enumerate(hv):
            t.insert(q, i)
        t.balance()
        bins = {}
        for v in bv:                                                 # per 5 deg of azimuth: the band's closest point
            a = int((math.degrees(math.atan2(v.x - cran.x, -(v.z - cran.z))) + 180) // 5)
            bins[a] = min(bins.get(a, 1.0), t.find(v)[2])
        gaps = list(bins.values())
    if os.environ.get('HAT_DEBUG'):
        for q, e in sorted(where, key=lambda t: -t[1])[:8] + [t for t in where if t[1] < 0][:4]:
            print('CLEAR POKE %s y %.3f phi %.0f out %.0f mm' % (key, q.y, math.degrees(math.atan2(q.x - cran.x, -(q.z - cran.z))), 1000 * e))
    print('CLEAR HAT %s exposed %d of %d hair verts under it  band-to-hair gap max %.0f mm (median %.0f)' % (
        key, len(pokes), sum(1 for _, w in moved if w >= 0.5), 1000 * max(gaps, default=0),
        1000 * sorted(gaps)[len(gaps) // 2] if gaps else 0))


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
        cases += [('chest1', {'Chest_Size': 1}), ('heavy_chest1', {'Build_Heavy': 1, 'Chest_Size': 1}),
                  ('squash', {'Chest_Size': 1, 'Chest_Squash_L': 1, 'Chest_Squash_R': 1}),
                  ('stretch_heavy', {'Chest_Size': 1, 'Build_Heavy': 1, 'Chest_Stretch_L': 1, 'Chest_Stretch_R': 1}),
                  ('side_slim', {'Chest_Size': 0.8, 'Build_Slim': 1, 'Chest_Side_L': 1, 'Chest_Side_R': 1})]
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


def _fcurve_sets(act):
    if getattr(act, 'fcurves', None) is not None and not getattr(act, 'layers', None):
        yield act.fcurves                                            # legacy action
    for layer in getattr(act, 'layers', []):                         # slotted actions (Blender 4.4+)
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield bag.fcurves


def drop_bones(rig, names):
    """Remove bones from the build rig and their tracks from every clip (base clips key body bones only)."""
    paths = tuple('pose.bones["%s"]' % n for n in names)
    for act in bpy.data.actions:
        for fcs in _fcurve_sets(act):
            for fc in [f for f in fcs if f.data_path.startswith(paths)]:
                fcs.remove(fc)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for n in names:
        rig.data.edit_bones.remove(rig.data.edit_bones[n])
    bpy.ops.object.mode_set(mode='OBJECT')


def export_all(rig, head, hair, regions, hair_skinned=False):
    base = BASE + '_base'
    out = os.path.join(ROOT, 'characters', base, 'art')
    pdir = lambda pid: os.path.join(ROOT, 'characters', 'parts', pid, 'art')
    # hair first: a skinned hair part exports with its own bones, then they leave the rig (bases carry none)
    _export(os.path.join(pdir(HAIR_ID), HAIR_ID + '.glb'), ([rig] if hair_skinned else []) + [hair], False)
    _tscn(pdir(HAIR_ID), HAIR_ID)
    pj = {'slot': 'hair'} if hair_skinned else {'slot': 'hair', 'attach': 'Head'}
    if CURLS:
        pj['bones'] = [{'name': b[0], 'parent': b[4]} for b in part_bones()]
        pj['springs'] = springs()
        drop_bones(rig, [b[0] for b in part_bones()])
        hb.rig_table = _rig_table
    _json(os.path.join(pdir(HAIR_ID), 'part.json'), pj)
    bodies = regions + [o for o in bpy.data.objects if o.name.startswith(('HandL', 'HandR', 'NailsL', 'NailsR'))]
    _export(os.path.join(out, base + '.glb'), [rig] + bodies, True)
    _tscn(out, base)
    accs = {o for _, objs in acc.ACC.values() for o in objs}
    for stem, (slot, objs) in acc.ACC.items():                       # head accessories: one rigid part each
        pid = stem + SFX
        _export(os.path.join(pdir(pid), pid + '.glb'), objs, False)
        _tscn(pdir(pid), pid)
        pj = {'slot': slot, 'attach': 'Head'}
        if slot == 'hat':
            pj['shapes'] = {'Hair_Hat' if stem == 'cap_driver' else 'Hair_Beret': 1.0}
        _json(os.path.join(pdir(pid), 'part.json'), pj)
    face = [o for o in head.children_recursive if o != hair and o not in hair.children_recursive and o not in accs]
    face.append(bpy.data.objects['HeadSkin'])
    hidden = [o.name for o in face if o.get('hidden')]
    hb.rig_json(os.path.join(out, base + '_rig.json'), hidden)    # hidden + expressions: the default head's face parts
    rj = json.load(open(os.path.join(out, base + '_rig.json')))
    rj['first_person'] += ['Body_LowerArmL', 'Body_LowerArmR']      # bare forearms under a T-shirt
    if CURLS:                                                       # part bones are not body bones
        part = {b[0] for b in part_bones()}
        for c in rj['clips'].values():
            c['bones'] = [b for b in c.get('bones', []) if b not in part]
    _json(os.path.join(out, base + '_rig.json'), rj)
    parts = {'head': HEAD_ID, 'hair': HAIR_ID, 'top': ('tshirt' if FEMALE else 'hoodie') + SFX, 'bottom': 'joggers' + SFX, 'shoes': 'sneakers' + SFX}
    colors = dict(COLORS, top=SHIRT[0], rib=SHIRT[1], print=PRINT[0], print_ink=PRINT[1]) if FEMALE else COLORS
    cj = {'parts': parts, 'paint': PAINT, 'colors': colors, 'shapes': {'Build_Slim': 0.0, 'Build_Heavy': 0.0}}
    if hb.SPEC['chest']:
        cj['shapes']['Chest_Size'] = 0.8
        cj['chest'] = {'chains': [['LeftBreast', 'LeftBreast'], ['RightBreast', 'RightBreast']], 'radius': 0.05,
                       'tip_dir': [0, 1, 0], 'tip': 0.25}
    _json(os.path.join(out, 'character.json'), cj)
    # head: skinned neck (HeadSkin) + rigid face parts in character space at rest
    _export(os.path.join(pdir(HEAD_ID), HEAD_ID + '.glb'), [rig, head] + face, False)
    _tscn(pdir(HEAD_ID), HEAD_ID)
    _json(os.path.join(pdir(HEAD_ID), 'part.json'), {'slot': 'head', 'attach': 'Head', 'hidden': hidden,
                                                       'expressions': hb.EXPRESSIONS, 'mouths': hb.MOUTHS, 'shut': hb.SHUT})
    for pid, (slot, prefixes, hides) in PARTS.items():
        objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(prefixes)]
        if not objs:
            continue
        _export(os.path.join(pdir(pid + SFX), pid + SFX + '.glb'), [rig] + objs, False)
        _tscn(pdir(pid + SFX), pid + SFX)
        _json(os.path.join(pdir(pid + SFX), 'part.json'), {'slot': slot, 'hides': hides})
    print('CHAR_BUILT', base, len(regions), 'regions:', ' '.join(sorted(o.name for o in regions)))


PAINT = {'CK2_Print': 'print', 'CK2_PrintInk': 'print_ink', 'CK2_Shirt' + SHIRT[0][1:]: 'top', 'CK2_Rib': 'rib', 'CK2_Skin': 'skin', 'CK2_Hair': 'hair', 'CK2_Brow': 'hair*0.82', 'CK2_Pupil': 'eyes', 'CK2_Blush': 'blush', 'CK2_BlushHot': 'blush*0.88'}
PAINT['CK2_Overshirt'] = 'outer'
PAINT['CK2_HairFade'] = 'skin*0.62'      # clipped fade on curly crops: a skin shadow, any skin tone
PAINT['CK2_CgRib'] = 'outer'               # cardigan knit bands take the outer colour
PAINT['CK2_HairGrey'] = 'hair_grey'        # grey streak bands (bob)
PAINT['CK2_AgeLine'] = 'skin*0.8'         # smile lines on older faces
COLORS = {'skin': hb.SKIN, 'hair': hb.HAIR, 'hair_grey': '#A8A39C', 'eyes': '#2E2624', 'blush': 'auto', 'outer': OVERSHIRT}
for _m, _slot in (('Top', 'top'), ('Pants', 'bottom'), ('PantCuff', 'bottom'), ('Shoe', 'shoes')):
    _key = {'Top': 'top', 'Pants': 'pants', 'PantCuff': 'pants', 'Shoe': 'shoe'}[_m]
    PAINT['CK2_' + _m + hb.COLOURWAYS['A'][_key][1:]] = _slot
COLORS.update(rib=hb.COLOURWAYS['A']['rib'], top=hb.COLOURWAYS['A']['top'], bottom=hb.COLOURWAYS['A']['pants'], shoes=hb.COLOURWAYS['A']['shoe'])

main()
