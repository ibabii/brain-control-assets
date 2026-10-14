"""Modelled props: chunky, smooth, hand-painted textures (ink.py). No concept pixels.

Builders work in a local frame (Godot axes: +Y up, +Z toward the camera) and take the base centre of the object.
Kenney's CC0 food kit was tried for the can, mug and donut; its faceted low-poly look clashed with the concept, so
these are modelled here.
"""
import math

import bmesh
import numpy as np
from mathutils import Vector

import ink
import lib
from lib import Frame

PX = 1600
SPRINKLES = ['#F2D35A', '#5AA2E0', '#7CC46A', '#FFFFFF', '#9A7BD0', '#E8615A']


def face_cam(base, extra=0.0):
    """Frame at `base`, turned about Y so local +Z points at the camera (plus `extra` degrees)."""
    d = lib.CAM - Vector(base)
    return Frame(base, (0, math.degrees(math.atan2(d.x, d.z)) + extra, 0))


def M(name, color, rough=0.6, metal=0.0, **kw):
    return lib.mat('Prop_' + name, color, rough, metal, **kw)


def tex(name, canvas, rough=0.6, emit=None):
    img = lib.image_from_array('Prop_' + name, canvas.image()[..., :3])
    if emit:
        return lib.mat('PropTex_' + name, '#ffffff', rough, image=img, emit_image=img, strength=emit)
    return lib.mat('PropTex_' + name, '#ffffff', rough, image=img)


def obj(name, bm, mats, f, parent, smooth=True):
    lib.transform_bm(bm, f)
    return lib.from_bmesh(name, bm, mats, parent, pivot=f.o, smooth=smooth)


# --- builders (local bmesh with UVs) -------------------------------------------------------------------

def lathe(profile, seg=40, planar=None):
    """Revolve [(r, y, v[, mat])] about +Y. u runs around (0.5 faces +Z), v from the profile.
    planar=R maps UVs from x/z instead (for discs seen from above)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    rings = []
    for p in profile:
        r, y = p[0], p[1]
        rings.append([bm.verts.new((max(r, 1e-5) * math.sin(2 * math.pi * i / seg - math.pi), y,
                                    max(r, 1e-5) * math.cos(2 * math.pi * i / seg - math.pi))) for i in range(seg)])
    for k in range(len(profile) - 1):
        m = profile[k][3] if len(profile[k]) > 3 else 0
        v0, v1 = profile[k][2], profile[k + 1][2]
        for i in range(seg):
            j = (i + 1) % seg
            vs = [rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]]
            try:
                fc = bm.faces.new(vs)
            except ValueError:
                continue
            fc.material_index = m
            u0, u1 = i / seg, (i + 1) / seg
            for loop, (u, v) in zip(fc.loops, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]):
                loop[uv].uv = (loop.vert.co.x / (2 * planar) + 0.5, loop.vert.co.z / (2 * planar) + 0.5) if planar \
                    else (u, v)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def sweep(path, radii, sides=12, squash=1.0):
    """Tube through local points with a radius per point (taper to ~0 to close the ends). v runs along."""
    path = [Vector(p) for p in path]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    n = len(path)
    tang = [(path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized() for i in range(n)]
    ref = Vector((0, 0, 1)) if abs(tang[0].z) < 0.9 else Vector((1, 0, 0))
    side = tang[0].cross(ref).normalized()
    rings = []
    total = sum((path[i + 1] - path[i]).length for i in range(n - 1))
    acc = [0.0]
    for i in range(n - 1):
        acc.append(acc[-1] + (path[i + 1] - path[i]).length)
    for i in range(n):
        side = (side - tang[i] * side.dot(tang[i])).normalized()    # parallel transport
        up = tang[i].cross(side)
        r = max(radii[i], 1e-5)
        rings.append([bm.verts.new(path[i] + side * (r * math.cos(2 * math.pi * k / sides))
                                   + up * (r * squash * math.sin(2 * math.pi * k / sides))) for k in range(sides)])
    for i in range(n - 1):
        for k in range(sides):
            j = (k + 1) % sides
            fc = bm.faces.new([rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]])
            for loop, t in zip(fc.loops, [(k / sides, acc[i] / total), ((k + 1) / sides, acc[i] / total),
                                          ((k + 1) / sides, acc[i + 1] / total), (k / sides, acc[i + 1] / total)]):
                loop[uv].uv = t
    for ring in (rings[0], rings[-1]):
        bm.faces.new(ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def uv_sphere(r, scale=(1, 1, 1), seg=32, rings=18, centre=(0, 0, 0)):
    bm = bmesh.new()
    bm.loops.layers.uv.new('UVMap')
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r, calc_uvs=True)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0], v.co.z * scale[1], -v.co.y * scale[2])) + Vector(centre)
    return bm


def rounded_box(size, r, centre=(0, 0, 0), res=2):
    bm = lib.slab_bm(lib.rrect(size[0], size[1], r, res + 2), size[2], r, bevel_res=res)
    for v in bm.verts:
        v.co = Vector((v.co.x, v.co.y, v.co.z - size[2] / 2)) + Vector(centre)
    return bm


def merge(*bms):
    out = bmesh.new()
    for b in bms:
        me = __import__('bpy').data.meshes.new('tmp')
        b.to_mesh(me)
        out.from_mesh(me)
        __import__('bpy').data.meshes.remove(me)
        b.free()
    return out


def face_card(name, w, h, canvas, f, parent, rough=0.6, emit=None, thick=0.0012, r=0.004):
    """Flat textured panel (labels, screens) on f's XY plane, front at z=0."""
    from paper import card
    return card(name, lib.rrect(w, h, r, 3), thick, f, (w, h), tex(name, canvas, rough, emit), parent)


def screw(name, f, pos, parent, r=0.006):
    bm = lathe([(0, 0, 0), (r, 0, 0), (r, 0.0012, 0), (r * 0.8, 0.0025, 0), (0, 0.0032, 0)], 12)
    for v in bm.verts:
        v.co = Vector((v.co.x, -v.co.z, v.co.y))       # face +Z
    slot_ = rounded_box((r * 1.4, r * 0.3, 0.0012), r * 0.1, (0, 0, 0.0028))
    return obj(name, merge(bm, slot_), [M('Screw', '#A6A9A3', 0.35, 0.7)], f.child(pos), parent)


# --- desk ----------------------------------------------------------------------------------------------

def can(name, base, h, parent):
    """Brain Fuel: red can, scuffed white paint, label with the brain doodle."""
    r = h * 0.34
    f = face_cam(base, 8)
    bm = lathe([(0, 0.025 * h, 0.01, 1), (0.82 * r, 0, 0.01, 1), (0.93 * r, 0.006 * h, 0.01, 1), (r, 0.06 * h, 0.04),
                (r, 0.9 * h, 0.96, 1), (0.86 * r, 0.975 * h, 0.99, 1), (0.89 * r, h, 0.99, 1), (0.81 * r, h, 0.99, 1),
                (0.78 * r, 0.98 * h, 0.99, 1), (0, 0.98 * h, 0.99, 1)], 48)
    cw, ch = int(2 * math.pi * r * PX), int(0.84 * h * PX)
    c = ink.paper(cw, ch, '#D9483F', 21, grain=0.06, vignette=0.0)
    rng = np.random.default_rng(4)
    for _ in range(70):
        c.ellipse((rng.random(), rng.random()), rng.uniform(0.01, 0.05), rng.uniform(0.005, 0.03), '#F4EDE4',
                  rot=rng.uniform(0, 3), opacity=rng.uniform(0.5, 0.95))
    k = c.h / c.w
    c.ellipse((0.5, 0.5), 0.36 * c.w / c.h * 0.42, 0.44, '#F6F0E6', soft=3)
    ink.text(c, 'BRAIN\nFUEL', (0.5, 0.68), 0.19, '#22201E', weight=1)
    ink.brain(c, (0.5, 0.33), 0.22, '#C9475E', '#F4A6B5')
    del k
    obj(name, bm, [tex(name, c, 0.35), M('CanMetal', '#C9CCCC', 0.25, 0.85)], f, parent)
    tab = lib.slab_bm(lib.rrect(r * 0.55, r * 0.3, r * 0.12, 3), 0.0012, 0.0004,
                      holes=[list(reversed(lib.rrect(r * 0.3, r * 0.14, r * 0.06, 3)))], bevel_res=1)
    for v in tab.verts:
        v.co = Vector((v.co.x, h * 0.982 + v.co.z, -v.co.y + r * 0.2))
    obj(name + 'Tab', tab, [M('CanMetal', '#C9CCCC', 0.25, 0.85)], f, parent)
    return f


def mug(name, base, h, parent, handle_side=1):
    """Big cream mug with coffee drips and lettering; handle on the camera's right."""
    r = h * 0.36
    f = face_cam(base, -10)
    t = r * 0.11
    bm = lathe([(0, 0, 0.01), (0.88 * r, 0, 0.01), (r, 0.05 * h, 0.04), (r, 0.94 * h, 0.96), (r - t * 0.2, h, 0.995),
                (r - t * 0.8, h, 0.995), (r - t, 0.95 * h, 0.995), (r - t, 0.9 * h, 0.995, 1),
                (0, 0.9 * h, 0.995, 1)], 56)
    cw, ch = int(2 * math.pi * r * PX * 0.7), int(0.9 * h * PX * 0.7)
    c = ink.paper(cw, ch, '#F4EBDD', 22, grain=0.02, vignette=0.0)
    rng = np.random.default_rng(9)
    for _ in range(16):                       # drips down from the rim
        u = rng.random()
        L = rng.uniform(0.08, 0.45)
        w = rng.uniform(4, 9)
        c.stroke([(u, 1.0), (u + rng.uniform(-0.004, 0.004), 1 - L)], w, '#9A5B2E', 0.85)
        c.ellipse((u, 1 - L), w / c.h * 0.7, w / c.h * 0.9, '#9A5B2E', opacity=0.85)
    c.stroke([(0, 0.985), (1, 0.985)], 10, '#9A5B2E', 0.7)
    ink.text(c, 'SAME\nHUMAN\nDIFFERENT\nMESS', (0.5, 0.5), 0.14, '#22201E', weight=1)
    ink.smiley(c, (0.6, 0.13), 0.1, '#22201E', ring=False)
    obj(name, bm, [tex(name, c, 0.3), M('Coffee', '#3B2416', 0.15)], f, parent)
    s = handle_side
    path = [(s * (r - 0.004), 0.78 * h, 0), (s * (r + 0.12 * h), 0.8 * h, 0), (s * (r + 0.24 * h), 0.68 * h, 0),
            (s * (r + 0.25 * h), 0.42 * h, 0), (s * (r + 0.14 * h), 0.27 * h, 0), (s * (r - 0.004), 0.25 * h, 0)]
    hb = sweep(path, [0.065 * h] * len(path), 14, squash=0.75)
    obj(name + 'Handle', hb, [M('MugGlaze', '#F4EBDD', 0.3)], f, parent)
    return f


def donut(name, base, d, parent, seed=3):
    R, r = 0.3 * d, 0.2 * d
    f = face_cam(base)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    nu, nv = 56, 24
    rng = np.random.default_rng(seed)
    wav = rng.uniform(0, 6.28, 4)

    def edge(a, outer):
        k = sum(math.sin(a * (3 + i) + wav[i]) for i in range(4)) / 4
        return (0.2 + 0.3 * k) if outer else (math.pi + 0.15 + 0.3 * k)

    grid = []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        row = []
        for j in range(nv):
            b = 2 * math.pi * j / nv - math.pi / 2         # -90 deg = bottom
            iced = edge(a, True) < b < edge(a, False)
            rr = r * (1.06 if iced else 1.0)
            x = (R + rr * math.cos(b)) * math.sin(a)
            z = (R + rr * math.cos(b)) * math.cos(a)
            y = r * 0.9 + rr * math.sin(b) * 0.88
            row.append((bm.verts.new((x, y, z)), iced))
        grid.append(row)
    for i in range(nu):
        for j in range(nv):
            q = [grid[i][j], grid[(i + 1) % nu][j], grid[(i + 1) % nu][(j + 1) % nv], grid[i][(j + 1) % nv]]
            fc = bm.faces.new([p[0] for p in q])
            fc.material_index = 1 if sum(p[1] for p in q) >= 3 else 0
            for loop, (ii, jj) in zip(fc.loops, [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]):
                loop[uvl].uv = (ii / nu, jj / nv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for fc in bm.faces:                                     # outward
        ctr = fc.calc_center_median()
        ring = Vector((ctr.x, 0, ctr.z)).normalized() * R + Vector((0, r * 0.9, 0))
        if fc.normal.dot(ctr - ring) < 0:
            fc.normal_flip()
    c = ink.paper(256, 128, '#E2A55C', 30, grain=0.12, vignette=0.0)
    shade = np.clip((c.y / c.h), 0, 1)                      # rows top-down: v high = top of tube
    c.multiply(0.82 + 0.25 * (1 - shade))
    obj(name, bm, [tex(name + 'Dough', c, 0.7), M('Icing', '#F07B9A', 0.28)], f, parent)
    # Sprinkles on the icing, one mesh per colour.
    groups = {col: [] for col in SPRINKLES}
    for k in range(90):
        a = rng.uniform(0, 2 * math.pi)
        b = rng.uniform(edge(a, True) + 0.25, edge(a, False) - 0.25)
        if b < -0.1 or b > math.pi + 0.1:
            continue
        p = Vector(((R + r * 1.07 * math.cos(b)) * math.sin(a), r * 0.9 + r * 1.07 * math.sin(b) * 0.88,
                    (R + r * 1.07 * math.cos(b)) * math.cos(a)))
        nrm = Vector((math.cos(b) * math.sin(a), math.sin(b), math.cos(b) * math.cos(a))).normalized()
        t = nrm.cross(Vector((rng.normal(), rng.normal(), rng.normal()))).normalized() * d * 0.022
        groups[SPRINKLES[k % len(SPRINKLES)]].append(sweep([p - t, p + t], [d * 0.008] * 2, 6))
    for col, parts in groups.items():
        if parts:
            obj(name + 'Sprinkles' + col[1:], merge(*parts), [M('Sprinkle' + col[1:], col, 0.35)], f, parent)
    return f


def crumple(name, base, r, parent, seed):
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r)
    for _ in range(9):                                       # fold planes: flatten one side -> crisp creases
        n = Vector(rng.normal(size=3)).normalized()
        d = rng.uniform(0.35, 0.8) * r
        for v in bm.verts:
            s = v.co.dot(n)
            if s > d:
                v.co -= n * (s - d) * rng.uniform(0.5, 0.9)
    for v in bm.verts:
        v.co *= 1 + rng.uniform(-0.07, 0.07)
        v.co.y *= 0.78
    lo = min(v.co.y for v in bm.verts)
    for v in bm.verts:
        v.co.y -= lo
    return obj(name, bm, [M('CrumplePaper', '#F2EEE6', 0.9)], Frame(base, (0, rng.uniform(0, 360), 0)), parent,
               smooth=False)


def folded_note(name, f, w, h, body, parent, seed, ink_col='#3B2A1E'):
    """Creased paper sheet with lettering (Progress > Perfection)."""
    rng = np.random.default_rng(seed)
    c = ink.paper(int(w * PX), int(h * PX), '#F6F1E7', seed, grain=0.03)
    ink.text(c, body, (0.5, 0.58), 0.17, ink_col)
    ink.heart(c, (0.5, 0.14), 0.12, ink_col)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    nx, ny = 14, 14
    folds = [(Vector(rng.normal(size=2)).normalized(), rng.uniform(-0.3, 0.3), rng.uniform(0.004, 0.01))
             for _ in range(4)]
    vs = [[bm.verts.new(((i / nx - 0.5) * w, (j / ny - 0.5) * h,
                         sum(a * abs((i / nx - 0.5) * n.x + (j / ny - 0.5) * n.y - o) for n, o, a in folds)))
           for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            fc = bm.faces.new([vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]])
            for loop, t in zip(fc.loops, [(i / nx, j / ny), ((i + 1) / nx, j / ny), ((i + 1) / nx, (j + 1) / ny),
                                          (i / nx, (j + 1) / ny)]):
                loop[uv].uv = t
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.0006)
    return obj(name, bm, [tex(name, c, 0.85)], f, parent, smooth=False)


def badge(name, base, d, parent):
    R = d / 2
    bm = lathe([(0, 0, 0.5), (R, 0, 0.5), (R, 0.12 * R, 0.5), (0.97 * R, 0.22 * R, 0.5), (0.8 * R, 0.3 * R, 0.5),
                (0.45 * R, 0.36 * R, 0.5), (0, 0.38 * R, 0.5)], 32, planar=R)
    c = ink.Canvas(128, 128, '#F2C94C')
    c.ellipse((0.42, 0.6), 0.25, 0.2, '#F8DD7A', opacity=0.8, soft=12)
    ink.smiley(c, (0.5, 0.48), 0.62, '#2B2220', w=5, ring=False)
    f = face_cam(base)
    f2 = f.child((0, 0, 0), (-55, 0, 0))                     # tilted up toward the camera
    return obj(name, bm, [tex(name, c, 0.35)], f2, parent)


def lever_box(name, base, w, h, parent):
    """Chunky beige box with two pull levers and taped paper labels."""
    f = face_cam(base, -6)
    d = 0.2
    body = M('LeverBox', '#C9BC9F', 0.62)
    obj(name, rounded_box((w, h, d), 0.018, (0, h / 2, 0)), [body], f, parent)
    obj(name + 'Front', rounded_box((w * 0.92, h * 0.78, 0.012), 0.01, (0, h * 0.5, d / 2)),
        [M('LeverPanel', '#B9AC8E', 0.65)], f, parent)
    for k, (x, knob, label) in enumerate([(-0.22, '#D4473A', 'ANXIETY\nBRAKE\n(PULL)'),
                                          (0.24, '#EAC04A', 'HYPE\nLEVER\n(PULL)')]):
        cx = x * w
        obj(name + 'Slot%d' % k, rounded_box((0.026, 0.02, 0.06), 0.008, (cx, h * 0.97, -0.02)),
            [M('Rubber', '#2F3434', 0.8)], f, parent)
        shaft = lathe([(0, 0, 0), (0.008, 0, 0), (0.008, 0.11, 0), (0, 0.11, 0)], 14)
        obj(name + 'Shaft%d' % k, shaft, [M('Shaft', '#3B4040', 0.4, 0.4)], f.child((cx, h * 0.95, -0.02), (-12, 0, 0)),
            parent)
        kb = lathe([(0, 0, 0), (0.017, 0, 0), (0.022, 0.03, 0), (0.02, 0.06, 0), (0.012, 0.072, 0), (0, 0.074, 0)], 20)
        obj(name + 'Knob%d' % k, kb, [M('Knob' + knob[1:], knob, 0.35)],
            f.child((cx, h * 0.95, -0.02), (-12, 0, 0)).child((0, 0.1, 0)), parent)
        lw, lh = w * 0.36, h * 0.52
        c = ink.paper(int(lw * PX), int(lh * PX), '#F1E3C6', 40 + k, grain=0.04)
        ink.text(c, label, (0.5, 0.52), 0.2, '#2B2220')
        lf = Frame()
        lf.o, lf.m = f.at((cx, h * 0.46, d / 2 + 0.0075)), f.m @ lib.rot((0, 0, (-3, 4)[k]))
        from paper import sheet, tape
        sheet(name + 'Label%d' % k, lf, lw, lh, tex(name + 'Label%d' % k, c, 0.85), parent, corner=0.003)
        tape(name + 'LabelTape%d' % k, lf, (0, lh * 0.48, 0.0003), (0.04, 0.014), 8 - 14 * k, parent, 30 + k)
    for sx in (-1, 1):
        for sy in (0.12, 0.88):
            screw(name + 'Screw', f, (sx * w * 0.44, h * sy, d / 2 + 0.006), parent)
    return f


# --- shelf and trinkets --------------------------------------------------------------------------------

def radio(name, base, w, parent):
    f = face_cam(base)
    h, d = w * 0.48, w * 0.42
    obj(name, rounded_box((w, h, d), h * 0.2, (0, h / 2, 0)), [M('Radio', '#D9A04C', 0.5)], f, parent)
    c = ink.Canvas(int(w * 0.55 * PX * 2), int(h * 0.7 * PX * 2), '#7A5A2E')
    for i in range(9):
        for j in range(5):
            c.ellipse(((i + 0.5) / 9, (j + 0.5) / 5), 0.06, 0.06, '#3B2A1E')
    face_card(name + 'Grille', w * 0.55, h * 0.7, c, f.child((-w * 0.17, h * 0.5, d / 2)), parent, r=0.006)
    for k, x in enumerate((0.27, 0.4)):
        kb = lathe([(0, 0, 0), (h * 0.14, 0, 0), (h * 0.14, h * 0.1, 0), (0, h * 0.1, 0)], 16)
        for v in kb.verts:
            v.co = Vector((v.co.x, -v.co.z, v.co.y))
        obj(name + 'Knob%d' % k, kb, [M('RadioKnob', '#F1E4CF', 0.4)], f.child((w * x, h * 0.5, d / 2)), parent)
    lib.tube(name + 'Antenna', [f.at((w * 0.35, h * 0.95, -d * 0.2)), f.at((w * 0.55, h * 2.6, -d * 0.3))], 0.0016,
             M('Steel', '#B9BDBE', 0.3, 0.8), parent, res=1, bevel_res=1)
    return f


def alien(name, base, h, parent):
    f = face_cam(base)
    g = M('Alien', '#7BC24A', 0.4)
    body = lathe([(0, 0, 0), (0.2 * h, 0, 0), (0.24 * h, 0.12 * h, 0), (0.2 * h, 0.35 * h, 0), (0.12 * h, 0.5 * h, 0),
                  (0, 0.52 * h, 0)], 24)
    head = uv_sphere(0.26 * h, (1.1, 0.9, 1.0), 28, 16, (0, 0.68 * h, 0))
    parts = [body, head]
    for s in (-1, 1):
        parts.append(sweep([(s * 0.17 * h, 0.4 * h, 0.02 * h), (s * 0.27 * h, 0.3 * h, 0.06 * h),
                            (s * 0.3 * h, 0.22 * h, 0.08 * h)], [0.05 * h, 0.045 * h, 0.04 * h], 10))
        parts.append(uv_sphere(0.045 * h, centre=(s * 0.3 * h, 0.21 * h, 0.08 * h), seg=12, rings=8))
        parts.append(sweep([(s * 0.1 * h, 0.85 * h, 0), (s * 0.16 * h, 0.98 * h, -0.02 * h)], [0.015 * h] * 2, 8))
        parts.append(uv_sphere(0.04 * h, centre=(s * 0.16 * h, 1.0 * h, -0.02 * h), seg=12, rings=8))
    obj(name, merge(*parts), [g], f, parent)
    eyes = merge(*[uv_sphere(0.075 * h, (1, 1.25, 0.5), 16, 10, (s * 0.11 * h, 0.7 * h, 0.21 * h)) for s in (-1, 1)])
    obj(name + 'Eyes', eyes, [M('GlossBlack', '#14110F', 0.12)], f, parent)
    obj(name + 'Smile', sweep([(-0.06 * h, 0.56 * h, 0.235 * h), (0, 0.54 * h, 0.245 * h), (0.06 * h, 0.56 * h, 0.235 * h)],
                              [0.008 * h] * 3, 6), [M('AlienMouth', '#2E5A1E', 0.5)], f, parent)
    return f


def valve(name, base, h, parent):
    f = face_cam(base)
    r = h * 0.28
    bm = lathe([(0, 0, 0), (r * 1.2, 0, 0), (r * 1.2, 0.08 * h, 0), (r, 0.12 * h, 0), (r, 0.8 * h, 0),
                (r * 1.1, 0.84 * h, 0), (r * 1.1, 0.9 * h, 0), (r * 0.5, 0.94 * h, 0), (r * 0.5, h, 0), (0, h, 0)], 28)
    obj(name, bm, [M('Valve', '#C9473D', 0.4)], f, parent)
    obj(name + 'Band', lathe([(r * 1.02, 0.5 * h, 0), (r * 1.02, 0.6 * h, 0)], 28),
        [M('ValveBand', '#E9DDBF', 0.6)], f, parent)
    return f


def disco_ball(name, centre, r, parent):
    f = Frame(centre, (0, 20, 0))
    bm = uv_sphere(r, seg=22, rings=14)
    c = ink.Canvas(22 * 8, 14 * 8, '#C9CDD2')
    rng = np.random.default_rng(8)
    for i in range(22):
        for j in range(14):
            c.rgb[j * 8:(j + 1) * 8, i * 8:(i + 1) * 8] = rng.uniform(0.45, 1.0)
            c.rgb[j * 8:(j + 1) * 8, i * 8] = 0.15
            c.rgb[j * 8, i * 8:(i + 1) * 8] = 0.15
    obj(name, bm, [tex(name, c, 0.2)], f, parent, smooth=False)
    obj(name + 'Cap', lathe([(0, r, 0), (r * 0.18, r * 0.98, 0), (r * 0.16, r * 1.12, 0), (0, r * 1.14, 0)], 12),
        [M('Steel', '#B9BDBE', 0.3, 0.8)], f, parent)
    return f


def speaker(name, centre, r, parent):
    f = face_cam(centre)
    f = f.child((0, 0, 0), (90, 0, 0))                     # disc faces the camera
    bm = lathe([(0, 0, 0.5), (r, 0, 0.5), (r, r * 0.25, 0.5), (r * 0.85, r * 0.3, 0.5), (0, r * 0.3, 0.5)], 32,
               planar=r)
    c = ink.Canvas(160, 160, '#3B3A36')
    for k in range(1, 7):
        ink.Canvas.stroke(c, ink._arc(0.5, 0.5, 0.07 * k, 0, 2 * math.pi, 40), 3, '#2A2927')
    c.ellipse((0.5, 0.5), 0.11, 0.11, '#E59A3A')
    c.ellipse((0.5, 0.5), 0.06, 0.06, '#3B3A36')
    return obj(name, bm, [tex(name, c, 0.6)], f, parent)


def meter_box(name, base, w, parent, yaw=0.0):
    """Mental Bandwidth: beige gadget with a label and a nearly empty meter."""
    f = Frame(base, (0, yaw, 0))
    h, d = w * 0.36, w * 0.4
    obj(name, rounded_box((w, h, d), 0.012, (0, h / 2, 0)), [M('Gadget', '#E6DCC6', 0.55)], f, parent)
    c = ink.paper(int(w * 0.92 * PX), int(h * 0.82 * PX), '#E9E0CC', 50, grain=0.03)
    ink.text(c, 'MENTAL\nBANDWIDTH', (0.5, 0.68), 0.3, '#2B2220', weight=1)
    c.stroke([(0.08, 0.24), (0.92, 0.24)], c.h * 0.17, '#2B2E2D')
    c.stroke([(0.1, 0.24), (0.22, 0.24)], c.h * 0.1, '#E2402F')
    face_card(name + 'Face', w * 0.92, h * 0.82, c, f.child((0, h * 0.5, d / 2 + 0.0015)), parent, rough=0.55)
    for sx in (-1, 1):
        screw(name + 'Screw', f, (sx * w * 0.43, h * 0.85, d / 2 + 0.0012), parent, 0.004)
    obj(name + 'Led', uv_sphere(0.005, centre=(w * 0.44, h * 0.12, d / 2 + 0.002), seg=10, rings=6),
        [M('LedGreen', '#6BDC5A', 0.3, emit='#6BDC5A', strength=2.0)], f, parent)
    return f


def cat_tv(name, base, w, parent, yaw=0.0):
    """Little CRT: FEED THE CAT ??? in chalky white on a glowing screen."""
    f = Frame(base, (0, yaw, 0))
    h, d = w * 0.78, w * 0.7
    shell = M('Gadget', '#E6DCC6', 0.55)
    obj(name, rounded_box((w, h, d * 0.6), 0.02, (0, h / 2 + 0.012, d * 0.2)), [shell], f, parent)
    obj(name + 'Back', rounded_box((w * 0.7, h * 0.7, d * 0.45), 0.03, (0, h * 0.5, -d * 0.25)), [shell], f, parent)
    sw, sh = w * 0.68, h * 0.66
    obj(name + 'Bezel', rounded_box((sw + 0.02, sh + 0.02, 0.01), 0.02, (-w * 0.08, h * 0.54, d * 0.5)),
        [M('Bezel', '#3B3F3E', 0.5)], f, parent)
    c = ink.Canvas(int(sw * PX * 1.5), int(sh * PX * 1.5), '#1A2F33')
    c.ellipse((0.5, 0.5), 0.75, 0.6, '#2C5257', soft=30, opacity=0.8)
    ink.text(c, 'FEED\nTHE\nCAT\n???', (0.3, 0.5), 0.17, '#F2F2EA', weight=1)
    ink.cat(c, (0.72, 0.3), 0.3, '#F2F2EA', w=3)
    face_card(name + 'Screen', sw, sh, c, f.child((-w * 0.08, h * 0.54, d * 0.5 + 0.006)), parent, rough=0.45,
              r=0.016)
    for k in range(2):
        kb = lathe([(0, 0, 0), (0.011, 0, 0), (0.011, 0.01, 0), (0, 0.01, 0)], 14)
        for v in kb.verts:
            v.co = Vector((v.co.x, -v.co.z, v.co.y))
        obj(name + 'Knob%d' % k, kb, [M('Bezel', '#3B3F3E', 0.5)], f.child((w * 0.37, h * (0.62 - 0.2 * k), d * 0.5)),
            parent)
    for sx in (-0.3, 0.3):
        obj(name + 'Foot', rounded_box((0.03, 0.012, 0.03), 0.004, (sx * w, 0.006, d * 0.2)),
            [M('Rubber', '#2F3434', 0.8)], f, parent)
    return f


def banana(name, base, h, parent, yaw=0.0):
    """Banana buddy: thumbs up, little blue hat."""
    f = Frame(base, (0, yaw, 0)).child((0, 0, 0), (0, 0, -8))
    n = 14
    path, radii = [], []
    for i in range(n):
        t = i / (n - 1)
        a = (t - 0.5) * 1.1
        path.append((0.38 * h * (1 - math.cos(a)) - 0.05 * h, h * (0.02 + 0.92 * t), 0))
        radii.append(0.15 * h * math.sin(math.pi * (0.06 + 0.88 * t)) ** 0.6)
    bm = sweep(path, radii, 10)
    c = ink.Canvas(64, 256, '#F2C94C')
    for v0, v1 in ((0.0, 0.07), (0.93, 1.0)):
        c.ellipse((0.5, (v0 + v1) / 2), 2, 0.05, '#7A5A2E')
    for k in range(5):
        c.stroke([(k / 5 + 0.1, 0.1), (k / 5 + 0.1, 0.9)], 3, '#D9A93C', 0.5)
    obj(name, bm, [tex(name, c, 0.45)], f, parent)
    fc = Vector((0.0, 0.52 * h, 0.15 * h))
    eyes = merge(*[uv_sphere(0.028 * h, (1, 1.3, 0.6), 12, 8, fc + Vector((s * 0.05 * h, 0.04 * h, -0.005 * h)))
                   for s in (-1, 1)])
    obj(name + 'Eyes', eyes, [M('GlossBlack', '#14110F', 0.12)], f, parent)
    obj(name + 'Smile', sweep([fc + Vector((-0.05 * h, -0.02 * h, -0.006 * h)), fc + Vector((0, -0.055 * h, 0.002 * h)),
                               fc + Vector((0.05 * h, -0.02 * h, -0.006 * h))], [0.01 * h] * 3, 6),
        [M('BananaMouth', '#7A2E22', 0.4)], f, parent)
    top = Vector(path[-2])
    hat = lathe([(0, 0, 0), (0.17 * h, 0, 0), (0.17 * h, 0.015 * h, 0), (0.09 * h, 0.02 * h, 0), (0.085 * h, 0.13 * h, 0),
                 (0, 0.135 * h, 0)], 24)
    obj(name + 'Hat', hat, [M('Hat', '#2F4F8F', 0.55)], f.child(tuple(top - Vector((0, 0.03 * h, 0))), (0, 0, 14)), parent)
    glove = M('Glove', '#F4F0E6', 0.5)
    for s in (-1, 1):
        sh = Vector((s * 0.12 * h + path[6][0], 0.42 * h, 0.02 * h))
        hand = sh + Vector((s * 0.14 * h, 0.06 * h, 0.06 * h))
        obj(name + 'Arm%d' % (s > 0), sweep([sh, (sh + hand) / 2 + Vector((0, -0.03 * h, 0)), hand], [0.018 * h] * 3, 8),
            [M('Arm', '#3B3A36', 0.5)], f, parent)
        g = merge(uv_sphere(0.05 * h, (1, 0.9, 0.9), 14, 10, hand),
                  sweep([hand + Vector((0, 0.03 * h, 0)), hand + Vector((0, 0.1 * h, 0))], [0.02 * h, 0.017 * h], 8))
        obj(name + 'Glove%d' % (s > 0), g, [glove], f, parent)
    return f


def octopus(name, base, w, parent):
    f = face_cam(base)
    rng = np.random.default_rng(12)
    c = ink.Canvas(256, 128, '#35B6AA')
    for _ in range(60):
        c.ellipse((rng.random(), rng.uniform(0.25, 1)), rng.uniform(0.02, 0.05), rng.uniform(0.02, 0.05), '#7B5BB5',
                  opacity=rng.uniform(0.3, 0.7), soft=3)
    obj(name, uv_sphere(0.36 * w, (1, 0.88, 0.95), 36, 20, (0, 0.5 * w, 0)), [tex(name, c, 0.55)], f, parent)
    t = ink.Canvas(64, 128, '#35B6AA')
    yy = t.y / t.h
    t.paint(np.clip((yy - 0.62 + 0.04 * np.sin(t.x / 6)) * 30, 0, 1), '#8E63C9')
    parts = []
    for k in range(7):
        a = math.radians(-150 + 300 * k / 6)
        p = Vector((math.sin(a) * 0.36 * w, 0.1 * w, math.cos(a) * 0.3 * w + 0.04 * w))
        parts.append(uv_sphere(0.13 * w, (1, 0.75, 1.15), 20, 12, p))
    obj(name + 'Tentacles', merge(*parts), [tex(name + 'Tip', t, 0.55)], f, parent)
    eyes = merge(*[uv_sphere(0.045 * w, (1, 1.2, 0.6), 14, 8, (s * 0.11 * w, 0.56 * w, 0.33 * w)) for s in (-1, 1)])
    obj(name + 'Eyes', eyes, [M('GlossBlack', '#14110F', 0.12)], f, parent)
    obj(name + 'Smile', sweep([(-0.05 * w, 0.46 * w, 0.335 * w), (0, 0.43 * w, 0.345 * w), (0.05 * w, 0.46 * w, 0.335 * w)],
                              [0.009 * w] * 3, 6), [M('OctoMouth', '#1C3B38', 0.5)], f, parent)
    return f


PIXEL_PAL = [
    # (x0, x1, y0, y1, z0, z1, colour) in voxels; figure 10 wide, 18 tall, 4 deep
    (2, 4, 0, 1, 0, 4, '#5A3A22'), (6, 8, 0, 1, 0, 4, '#5A3A22'),            # boots
    (2, 4, 1, 5, 0, 3, '#2F4E86'), (6, 8, 1, 5, 0, 3, '#2F4E86'),            # legs
    (2, 8, 5, 6, 0, 3, '#E8B84A'),                                           # belt
    (2, 8, 6, 10, 0, 3, '#3A63A8'), (4, 6, 8, 10, 2.6, 3.05, '#E8B84A'),     # shirt + collar
    (0, 2, 6, 10, 0.5, 2.5, '#3A63A8'), (8, 10, 6, 10, 0.5, 2.5, '#3A63A8'),  # arms
    (0, 2, 5, 6, 0.5, 2.5, '#F2C29A'), (8, 10, 5, 6, 0.5, 2.5, '#F2C29A'),    # hands
    (2, 8, 10, 16, -0.5, 3.5, '#F2C29A'),                                    # head
    (1.6, 8.4, 15, 18, -0.9, 3.9, '#8A5A3A'), (1.6, 3, 12, 15, -0.9, 2, '#8A5A3A'),
    (7, 8.4, 12, 15, -0.9, 2, '#8A5A3A'), (3, 6, 18, 19, 0, 3, '#8A5A3A'),     # hair
    (3, 4, 13, 14, 3.5, 3.62, '#1E1A18'), (6, 7, 13, 14, 3.5, 3.62, '#1E1A18'),  # eyes
    (4, 6, 11, 11.5, 3.5, 3.62, '#B3473F'),                                  # mouth
]


def pixel_pal(name, base, h, parent):
    f = face_cam(base)
    v = h / 19
    groups = {}
    for x0, x1, y0, y1, z0, z1, col in PIXEL_PAL:
        size = ((x1 - x0) * v, (y1 - y0) * v, (z1 - z0) * v)
        ctr = ((x0 + x1) / 2 * v - 5 * v, (y0 + y1) / 2 * v, (z0 + z1) / 2 * v - 1.5 * v)
        groups.setdefault(col, []).append(rounded_box(size, min(size) * 0.12, ctr, 1) if min(size) > v * 0.3 else
                                          lib.box_bm(size, Frame(ctr)))
    for col, parts in groups.items():
        obj(name + col[1:], merge(*parts), [M('Voxel' + col[1:], col, 0.55)], f, parent, smooth=False)
    return f


# --- books ---------------------------------------------------------------------------------------------

def book(name, x0, x1, y, h, z_front, depth, color, title, parent, seed, label_x0=None):
    """Hardback lying flat, spine toward the camera, from x0 (left) to x1. Page block shows at the ends and back."""
    L = x1 - x0
    t = h * 0.13
    f = Frame(((x0 + x1) / 2, y, z_front - depth / 2))
    cover = M('BookCover' + color[1:], color, 0.62)
    # U-shaped cover, spine at +Z: outline in local (z, y), extruded along X.
    out = [(depth / 2 - h * 0.25, h / 2), (-depth / 2, h / 2), (-depth / 2, h / 2 - t), (depth / 2 - h * 0.3, h / 2 - t),
           (depth / 2 - h * 0.3, -h / 2 + t), (-depth / 2, -h / 2 + t), (-depth / 2, -h / 2),
           (depth / 2 - h * 0.25, -h / 2)]
    arc = [(depth / 2 - h * 0.25 + h * 0.25 * abs(math.cos(a)) ** 0.35, h / 2 * math.copysign(abs(math.sin(a)) ** 0.8, a))
           for a in np.linspace(-math.pi / 2, math.pi / 2, 13)[1:-1]]
    outline = out[:7] + [out[7]] + arc + [out[0]]
    bm = lib.slab_bm(outline[:-1], L, 0.002, bevel_res=1)
    for v in bm.verts:
        v.co = Vector((v.co.z - L / 2, v.co.y, v.co.x))
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])      # the axis swap mirrored it
    obj(name, bm, [cover], f, parent)
    pages = rounded_box((L - 0.008, h - 2 * t + 0.001, depth - h * 0.3 - 0.004), 0.002, (0, 0, -h * 0.15 - 0.004))
    obj(name + 'Pages', pages, [M('Pages', '#EFE4CC', 0.85)], f, parent)
    if title is not None:
        sw, sh = x1 - 0.012 - max(x0 + 0.01, label_x0 if label_x0 is not None else x0), h * 0.8
        c = ink.Canvas(int(sw * PX), max(int(sh * PX), 24), color)
        c.multiply(np.ones((c.h, c.w)) * 0.98)
        for u in (0.04, 0.96):
            c.stroke([(u, 0.05), (u, 0.95)], 3, '#E9C77A', 0.9)
        if title:
            ink.text(c, title, (0.5, 0.5), 0.62, '#F3DFAE', weight=1.5)
        lf = f.child((x1 - (x0 + x1) / 2 - sw / 2 - 0.012, 0, depth / 2 + 0.0026))
        face_card(name + 'Spine', sw, sh, c, lf, parent, rough=0.6, thick=0.0006, r=0.002)
    return f
