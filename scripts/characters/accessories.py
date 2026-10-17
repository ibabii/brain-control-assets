"""Head accessories for the S1 cast (character_system_plan.md phase 3): round glasses, a short full beard, the Lady's
beret and the bus driver's peaked cap. Built in canonical head space from the base's own head (scripts/human/build.py
calls `build` through ACCESSORY_HOOK before the head scale), so they ride the head like the hair: rigid parts on
the Head bone. Each hat names its hair key in HATS (build_char.hat_keys presses the hair under it).
"""
import math

import bpy
from mathutils import Vector

import build as hb
import lib
from lib import B, G
from sculpt import meta, ball, chain, ell, solid, adopt, Surface

ACC = {}                 # part stem -> (slot, [objects])
# hair key -> band (front y, drop to the back, tilt down toward the Human's right +X, canonical) and the hair kept
# under the hat (m off the skin): the cap presses it flat, the beret leaves the curls their volume
HATS = {'Hair_Hat': dict(front=1.722, drop=0.034, tilt=0.0, press=0.011),
        'Hair_Beret': dict(front=1.752, drop=0.02, tilt=0.032, press=0.026)}


def band_y(hat, phi):
    return hat['front'] - hat['drop'] * (1 - math.cos(phi)) / 2 - hat['tilt'] * math.sin(phi)


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


def _band(surf, hat, lift, k=72):
    """Points round the head along a hat's band line, lift off the skin (the pressed hair under it)."""
    pts = []
    for i in range(k):
        phi = 2 * math.pi * i / k
        d = Vector((math.sin(phi), 0, -math.cos(phi)))
        loc, nrm = surf.hit(Vector((0, band_y(hat, phi), 0)) + d * 0.4, -d)
        pts.append(loc + Vector((nrm.x, 0, nrm.z)).normalized() * lift)
    return pts


def _loft(name, band, profile, mat, frame=None):
    """Closed crown mesh: rings from the band (scale s about its centre, height h above it, the band's own slope
    fading out by `level`), capped at the top. frame(p, t) can bend the rings (tilt, droop)."""
    c = sum(band, Vector()) / len(band)
    rings = []
    for sc, h, level in profile:
        ring = []
        for p in band:
            q = c + Vector(((p.x - c.x) * sc, (p.y - c.y) * (1 - level) + h, (p.z - c.z) * sc))
            ring.append(frame(q, h) if frame else q)
        rings.append(ring)
    top = c + Vector((0, profile[-1][1] + 0.004, 0))
    top = frame(top, profile[-1][1]) if frame else top
    n = len(band)
    verts = [B(p) for r in rings for p in r] + [B(top)]
    faces = []
    for j in range(len(rings) - 1):
        for i in range(n):
            a, b = j * n + i, j * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    t = len(verts) - 1
    faces += [((len(rings) - 1) * n + i, (len(rings) - 1) * n + (i + 1) % n, t) for i in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    m = o.modifiers.new('Sub', 'SUBSURF')
    m.levels = 2
    for x in bpy.data.objects:
        x.select_set(x == o)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier='Sub')
    for f in o.data.polygons:
        f.use_smooth = True
    o.data.materials.append(mat)
    return o


def beret(surf):
    """The Lady's purple beret (classic French): a soft disc ~1.3x the head's width tilted ~18 deg to her right, the
    rim down on the crown just above the hairline, the overhang drooping over her right temple, a stalk on top."""
    hat = HATS['Hair_Beret']
    band = _band(surf, hat, hat['press'] - 0.004)
    c = sum(band, Vector()) / len(band)
    tilt = math.radians(18)

    def frame(q, h):                                                  # tilt about the band centre, droop on +X
        d = q - c
        x = d.x * math.cos(tilt) + d.y * math.sin(tilt) * (h > 0.0)
        y = d.y * math.cos(tilt) - d.x * math.sin(tilt) * (h > 0.0)
        droop = -0.022 * max(0.0, x / 0.15) ** 1.5 * min(1.0, h / 0.04)
        return c + Vector((x, y + droop, d.z))
    prof = [(1.0, 0.0, 0.0), (1.06, 0.012, 0.3), (1.3, 0.04, 0.7), (1.46, 0.07, 1.0), (1.44, 0.092, 1.0),
            (1.2, 0.112, 1.0), (0.7, 0.124, 1.0), (0.25, 0.128, 1.0)]
    mat = lib.mat('Beret', '#7A4FA0', 0.95)
    out = [_loft('Beret', band, prof, mat, frame)]
    rim = meta('BeretBand', 0.003)                                   # a soft rolled band where it meets the hair
    chain(rim, band + band[:1], 0.007, 0.007, step=0.003)
    out.append(solid('BeretBand', [rim], 0.0025, 3000, mat))
    st = meta('BeretStalk', 0.002)
    tip = frame(c + Vector((0, 0.13, 0)), 0.13)
    chain(st, [tip, tip + Vector((0.004, 0.016, 0.002))], 0.0055, 0.004, step=0.002)
    out.append(solid('BeretStalk', [st], 0.0018, 600, mat))
    return out


def cap(surf):
    """The bus driver's peaked cap: the band round mid-forehead and just above the ears, a crown flaring a little
    wider than the band to a flat top, a big visor angled down ~15 deg, a gold badge at the front."""
    hat = HATS['Hair_Hat']
    band = _band(surf, hat, hat['press'] + 0.002)
    mat = lib.mat('Cap', '#2C3A5A', 0.85)
    prof = [(1.0, 0.0, 0.0), (1.05, 0.035, 0.35), (1.14, 0.08, 0.75), (1.25, 0.12, 1.0), (1.3, 0.14, 1.0),
            (1.26, 0.152, 1.0), (1.0, 0.157, 1.0), (0.3, 0.16, 1.0)]
    out = [_loft('Cap', band, prof, mat)]
    bd = meta('CapBand', 0.003)
    chain(bd, band + band[:1], 0.011, 0.011, step=0.003)
    out.append(solid('CapBand', [bd], 0.0025, 4000, lib.mat('CapVisor', '#1E1E22', 0.5)))
    vis = meta('CapVisor', 0.002)                                     # visor: a half-disc jutting forward, down 15 deg
    front = band[0]
    for i in range(19):
        a = math.pi * i / 18
        for rr in (0.0, 0.016, 0.032, 0.048, 0.064, 0.078):
            w = 0.1 * (1 - 0.35 * rr / 0.078)
            ball(vis, front + Vector((w * math.cos(a), -0.004 - rr * math.sin(a) * 0.27,
                                      -0.004 - rr * math.sin(a))), 0.0065)
    out.append(solid('CapVisor', [vis], 0.0018, 3500, lib.mat('CapVisor', '#1E1E22', 0.5)))
    bg = meta('CapBadge', 0.0015)
    c = sum(band, Vector()) / len(band)
    ball(bg, c + (front - c) * 1.1 + Vector((0, 0.055 - (front.y - c.y) * 0.4, -0.003)), 0.011)   # on the crown
    out.append(solid('CapBadge', [bg], 0.0015, 600, lib.mat('Badge', '#C9A24A', 0.4, metal=0.6)))
    return out


def hair_curly(skin, surf):
    """Short dark curly crop (the roommate; ref_heads_expressions 'male 3'): a round mass of tight clay curls, fuller
    on top, short at the sides and nape; neighbouring curls in different families so each one reads."""
    edge = lambda phi: hb.hairline(phi) + 0.01 + 0.025 * hb._ss((abs(phi) - 1.9) / 0.7)
    shell = hb.scalp_shell(skin, edge, lift=0.003, thick=0.006)
    curls = []                                                       # (centre, radius): real spheres, voxel-unioned
    el0 = lambda phi: math.asin(max(-0.95, min(0.95, (edge(phi) + 0.008 - hb.CRANIUM.y) / 0.15)))
    rows = 9
    for j in range(rows + 1):
        e_mid = el0(0.0) + (math.pi / 2 - el0(0.0)) * j / rows
        ring = max(1, int(46 * math.cos(e_mid)))                       # ~2 cm apart on every row
        for i in range(ring):
            phi = -math.pi + 2 * math.pi * (i + 0.5 * (j % 2)) / ring
            e0 = el0(phi)
            el = e0 + (math.pi / 2 - e0) * j / rows
            d = Vector((math.cos(el) * math.sin(phi), math.sin(el), -math.cos(el) * math.cos(phi)))
            loc, nrm = surf.hit(hb.CRANIUM + d * 0.4, -d)
            top = hb._ss((el - 0.5) / 0.7)                            # fuller on top, short at the sides/back
            back = hb._ss((abs(phi) - 2.0) / 0.8)
            r = 0.012 + 0.003 * top - 0.002 * back
            jit = 0.003 * math.sin(i * 12.9898 + j * 78.233)
            curls.append((loc + nrm * (0.006 + 0.008 * top + jit), r * 1.15))   # every curl stands proud
    import bmesh
    bm = bmesh.new()
    for c, r in curls:
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r, matrix=__import__('mathutils').Matrix.Translation(B(c)))
    me = bpy.data.meshes.new('HairCurly')
    bm.to_mesh(me)
    bm.free()
    hair = bpy.data.objects.new('HairCurly', me)
    bpy.context.scene.collection.objects.link(hair)
    hair.data.materials.append(lib.mat('Hair', hb.HAIR, 0.9))
    return [hb.union_shell(hair, shell, 0.0025, 16000, smooth=1)]


def build(head, skin):
    """ACCESSORY_HOOK: every accessory for this base, adopted under the head empty (they scale with the head)."""
    surf = Surface(skin)
    for stem, slot, objs in (('glasses_round', 'glasses', glasses(surf)), ('beard_full', 'beard', beard(head, surf)),
                             ('beret', 'hat', beret(surf)), ('cap_driver', 'hat', cap(surf)),
                             ('hair_curly', 'hair', hair_curly(skin, surf))):
        for o in objs:
            o.name = 'Acc_' + stem + '_' + o.name
            adopt(o, head, hb.NECK)
        ACC[stem] = (slot, objs)
