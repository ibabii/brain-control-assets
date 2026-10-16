"""Head accessories for the S1 cast (character_system_plan.md phase 3): round glasses, a short full beard, the Lady's
beret and the bus driver's peaked cap. Built in canonical head space from the base's own head (scripts/human/build.py
calls `build` through ACCESSORY_HOOK before the head scale), so they ride the head like the hair: rigid parts on
the Head bone. Hats also leave `HAT_BAND` for the hair's Hair_Hat key (hair flattens under a hat)."""
import math

import bpy
from mathutils import Vector

import build as hb
import lib
from lib import B, G
from sculpt import meta, ball, chain, ell, solid, adopt, Surface

ACC = {}                 # part stem -> (slot, [objects])
HAT_BAND = 1.765         # canonical height of a hat's band at the front (it tilts down 0.02 toward the back)


def _pos(name):
    return G(bpy.data.objects[name].matrix_world.translation)


def _ring(mb, c, n, rad, r, k=48, sx=1.0):
    """Clay ring of tube radius r round centre c in the plane with normal n."""
    u = n.cross(Vector((0, 1, 0))).normalized()
    v = n.cross(u).normalized()
    pts = [c + (u * math.cos(t) * sx + v * math.sin(t)) * rad for t in [2 * math.pi * i / k for i in range(k + 1)]]
    chain(mb, pts, r, r, step=0.0025)


def glasses(surf):
    """Round, thick, dark frames (ref_heads_expressions: male 2): a ring round each eye, a bridge, temples to the ears."""
    fams = []
    eyes = [_pos('WhiteL'), _pos('WhiteR')]
    for s, e in zip((-1, 1), eyes):
        mb = meta('GlassRim%d' % (s + 1), 0.002)
        n = Vector((s * 0.18, 0.0, -1.0)).normalized()               # faces a little outward, like the face
        c = e + Vector((0.0, 0.002, -0.022))
        _ring(mb, c, n, 0.047, 0.0055)
        fams.append(mb)
        tm = meta('GlassArm%d' % (s + 1), 0.002)                    # temple: straight back from the rim's outer
        a = c + Vector((s * 0.047, 0.006, 0.006))                    # edge into the hair (no stick past the cheek)
        chain(tm, [a, a + Vector((-s * 0.004, -0.003, 0.12))], 0.0042, 0.0042, step=0.003)
        fams.append(tm)
    br = meta('GlassBridge', 0.002)                                 # bridge: an arch over the nose
    l, r = eyes[0] + Vector((0.047 * 0.9, 0.008, -0.026)), eyes[1] + Vector((-0.047 * 0.9, 0.008, -0.026))
    mid = (l + r) / 2 + Vector((0, 0.008, -0.004))
    chain(br, [l, mid, r], 0.0045, 0.0045, step=0.002)
    fams.append(br)
    return [solid('Glasses', fams, 0.0012, 5000, lib.mat('Glasses', '#2A2422', 0.6))]


def beard(head, surf):
    """Short full clay beard (ref: Male 4 / Bearded male): chin and jaw from ear to ear, up the cheeks to the
    sideburns, and a moustache; the mouth stays clear (it animates)."""
    mouth = _pos('Smile')
    mb = meta('Beard', 0.004)
    placed = []
    for v, n in zip(surf.verts, surf.normals):
        if v.z > 0.02 or v.y > mouth.y + 0.035:
            continue
        dx = abs(v.x)
        jaw_top = mouth.y + 0.03 - 0.0 * dx                            # cheeks up to about the mouth corner line
        if v.y > jaw_top and dx < 0.1:
            continue
        if dx < 0.034 and mouth.y - 0.022 < v.y < mouth.y + 0.035:      # the mouth stays clear
            continue
        if v.y < mouth.y - 0.11 or (v.z > -0.04 and v.y < mouth.y - 0.07):   # stops under the jaw (not the neck)
            continue
        if any((v - p).length < 0.009 for p in placed):
            continue
        placed.append(v)
        ball(mb, v + n * 0.004, 0.0095)
    fams = [mb]
    mo = meta('Moustache', 0.003)                                     # two rounded wings over the mouth
    for s in (-1, 1):
        pts = []
        for i in range(7):
            t = i / 6
            q = Vector((s * (0.004 + 0.042 * t), mouth.y + 0.026 - 0.016 * t * t, -0.3))
            loc, nrm = surf.hit(q, Vector((0, 0, 1)))
            pts.append(loc + nrm * 0.008)
        chain(mo, pts, 0.011, 0.007, step=0.0025)
    fams.append(mo)
    return [solid('Beard', fams, 0.0025, 7000, lib.mat('Hair', hb.HAIR, 0.9))]


def _band(surf, y_front, drop, lift, k=72):
    """Points round the head at the hat line (front y_front, back y_front - drop), lift off the skin."""
    pts = []
    for i in range(k + 1):
        phi = 2 * math.pi * i / k
        y = y_front - drop * (1 - math.cos(phi)) / 2
        d = Vector((math.sin(phi), 0, -math.cos(phi)))
        loc, nrm = surf.hit(Vector((0, y, 0)) + d * 0.4, -d)
        pts.append(loc + Vector((nrm.x, 0, nrm.z)).normalized() * lift)
    return pts


def beret(surf):
    """The Lady's purple beret: a wide soft disc slouched down to her right over a snug band, a tiny stalk on top."""
    band = _band(surf, HAT_BAND, 0.02, 0.02)
    c = sum(band, Vector()) / len(band)
    mb = meta('BeretBand', 0.003)
    chain(mb, band, 0.009, 0.009, step=0.003)
    top = meta('BeretTop', 0.004)
    ctr = c + Vector((0.012, 0.042, 0.006))
    ell(top, ctr, (0.098, 0.026, 0.098))
    for i in range(16):                                               # the rim: a soft roll, lower on the slouch side
        a = 2 * math.pi * i / 16
        h = -0.012 * math.cos(a) + 0.004
        ball(top, ctr + Vector((0.098 * math.cos(a), h, 0.1 * math.sin(a))), 0.026)
    stalk = meta('BeretStalk', 0.002)
    chain(stalk, [ctr + Vector((-0.004, 0.024, 0)), ctr + Vector((0.0, 0.042, 0.004))], 0.0055, 0.004, step=0.002)
    return [solid('Beret', [mb, top, stalk], 0.0025, 6000, lib.mat('Beret', '#7A4FA0', 0.9))]


def cap(surf):
    """The bus driver's peaked cap: a crown flaring to a flat round top, a band, a black visor and a gold badge."""
    band = _band(surf, HAT_BAND, 0.02, 0.022)
    c = sum(band, Vector()) / len(band)
    mb = meta('CapBand', 0.003)
    chain(mb, band, 0.013, 0.013, step=0.003)
    crown = meta('CapCrown', 0.004)
    ell(crown, c + Vector((0, 0.03, 0.006)), (0.1, 0.035, 0.108))          # the body over the band
    ell(crown, c + Vector((0, 0.062, -0.004)), (0.118, 0.018, 0.122))      # the wide flat top, a little forward
    caps = [solid('Cap', [mb, crown], 0.0025, 6000, lib.mat('Cap', '#2C3A5A', 0.85))]
    vis = meta('CapVisor', 0.002)                                     # visor: a half-disc jutting forward, tilted down
    front = band[0]
    for i in range(15):
        a = math.pi * i / 14
        for rr in (0.0, 0.015, 0.03, 0.045, 0.058):
            ball(vis, front + Vector((0.07 * math.cos(a) * (1 - 0.3 * rr / 0.058), -0.006 - rr * 0.32,
                                      -0.006 - rr * (0.4 + 0.6 * math.sin(a)))), 0.007)
    caps.append(solid('CapVisor', [vis], 0.0018, 3000, lib.mat('CapVisor', '#1E1E22', 0.5)))
    bd = meta('CapBadge', 0.0015)
    ball(bd, front + Vector((0, 0.022, -0.012)), 0.011)
    caps.append(solid('CapBadge', [bd], 0.0015, 600, lib.mat('Badge', '#C9A24A', 0.4, metal=0.6)))
    return caps


def build(head, skin):
    """ACCESSORY_HOOK: every accessory for this base, adopted under the head empty (they scale with the head)."""
    surf = Surface(skin)
    for stem, slot, objs in (('glasses_round', 'glasses', glasses(surf)), ('beard_full', 'beard', beard(head, surf)),
                             ('beret', 'hat', beret(surf)), ('cap_driver', 'hat', cap(surf))):
        for o in objs:
            o.name = 'Acc_' + stem + '_' + o.name
            adopt(o, head, hb.NECK)
        ACC[stem] = (slot, objs)
