"""The Human (the body the brain pilots): style blockout for approval. Brief: docs/human_brief.md.
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/human/build.py
Godot coords throughout (lib convention): feet at the origin, +Y up, faces -Z, the Human's right = +X.
Writes human/art/human.glb (colourway A) and previews/human/human_<id>.glb for every colourway.
Face parts move by node transforms and visibility only (art contract): eyes, lids, brows, mouth set, blush.
"""
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

K = 0.55                                   # metaball surface radius / element radius (stiffness 2), as the hands
SKIN, NAIL = '#F2A99A', '#F5BCAE'          # same skin as the brain's hands
HAIR, BROW = '#6A4636', '#573729'
INK, TONGUE, BLUSH = '#4E2629', '#D9787A', '#E58F86'
# Colourways: top, rib (cuffs/hem/collar), trousers, shoe upper, sole, laces/strings.
COLOURWAYS = {
    'A': dict(top='#D9A04C', rib='#C58E3F', pants='#2D5C5B', shoe='#F8F4EA', sole='#2D5C5B', lace='#2D5C5B'),
    'B': dict(top='#3F6F6C', rib='#355F5C', pants='#D8C7A8', shoe='#F8F4EA', sole='#454C48', lace='#D9A04C'),
    'C': dict(top='#A9584C', rib='#97493F', pants='#454C48', shoe='#F1E4CF', sole='#D9A04C', lace='#F8F4EA'),
}
HAND_SCALE = 1.12                          # on top of the brain hand's own 1.2

# Skeleton-ish landmarks (also the future rig joints).
EYE_Y = 1.625
NECK = Vector((0, 1.47, 0.0))
SHOULDER = Vector((0.20, 1.355, 0.0))
ELBOW = SHOULDER + Vector((math.sin(math.radians(12)), -math.cos(math.radians(12)), 0.0)) * 0.27
FORE = Vector((0.12, -1.0, -0.22)).normalized()
WRIST = ELBOW + FORE * 0.24
HIP = Vector((0.10, 0.82, 0.0))
KNEE = Vector((0.118, 0.46, -0.012))
ANKLE = Vector((0.135, 0.15, 0.0))


def mirror(v, s):
    return Vector((v.x * s, v.y, v.z))


# --- metaball modelling (Godot coords in, Blender elements out) ----------------------------------------

def meta(name, res):
    mb = bpy.data.metaballs.new(name)
    mb.resolution = mb.render_resolution = res
    o = bpy.data.objects.new(name, mb)
    bpy.context.scene.collection.objects.link(o)
    return mb


def ell(mb, c, semi, neg=False):
    r = max(semi) / K
    e = mb.elements.new(type='ELLIPSOID')
    e.co, e.radius = B(c), r
    sx, sy, sz = (s / (K * r) for s in semi)
    e.size_x, e.size_y, e.size_z = sx, sz, sy                  # Godot (x, y, z) semi -> Blender (x, z, y)
    e.use_negative = neg


def cap(mb, a, b, radius):
    a, b = B(a), B(b)
    e = mb.elements.new(type='CAPSULE')
    e.co, e.radius, e.size_x = (a + b) / 2, radius / K, (b - a).length / 2
    e.rotation = Vector((1, 0, 0)).rotation_difference((b - a).normalized())


def ball(mb, c, radius):
    e = mb.elements.new(type='BALL')
    e.co, e.radius = B(c), radius / K


def chain(mb, pts, r0, r1, step=0.006):
    """Tapered clump: balls along a polyline, radius r0 -> r1."""
    pts = [Vector(p) for p in pts]
    total = sum((b - a).length for a, b in zip(pts, pts[1:]))
    s = 0.0
    for a, b in zip(pts, pts[1:]):
        n = max(1, int((b - a).length / step))
        for i in range(n):
            t = (s + (b - a).length * i / n) / total
            ball(mb, a.lerp(b, i / n), r0 + (r1 - r0) * t)
        s += (b - a).length
    ball(mb, pts[-1], r1)


def solid(name, families, voxel, tris, material, smooth_iter=2):
    """Metaball families -> one mesh (voxel union) at about `tris` triangles, as an object at the origin
    (Blender coords, not yet a lib node)."""
    objs = []
    dg = bpy.context.evaluated_depsgraph_get()
    for mb in families:
        src = next(o for o in bpy.data.objects if o.data == mb)
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))
        bpy.data.objects.remove(src, do_unlink=True)
        bpy.data.metaballs.remove(mb)
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        objs.append(o)
    for x in bpy.data.objects:
        x.select_set(x in objs)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.data.remesh_voxel_size = voxel
    bpy.ops.object.voxel_remesh()
    m = o.modifiers.new('Dec', 'DECIMATE')
    m.ratio = min(1.0, tris / max(1, 2 * len(o.data.polygons)))
    bpy.ops.object.modifier_apply(modifier='Dec')
    bm = bmesh.new()
    bm.from_mesh(o.data)
    for _ in range(smooth_iter):
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.4, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()
    for f in o.data.polygons:
        f.use_smooth = True
    o.data.materials.append(material)
    o.name = name
    return o


def adopt(o, parent, pivot):
    """Blender-space object built at the origin -> lib node at `pivot` (Godot), parented, linked to lib.COLL."""
    bpy.context.scene.collection.objects.unlink(o)
    lib.COLL.objects.link(o)
    o.data.transform(Matrix.Translation(-B(pivot)))
    o.matrix_world = Matrix.Translation(B(pivot))
    lib.set_parent(o, parent)
    return o


# --- surface helpers -------------------------------------------------------------------------------------

class Surface:
    """BVH of an object in Godot coords: ray hits and nearest points for placing decals on it."""

    def __init__(self, o):
        mw = o.matrix_world
        me = o.data
        me.calc_loop_triangles()
        self.verts = [G(mw @ v.co) for v in me.vertices]
        self.normals = [(G(mw.to_3x3() @ v.normal)).normalized() for v in me.vertices]
        self.tree = BVHTree.FromPolygons(self.verts, [t.vertices for t in me.loop_triangles])

    def hit(self, start, d):
        loc, n, _, _ = self.tree.ray_cast(Vector(start), Vector(d).normalized(), 1.0)
        if loc is None:
            raise ValueError('decal ray missed at %s' % (tuple(start),))
        if n.dot(Vector(d)) > 0:
            n = -n
        return loc, n

    def front(self, x, y, z0=-0.5):
        """First hit looking from the front (-Z) toward +Z."""
        return self.hit((x, y, z0), (0, 0, 1))


def decal(name, surf, outline, frame, material, parent, offset=0.0012, rings=4, depth=0.0):
    """Flat 2D outline (frame-local XY, frame +Z = into the surface) projected onto `surf`, lifted by `offset`.
    depth > 0 adds a rim down to the surface so it reads as a raised patch."""
    c2 = Vector((sum(p[0] for p in outline) / len(outline), sum(p[1] for p in outline) / len(outline)))
    bm = bmesh.new()
    n = len(outline)
    grid = []
    for r in range(rings + 1):
        t = r / rings
        row = []
        for p in (outline if r else [c2]):
            q = c2.lerp(Vector(p), t)
            start = frame.at((q.x, q.y, -0.2))
            loc, nrm = surf.hit(start, frame.dir((0, 0, 1)))
            row.append(bm.verts.new(loc + nrm * offset))
        grid.append(row)
    for k in range(n):
        bm.faces.new((grid[0][0], grid[1][k], grid[1][(k + 1) % n]))
    for r in range(1, rings):
        for k in range(n):
            bm.faces.new((grid[r][k], grid[r + 1][k], grid[r + 1][(k + 1) % n], grid[r][(k + 1) % n]))
    if depth > 0:
        edge = grid[-1]
        low = []
        for v in edge:
            _, nrm = surf.tree.find_nearest(v.co)[:2]
            low.append(bm.verts.new(v.co - Vector(nrm).normalized() * depth))
        for k in range(n):
            bm.faces.new((edge[k], low[k], low[(k + 1) % n], edge[(k + 1) % n]))
    bm.normal_update()
    # face winding toward the viewer (against the projection direction)
    into = frame.dir((0, 0, 1))
    if sum(f.normal.dot(into) for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return lib.from_bmesh(name, bm, material, parent)


def on_curve(surf, pts2d, frame, lift):
    out = []
    for p in pts2d:
        loc, nrm = surf.hit(frame.at((p[0], p[1], -0.2)), frame.dir((0, 0, 1)))
        out.append(loc + nrm * lift)
    return out


def godot_rot(o, deg):
    """Set a node's rotation as a Godot euler (YXZ, degrees) about its pivot."""
    R = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))           # Godot -> Blender basis
    rb = R @ lib.rot(deg) @ R.inverted()
    loc = o.matrix_world.to_translation()
    o.matrix_world = Matrix.Translation(loc) @ rb.to_4x4()


# --- parts -------------------------------------------------------------------------------------------------

def head_skin():
    mb = meta('HeadSkin', 0.006)
    ell(mb, (0, 1.635, 0.0), (0.128, 0.145, 0.132))               # cranium (top 1.78)
    ell(mb, (0, 1.548, -0.028), (0.112, 0.082, 0.102))            # jaw and chin
    for s in (-1, 1):
        ell(mb, (s * 0.062, 1.565, -0.062), (0.058, 0.048, 0.058))   # round cheeks
    ell(mb, (0, 1.586, -0.137), (0.029, 0.027, 0.027))            # bulb nose
    cap(mb, (0, 1.36, 0.012), (0, 1.50, 0.0), 0.054)               # neck (into the collar)
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
    surf = Surface(head)
    mb = meta('Hair', 0.0055)
    placed = []
    for v, n in zip(surf.verts, surf.normals):
        phi = math.atan2(v.x, -v.z)
        if v.y < hairline(phi) or v.y < 1.45:
            continue
        if abs(v.x) > 0.105 and 1.55 < v.y < 1.66 and -0.03 < v.z < 0.045:           # leave the ears out
            continue
        if any((v - p).length < 0.017 for p in placed):
            continue
        placed.append(v)
        ball(mb, v + n * 0.0045, 0.019)
    # Fringe: clumps from the crown sweeping forward and to the Human's right, tips above the brows.
    for pts, r0, r1 in (
            ([(-0.07, 1.775, -0.04), (-0.01, 1.752, -0.105), (0.045, 1.725, -0.128), (0.085, 1.706, -0.112)], 0.030, 0.015),
            ([(-0.10, 1.755, -0.015), (-0.075, 1.736, -0.095), (-0.035, 1.712, -0.132)], 0.028, 0.014),
            ([(0.02, 1.785, -0.03), (0.075, 1.75, -0.09), (0.112, 1.712, -0.075)], 0.028, 0.014),
            ([(-0.11, 1.735, -0.02), (-0.122, 1.70, -0.075)], 0.022, 0.012)):
        chain(mb, pts, r0, r1)
    # Bedhead cowlick at the back of the crown.
    for tip in ((-0.03, 1.835, 0.09), (0.0, 1.85, 0.075), (0.032, 1.83, 0.095)):     # soft three-tuft cowlick
        chain(mb, [(0.0, 1.77, 0.06), tip], 0.022, 0.011)
    return solid('Hair', [mb], 0.0045, 4500, lib.mat('Hair', HAIR, 0.72))


def top(cw):
    """Sweatshirt: torso + hood family, one family per sleeve (no webbing to the body), unioned."""
    body = meta('TopBody', 0.008)
    ell(body, (0, 1.22, 0.0), (0.185, 0.17, 0.126))               # chest
    ell(body, (0, 1.035, -0.018), (0.192, 0.15, 0.142))           # soft belly
    ell(body, (0, 0.925, 0.0), (0.196, 0.07, 0.136))              # loose hem flare
    cap(body, (-0.15, 1.342, 0.006), (0.15, 1.342, 0.006), 0.066)    # sloped shoulders
    ell(body, (0, 1.425, 0.085), (0.15, 0.07, 0.08))              # bunched hood behind the neck
    fams = [body]
    for s in (-1, 1):
        sl = meta('Sleeve%d' % s, 0.008)
        sh, el, wr = mirror(SHOULDER, s), mirror(ELBOW, s), mirror(WRIST, s)
        ball(sl, sh + Vector((-s * 0.008, -0.01, 0)), 0.064)
        cap(sl, sh, el, 0.063)
        cap(sl, el, wr - mirror(FORE, s) * 0.105, 0.058)            # rounded end stops short of the cuff
        fams.append(sl)
    return solid('Top', fams, 0.006, 5000, lib.mat('Top' + cw['top'][1:], cw['top'], 0.9))


def pants(cw):
    pel = meta('Pelvis', 0.008)
    ell(pel, (0, 0.86, 0.004), (0.178, 0.125, 0.126))
    fams = [pel]
    for s in (-1, 1):
        lg = meta('Leg%d' % s, 0.008)
        h, k, a = mirror(HIP, s), mirror(KNEE, s), mirror(ANKLE, s)
        cap(lg, h, k, 0.084)
        cap(lg, k, a + Vector((0, 0.07, 0)), 0.076)                # rounded end hides inside the cuff
        fams.append(lg)
    return solid('Pants', fams, 0.006, 3500, lib.mat('Pants' + cw['pants'][1:], cw['pants'], 0.88))


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
        o_ = Vector((s, 0, 0))
        o_ = (o_ - d * o_.dot(d)).normalized()                          # back of the hand faces out
        M = Matrix((o_.cross(-d), o_, -d)).transposed()                 # columns: local x, y (back), z (sleeve)
        wr = mirror(WRIST, s)
        for src, m, nm in (('Hand', skin, 'Hand'), ('Nails', nail, 'Nails')):
            o = next(x for x in new if x.name.startswith(src))
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
            bm = bmesh.new()
            bm.from_mesh(me)
            for v in bm.verts:
                v.co = wr + M @ (G(o.matrix_world @ v.co) * HAND_SCALE)
            h = lib.from_bmesh(nm + side.upper(), bm, m, parent, wr)
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


def face(head_node, skin_obj):
    surf = Surface(skin_obj)
    white = lib.mat('EyeWhite', '#F8F4EA', 0.3)
    pupil = lib.mat('Pupil', '#2E2624', 0.3)
    glint = lib.mat('Glint', '#FFFFFF', 0.2)
    skin = lib.mat('Skin', SKIN, 0.55)
    ink = lib.mat('Mouth', INK, 0.7)
    front = Frame((0, 0, 0))                                         # projection along +Z (from the front)
    for s, side in ((-1, 'L'), (1, 'R')):
        hit, _ = surf.front(s * 0.05, EYE_Y)
        e = Vector((s * 0.05, EYE_Y, hit.z + 0.011))
        eye = lib.empty('Eye' + side, e, head_node)
        semi = (0.029, 0.037, 0.024)
        w = lib.sphere('White' + side, 1.0, white, Frame(e), eye, scale=semi, seg=24, rings=14)
        look = lib.empty('Look' + side, e, eye)                       # rotate for gaze
        wsurf = Surface(w)
        p = decal('Pupil' + side, wsurf, ellipse(0.0145, 0.018, 20, -s * 0.003, -0.002), Frame((e.x, e.y, 0)),
                  pupil, look, offset=0.0009)
        g = decal('Glint' + side, wsurf, ellipse(0.0045, 0.0045, 10, -s * 0.003 + 0.006, 0.008), Frame((e.x, e.y, 0)),
                  glint, look, offset=0.0018)
        # Upper lid: closed half-ellipsoid shell around the eye; rotation about X opens (+) / closes (-).
        bm = lib.sphere_bm(1.0, Frame(), tuple(c * 1.13 for c in semi), seg=24, rings=14)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0),
                               plane_no=(0, 1, 0), clear_inner=True)
        edge = [ed for ed in bm.edges if ed.is_boundary]
        bmesh.ops.contextual_create(bm, geom=edge)
        lib.transform_bm(bm, Frame(e))
        lid = lib.from_bmesh('Lid' + side, bm, skin, eye, e)
        godot_rot(lid, (45, 0, 0))
        # Brow: chunky clump on the forehead.
        pts = on_curve(surf, [(s * 0.022, 1.676), (s * 0.05, 1.688), (s * 0.08, 1.678)], front, 0.006)
        lib.tube('Brow' + side, pts, 0.0095, lib.mat('Brow', BROW, 0.75), head_node, res=6, bevel_res=2)
        bl = decal('Blush' + side, surf, ellipse(0.026, 0.016, 18, s * 0.083, 1.567), front,
                   lib.mat('Blush', BLUSH, 0.7), head_node, offset=0.0015)
        bl['hidden'] = True
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


# --- assembly -------------------------------------------------------------------------------------------------

def build(cw_id):
    cw = COLOURWAYS[cw_id]
    lib.reset()
    root = lib.empty('Human', (0, 0, 0))
    body = lib.empty('Body', (0, 0, 0), root)
    head = lib.empty('Head', NECK, root)
    skin = adopt(head_skin(), head, NECK)
    hr = adopt(hair(skin), head, NECK)
    face(head, skin)
    adopt(top(cw), body, (0, 1.1, 0))
    adopt(pants(cw), body, (0, 0.5, 0))
    rib_img = rib_texture(cw['rib'])
    rib = lib.mat('Rib' + cw['rib'][1:], cw['rib'], 0.9, image=rib_img[0], normal=rib_img[1])
    band('Hem', Frame((0, 0.875, 0.0)), 0.188, 0.132, 0.05, 0.04, rib, body)
    top_obj = bpy.data.objects['Top']
    tsurf = Surface(top_obj)

    def collar_lift(a, r=0.082):                                  # sit the collar on the shoulder line
        loc, _ = tsurf.hit((math.sin(a) * r, 1.7, -math.cos(a) * r * 0.95 - 0.004), (0, -1, 0))
        return loc.y - 1.40
    band('Collar', Frame((0, 1.40, -0.004)), 0.076, 0.072, 0.03, 0.16, rib, body, lift=collar_lift)
    for s, side in ((-1, 'L'), (1, 'R')):
        wr = mirror(WRIST, s)
        d = mirror(FORE, s)
        band('Cuff' + side, frame_along(wr - d * 0.042, d), 0.046, 0.046, 0.05, 0.1, rib, body)
        band('PantCuff' + side, Frame(mirror(ANKLE, s) + Vector((0, -0.002, 0))), 0.083, 0.083, 0.05, 0.05,
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
    hands(body)
    lib.count_tris()
    return root


def export(root, path):
    hidden = [o for o in bpy.data.objects if o.get('hidden')]
    for o in bpy.data.objects:
        o.select_set(o == root or o in root.children_recursive)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, use_selection=True,
                              export_cameras=False, export_lights=False, export_extras=True)
    return hidden


def main():
    only = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out_art = os.path.join(lib.ROOT, 'human', 'art')
    out_prev = os.path.join(lib.ROOT, 'previews', 'human')
    os.makedirs(out_art, exist_ok=True)
    os.makedirs(out_prev, exist_ok=True)
    for cw_id in COLOURWAYS:
        if only and cw_id not in only:
            continue
        root = build(cw_id)
        export(root, os.path.join(out_prev, 'human_%s.glb' % cw_id))
        print('HUMAN %s tris=%d' % (cw_id, lib.count_tris()))
        if cw_id == 'A':
            export(root, os.path.join(out_art, 'human.glb'))
            os.makedirs(os.path.join(lib.ROOT, 'source', 'human'), exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(lib.ROOT, 'source', 'human', 'human.blend'))
    print('HUMAN_BUILT')


main()
