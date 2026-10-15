"""Sculpting helpers shared by the character and set builds (Godot coords in, like lib):
metaball families -> voxel-unioned meshes, surface rays, projected decals, curves on surfaces."""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import lib
from lib import B, G, Frame

K = 0.55                                   # metaball surface radius / element radius (stiffness 2)


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
