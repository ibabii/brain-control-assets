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
    c0 = sum(band, Vector()) / len(band)

    def fwd(q, h):                                                    # the top tilts a little forward (-Z down)
        return q + Vector((0, (q.z - c0.z) * 0.12 * min(1.0, h / 0.05), 0))
    # low crown: up the band's own height, then a flat slightly oval top overhanging ~15% all round
    top = surf.hit(Vector((c0.x, 2.3, c0.z)), Vector((0, -1, 0)))[0].y      # the skull's top over the band centre
    k = max(1.0, (top + hat['press'] + 0.008 - c0.y) / 0.073)              # crown just clears the pressed hair
    prof = [(1.0, 0.0, 0.0), (1.04, 0.025 * k, 0.5), (1.1, 0.045 * k, 1.0), (1.17, 0.056 * k, 1.0),
            (1.18, 0.063 * k, 1.0), (1.12, 0.069 * k, 1.0), (0.85, 0.072 * k, 1.0), (0.3, 0.073 * k, 1.0)]
    print('CLEAR CAP crown %.0f mm over the band centre' % (1000 * 0.073 * k))
    oval = [c0 + Vector(((p.x - c0.x) * 1.06, p.y - c0.y, (p.z - c0.z) * 0.98)) for p in band]
    out = [_loft('Cap', oval, prof, mat, fwd)]
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
    ball(bg, c + (front - c) * 1.06 + Vector((0, 0.03, -0.004)), 0.01)                           # on the crown front
    out.append(solid('CapBadge', [bg], 0.0015, 600, lib.mat('Badge', '#C9A24A', 0.4, metal=0.6)))
    return out


CURL_CLUMPS = [   # (azimuth phi: 0 front / pi back, elevation, radius, lift): ~19 chunky clumps, mixed sizes
    (-0.78, 0.62, 0.026, 0.004), (-0.36, 0.64, 0.031, 0.008), (0.06, 0.66, 0.028, 0.006), (0.45, 0.63, 0.033, 0.01),
    (0.84, 0.6, 0.025, 0.003),                                                       # fringe row, uneven
    (-1.12, 0.95, 0.03, 0.006), (-0.42, 1.04, 0.036, 0.014), (0.36, 1.0, 0.034, 0.012), (1.08, 0.94, 0.029, 0.006),
    (-0.75, 1.32, 0.035, 0.016), (0.18, 1.36, 0.038, 0.018), (0.92, 1.28, 0.032, 0.012),   # fuller top
    (-1.62, 0.78, 0.022, 0.0), (1.6, 0.8, 0.023, 0.001), (-2.2, 0.86, 0.026, 0.004), (2.25, 0.84, 0.027, 0.005),
    (-2.85, 0.92, 0.028, 0.006), (2.8, 0.95, 0.03, 0.007), (3.14, 1.2, 0.031, 0.01),      # back, smaller low down
    (-2.4, 0.5, 0.025, 0.003), (2.45, 0.48, 0.026, 0.003), (-2.95, 0.55, 0.027, 0.004), (2.9, 0.5, 0.026, 0.004),
    (-2.6, 0.12, 0.021, 0.0), (2.65, 0.1, 0.02, 0.0), (3.14, 0.2, 0.023, 0.001),          # down the back to the nape
    (-2.45, -0.25, 0.024, 0.002), (2.5, -0.27, 0.024, 0.002), (-2.9, -0.3, 0.025, 0.002), (2.92, -0.28, 0.025, 0.002),
    (-2.65, -0.6, 0.022, 0.0), (2.7, -0.62, 0.022, 0.0), (3.14, -0.65, 0.023, 0.0),     # distinct clumps down the
    (-2.95, -0.84, 0.019, 0.0), (2.98, -0.83, 0.019, 0.0),                              # back to the nape (Male 3)
]


def hair_curly(skin, surf):
    """Short dark curly crop (the roommate): ~19 chunky clay curl clumps in mixed sizes over a close-cropped base that
    fades at the sides and nape; fuller on top, uneven silhouette. Each clump = a main lump + 3 spiralling sub-lumps."""
    import bmesh
    from mathutils import Matrix
    # edges as scalp elevations (rad): the y-mapped crop at the front and sides, carried down the back of the big
    # cartoon skull to just above the nape curve (probed: el -0.95 ~ y 1.46 on the built head; past ~-1.1 the rays
    # reach the neck and the edge tears)
    el = lambda y: math.asin(max(-0.95, min(0.95, (y - hb.CRANIUM.y) / 0.15)))
    back = lambda phi: hb._ss((abs(phi) - 2.0) / 0.6)                              # 0 at the sides, 1 at the back
    side = lambda phi: hb.hairline(phi) + 0.01 + 0.025 * hb._ss((abs(phi) - 1.9) / 0.7)
    wav = lambda phi, k, a: a * math.sin(k * phi) * hb._ss((abs(phi) - 0.9) / 0.4)   # wavy, not a ruled line
    high = lambda phi: (el(side(phi) + 0.028 * hb._ss((abs(phi) - 1.0) / 0.6)) * (1 - back(phi)) - 0.8 * back(phi))   # the gradient carries on to the nape
    edge = lambda phi: el(side(phi)) * (1 - back(phi)) - 1.02 * back(phi) + wav(phi, 7, 0.03)
    low = lambda phi: edge(phi) - wav(phi, 11, 0.02) - 0.07 * hb._ss((abs(phi) - 0.9) / 0.4)
    shell = hb.scalp_shell(skin, None, lift=0.002, thick=0.005, edge_el=high)
    # clipped sides + nape: one skin-painted shell with a vertex-colour gradient (multiplies the paint): skin at its
    # lower edge, a dark skin shadow under the curls; no steps
    fade = hb.scalp_shell(skin, None, lift=0.0007, thick=0.0012, edge_el=low)
    fade.name = 'HairFade'
    col = fade.data.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    for v, c in zip(fade.data.vertices, col.data):
        d = G(fade.matrix_world @ v.co) - hb.CRANIUM
        e, ph = math.asin(max(-1.0, min(1.0, d.y / d.length))), math.atan2(d.x, -d.z)
        t = hb._ss((e - low(ph)) / max(0.05, high(ph) + 0.05 - low(ph)))
        k = 1 - 0.72 * t                                              # linear: 1 = skin, 0.28 ~ skin*0.56 in sRGB
        c.color = (k, k, k, 1.0)
    m = lib.mat('HairFade', '#FFFFFF', 0.9)
    nt = m.node_tree
    ca = nt.nodes.new('ShaderNodeVertexColor')
    ca.layer_name = 'Col'
    nt.links.new(ca.outputs['Color'], next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'])
    fade.data.materials.clear()
    fade.data.materials.append(m)
    fades = [fade]
    spheres = []

    def on_skull(phi, el):
        d = Vector((math.cos(el) * math.sin(phi), math.sin(el), -math.cos(el) * math.cos(phi)))
        return surf.hit(hb.CRANIUM + d * 0.4, -d)
    for k, (phi, el_, r, lift) in enumerate(CURL_CLUMPS):
        loc, nrm = on_skull(phi, el_)
        t1 = nrm.cross(Vector((0, 1, 0)) if abs(nrm.y) < 0.9 else Vector((1, 0, 0))).normalized()
        t2 = nrm.cross(t1)
        top = hb._ss((el_ - 0.9) / 0.3)                        # flatter on top (~10 % lower silhouette)
        r, lift = r * 0.82 * (1 - 0.2 * top), lift * 0.6 * (1 - 0.95 * top)   # short crop: chunky, not a pompadour
        c = loc + nrm * (r * (0.3 - 0.35 * top - 0.25 * hb._ss(-el_ / 0.4)) + lift)   # sunk on top, a little low down
        spheres.append((c, r))
        a0 = k * 2.1
        for i in range(3):                                     # sub-lumps spiral round and up: a C-curl
            a = a0 + i * 2.2
            rr = r * (0.62 - 0.08 * i)
            rise = (0.05 + 0.12 * i) * (1 - 0.85 * top)
            spheres.append((c + (t1 * math.cos(a) + t2 * math.sin(a)) * r * 0.72 + nrm * r * rise, rr))
    for phi in [i * 0.7 for i in range(-4, 5)] + [2.6, -2.6, 3.14]:   # sunk filler: base volume between the clumps
        for el_ in ((0.85, 1.2) if abs(phi) < 2.0 else (0.85, 1.2, 0.45, 0.05) if abs(phi) < 2.5 else
                    (0.85, 1.2, 0.45, 0.05, -0.35, -0.7)):                     # deep rows only where the mass is
            loc, nrm = on_skull(phi, el_)
            spheres.append((loc - nrm * 0.016, 0.028))
    bm = bmesh.new()
    for c, r in spheres:
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=r, matrix=Matrix.Translation(B(c)))
    me = bpy.data.meshes.new('HairCurly')
    bm.to_mesh(me)
    bm.free()
    hair = bpy.data.objects.new('HairCurly', me)
    bpy.context.scene.collection.objects.link(hair)
    hair.data.materials.append(lib.mat('Hair', hb.HAIR, 0.9))
    return [hb.union_shell(hair, shell, 0.0025, 16000, smooth=2)] + fades


def head_to_world(p):
    """Canonical head space -> the built base (head scale about the eye + the neck warp)."""
    return hb.HEAD_PIVOT + (Vector(p) - hb.HEAD_PIVOT) * hb.SPEC['head'] + (hb.warp(hb.NECK) - hb.NECK)


def world_to_head(p):
    return hb.HEAD_PIVOT + (Vector(p) - (hb.warp(hb.NECK) - hb.NECK) - hb.HEAD_PIVOT) / hb.SPEC['head']


# female base + head_mom + cardigan_f (world, probed): where the head's neck column meets the cardigan, back -> side
COLLAR_LINE = [(0.0, 1.36, 0.122), (0.044, 1.366, 0.106), (0.074, 1.375, 0.073), (0.097, 1.378, 0.03)]


def glasses_halfmoon(surf):
    """Half-moon reading glasses low on the nose (Mom): a flat top across the lower eye, a round bottom rim, thin
    bronze frame, temples back over the ears and a cord from the temple tips round the back of the neck, resting on
    the cardigan collar (COLLAR_BACK)."""
    fams = []
    eyes = [_pos('WhiteL'), _pos('WhiteR')]
    tips = []
    for s, e in zip((-1, 1), eyes):
        mb = meta('MoonRim%d' % (s + 1), 0.0018)
        c = e + Vector((0.0, -0.012, -0.03))
        pts = [c + Vector((0.034 * math.cos(t), -0.028 * math.sin(t), 0)) for t in [math.pi * i / 16 for i in range(17)]]
        chain(mb, pts + [pts[0]], 0.0032, 0.0032, step=0.0018)               # the D: arc + straight top
        fams.append(mb)
        tm = meta('MoonArm%d' % (s + 1), 0.0018)
        a = c + Vector((s * 0.034, 0.0, 0.004))
        arm = [a]
        for z in (0.03, 0.07, 0.1, 0.125):                                 # along the side of the head, over the ear
            loc, n = surf.hit((s * 0.3, 1.648 - 0.25 * max(0.0, z - 0.1), a.z + z), (-s, 0, 0))
            arm.append(loc + n * 0.005)
        chain(tm, arm, 0.0028, 0.0028, step=0.003)
        tips.append(arm[-1])
        fams.append(tm)
    br = meta('MoonBridge', 0.0018)
    l, r = eyes[0] + Vector((0.034, -0.012, -0.03)), eyes[1] + Vector((-0.034, -0.012, -0.03))
    chain(br, [l, (l + r) / 2 + Vector((0, 0.005, -0.004)), r], 0.003, 0.003, step=0.0018)
    fams.append(br)
    frame = solid('GlassesMoon', fams, 0.001, 4000, lib.mat('GlassesBronze', '#8E5B3E', 0.6))
    cord = []                                                # in world: down behind the ear, round the neck on the collar
    for s, t in zip((-1, 1), tips):
        w = head_to_world(t)
        line = []
        for x, y, z in reversed(COLLAR_LINE[1:]):           # side -> back, 5 mm out from the neck, 3 mm up
            out = Vector((x, 0, z - 0.03)).normalized()
            line.append(Vector((s * x, y + 0.003, z)) + Vector((s * out.x, 0, out.z)) * 0.005)
        side = [w, w + Vector((s * 0.004, -0.08, 0.004)), Vector((s * 0.165, 1.47, 0.05))] + line
        cord.append(side if s < 0 else list(reversed(side)))
    back = Vector(COLLAR_LINE[0]) + Vector((0, 0.003, 0.005))
    pts = [world_to_head(q) for q in cord[0] + [back] + cord[1]]
    c = lib.tube('GlassesCord', pts, 0.002, lib.mat('GlassesCord', '#6E4B3A', 0.7), None, res=6, bevel_res=1)
    return [frame, c]


def earrings_pearl(surf):
    """Small pearl studs seated on the earlobes (Mom): the lowest point of each ear, a little to the front."""
    out = []
    pearl = lib.mat('Pearl', '#F3EEE3', 0.6)
    for s in (-1, 1):                                        # on the lobe: the bottom of the ear ellipsoid (hb.head_skin)
        c = Vector((s * 0.149, 1.566, 0.01))
        out.append(lib.sphere('Pearl%d' % (s + 1), 0.0062, pearl, lib.Frame(tuple(c)), None, seg=16, rings=10))
    return out


def hair_bob(skin, surf):
    """Soft wavy bob (Mom, AD FIX): chunky clay locks from the crown down to chin length, waving in and out, tips
    curled under; a side-swept fringe above the brows. Salt-and-pepper (CK2_HairGrey -> slot hair_grey): a narrow grey
    streak sunk along each temple lock and the fringe lock at the part, and a few fine flecks on the back."""
    import bmesh
    from mathutils import Matrix
    edge = lambda phi: hb.hairline(phi) + 0.004
    shell = hb.scalp_shell(skin, edge, lift=0.004, thick=0.01)
    spheres = []                                            # (centre, radius, grey)

    def skin_r(phi, y):                                     # skin distance from the head axis at azimuth phi
        d = Vector((math.sin(phi), 0, -math.cos(phi)))
        try:
            loc, _ = surf.hit(Vector((0, y, 0)) + d * 0.4, -d)
        except ValueError:
            return 0.0
        return Vector((loc.x, 0, loc.z)).length
    part = -0.35                                            # side part on the Human's right
    n = 26
    for i in range(n):
        phi = -math.pi + 2 * math.pi * (i + 0.5) / n
        if abs(phi) < 0.8:
            continue
        grey = 0.8 <= abs(phi) < 1.05                       # temple bands, both sides
        d = Vector((math.sin(phi), 0, -math.cos(phi)))
        y_end = 1.478 + 0.022 * hb._ss((abs(phi) - 2.2) / 0.8)   # chin length, a touch shorter at the nape
        ph = i * 1.9
        pts = []
        top = math.radians(78)                              # over the scalp from the crown to the widest point
        e0 = math.asin(max(-0.95, min(0.95, (edge(phi) - hb.CRANIUM.y) / 0.15))) if abs(phi) < 1.3 else 0.0
        e0 = max(e0, 0.0)
        for k in range(12):
            el = top + (e0 - top) * k / 11
            dd = Vector((math.cos(el) * math.sin(phi), math.sin(el), -math.cos(el) * math.cos(phi)))
            loc, nrm = surf.hit(hb.CRANIUM + dd * 0.4, -dd)
            pts.append(loc + nrm * (0.012 + 0.008 * k / 11))
        y0 = pts[-1].y
        reach = Vector((pts[-1].x, 0, pts[-1].z)).length
        y = y0
        tuck = 1.2 < abs(phi) < 1.9                          # over the ear (azimuth ~1.64): parted round it, lobe shows
        while y > y_end:                                    # hang: never back in past the skin (cheek, ear, jaw)
            y -= 0.006
            if tuck:
                to = 1.3 if abs(phi) < 1.45 else 1.95               # part round the lobe: front lock forward, back ones back
                ph_ = math.copysign(abs(phi) + (to - abs(phi)) * hb._ss((1.7 - y) / 0.06), phi)
                d = Vector((math.sin(ph_), 0, -math.cos(ph_)))
                reach = skin_r(ph_, y) + 0.014 if y > 1.6 else max(reach, skin_r(ph_, y) + 0.014)
            else:
                reach = max(reach, skin_r(phi, y) + 0.014)
            t = (y0 - y) / (y0 - y_end)
            wave = 0.007 * math.sin(2 * math.pi * (y0 - y) / 0.075 + ph) * hb._ss(t / 0.3)
            curl = -0.016 * hb._ss((t - 0.78) / 0.22)       # tips turn under
            pts.append(d * (reach + 0.004 * t + wave + curl) + Vector((0, y, 0)))
        pts.append(d * (reach - 0.012) + Vector((0, y_end + 0.012, 0)))
        L = len(pts)
        for k, c in enumerate(pts):
            t = k / (L - 1)
            r = 0.024 + 0.008 * math.sin(math.pi * min(1.0, t * 1.3)) - 0.006 * hb._ss((t - 0.85) / 0.15)
            spheres.append((c, r, grey))
    # side-swept fringe from the part: three long locks to the Human's left temple, two short ones to the right
    for k, (p1, y1, r0, grey) in enumerate(((1.05, 1.695, 0.028, True), (0.8, 1.70, 0.028, False),
                                            (0.5, 1.703, 0.027, False), (0.2, 1.708, 0.025, False),
                                            (-0.75, 1.70, 0.025, False), (-1.0, 1.69, 0.024, False))):
        p0 = part + 0.1 * (k % 4) if k < 4 else part - 0.05
        for j in range(17):
            t = j / 16
            phi = p0 + (p1 - p0) * t
            yy = 1.80 - (1.80 - y1) * t ** 0.7
            dd = hb.scalp_dir(phi, yy)
            loc, nrm = surf.hit(hb.CRANIUM + dd * 0.4, -dd)
            lift = 0.014 + 0.008 * math.sin(math.pi * t) + 0.003 * math.sin(t * 9 + k)
            spheres.append((loc + nrm * lift, r0 * (1 - 0.3 * t), grey))
    objs = []
    streaks, back, prev = [], 0, None                       # grey locks -> brown + a streak a third as wide on top
    for c, r, g in spheres:
        out = (c - hb.CRANIUM).normalized()
        if g:
            p = (c + out * r * 0.5, r * 0.6)
            if prev and (prev[0] - p[0]).length < 0.03:         # dense along the lock: a smooth streak, not beads
                for t in (0.25, 0.5, 0.75):
                    streaks.append((prev[0].lerp(p[0], t), prev[1] + (p[1] - prev[1]) * t, True))
            streaks.append(p + (True,))
            prev = p
            continue
        elif abs(math.atan2(c.x, -c.z)) > 2.4 and 1.52 < c.y < 1.72:
            back += 1
            if back % 23 == 0:                                  # a few fine flecks on the back
                streaks.append((c + out * r * 0.93, 0.0045, True))
    spheres = [(c, r, False) for c, r, g in spheres] + streaks
    for name, grey, mat in (('HairBob', False, lib.mat('Hair', hb.HAIR, 0.9)),
                            ('HairBobGrey', True, lib.mat('HairGrey', '#8C867F', 0.9))):
        bm = bmesh.new()
        for c, r, g in spheres:
            if g == grey:
                bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=9, radius=r, matrix=Matrix.Translation(B(c)))
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        o.data.materials.append(mat)
        objs.append(o)
    hair = hb.union_shell(objs[0], shell, 0.0025, 18000, smooth=2)
    gr = objs[1]                                            # grey locks: their own clay union, a clean band edge
    gr.data.remesh_voxel_size = 0.0025
    for x in bpy.data.objects:
        x.select_set(x == gr)
    bpy.context.view_layer.objects.active = gr
    bpy.ops.object.voxel_remesh()
    bm = bmesh.new()                                        # soften the streak edges
    bm.from_mesh(gr.data)
    for _ in range(6):
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(gr.data)
    bm.free()
    for f in gr.data.polygons:
        f.use_smooth = True
    return [hair, gr]


def build(head, skin):
    """ACCESSORY_HOOK: every accessory for this base, adopted under the head empty (they scale with the head)."""
    surf = Surface(skin)
    for stem, slot, objs in (('glasses_round', 'glasses', glasses(surf)), ('beard_full', 'beard', beard(head, surf)),
                             ('beret', 'hat', beret(surf)), ('cap_driver', 'hat', cap(surf)),
                             ('hair_curly', 'hair', hair_curly(skin, surf)),
                             ('glasses_halfmoon', 'glasses', glasses_halfmoon(surf)),
                             ('earrings_pearl', 'earrings', earrings_pearl(surf)), ('hair_bob', 'hair', hair_bob(skin, surf))):
        for o in objs:
            o.name = 'Acc_' + stem + '_' + o.name
            if o.name in bpy.context.scene.collection.objects:      # sculpted at the origin
                adopt(o, head, hb.NECK)
            else:                                                   # lib-built (already placed in lib.COLL)
                lib.set_parent(o, head)
        ACC[stem] = (slot, objs)
