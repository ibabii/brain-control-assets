"""Shared helpers for the cockpit v2 build. All positions are Godot coordinates (metres, +Y up, camera looks -Z).

Meshes are built in Godot world space, then re-centred on a pivot, so every exported node sits at its pivot
with identity rotation unless stated otherwise.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONCEPT = ROOT + '/concepts/cockpit/cockpit-warm-ceramic-v1.png'
CW, CH = 1672, 941

# Game camera (src/cockpit/cockpit.tscn): position, pitch, vertical FOV.
CAM = Vector((0, 1.36, 0.8))
PITCH = math.radians(-14)
FWD = Vector((0, math.sin(PITCH), -math.cos(PITCH)))
UP = Vector((0, math.cos(PITCH), math.sin(PITCH)))
RIGHT = Vector((1, 0, 0))
TY = math.tan(math.radians(68) / 2)
TX = TY * CW / CH


def B(v):
    """Godot -> Blender."""
    return Vector((v[0], -v[2], v[1]))


def G(v):
    """Blender -> Godot."""
    return Vector((v[0], v[2], -v[1]))


# --- camera projection -------------------------------------------------------------------------

def project(p):
    d = Vector(p) - CAM
    z = d.dot(FWD)
    return (d.dot(RIGHT) / z / TX + 1) / 2 * CW, (1 - d.dot(UP) / z / TY) / 2 * CH


def ray(px, py):
    return (FWD + RIGHT * ((px / CW * 2 - 1) * TX) + UP * ((1 - py / CH * 2) * TY)).normalized()


def unproject(px, py, plane):
    point, normal = plane
    d = ray(px, py)
    t = (Vector(point) - CAM).dot(normal) / d.dot(normal)
    return CAM + d * t


def facing(depth, yaw=0.0, tilt=0.0):
    """Plane facing the camera at `depth` metres along its view axis, optionally turned."""
    n = -FWD
    n = Matrix.Rotation(math.radians(yaw), 3, 'Y') @ Matrix.Rotation(math.radians(tilt), 3, 'X') @ n
    return CAM + FWD * depth, n.normalized()


def zplane(z):
    return Vector((0, 0, z)), Vector((0, 0, 1))


def rot(deg):
    """Godot euler (degrees, YXZ order) -> 3x3 matrix in Godot space."""
    x, y, z = (math.radians(a) for a in deg)
    return Matrix.Rotation(y, 3, 'Y') @ Matrix.Rotation(x, 3, 'X') @ Matrix.Rotation(z, 3, 'Z')


class Frame:
    """Godot-space frame: origin + rotation. Maps local points to world."""

    def __init__(self, origin=(0, 0, 0), deg=(0, 0, 0), parent=None):
        self.m = rot(deg)
        self.o = Vector(origin)
        if parent:
            self.o = parent.at(origin)
            self.m = parent.m @ self.m

    def at(self, p):
        return self.o + self.m @ Vector(p)

    def dir(self, d):
        return self.m @ Vector(d)

    def child(self, origin=(0, 0, 0), deg=(0, 0, 0)):
        return Frame(origin, deg, self)


WORLD = Frame()

# --- colours and materials ----------------------------------------------------------------------

def srgb(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


MATS = {}


def mat(name, color='#ffffff', rough=0.6, metal=0.0, emit=None, strength=1.0, image=None, normal=None,
        normal_strength=1.0, emit_image=None):
    key = 'CK2_' + name
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    rgb = [linear(c) for c in srgb(color)]
    bsdf.inputs['Base Color'].default_value = (*rgb, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    m.diffuse_color = (*rgb, 1)
    if image is not None:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = image
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    if normal is not None:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = normal
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = normal_strength
        nt.links.new(tex.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    if emit_image is not None:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = emit_image
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = strength
    if emit:
        bsdf.inputs['Emission Color'].default_value = (*[linear(c) for c in srgb(emit)], 1)
        bsdf.inputs['Emission Strength'].default_value = strength
    MATS[key] = m
    return m


def image_from_array(name, arr, non_color=False):
    """arr: HxWx3/4 float 0..1, row 0 = top."""
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1))], 2)
    img = bpy.data.images.new(name, w, h, alpha=True)
    if non_color:
        img.colorspace_settings.name = 'Non-Color'
    img.pixels[:] = np.ascontiguousarray(arr[::-1], dtype=np.float32).ravel()
    img.pack()
    return img


_concept = None


def concept_image():
    global _concept
    if _concept is None:
        _concept = bpy.data.images.load(CONCEPT)
        _concept.name = 'ConceptPrint'
        _concept.pack()
    return _concept


def print_mat():
    """Paper/print surfaces textured straight from the approved concept, projected from the game camera."""
    return mat('ConceptPrint', '#ffffff', rough=0.82, image=concept_image())


# --- scene objects -------------------------------------------------------------------------------

COLL = None


def reset():
    global COLL
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    COLL = bpy.data.collections.new('CockpitArt')
    bpy.context.scene.collection.children.link(COLL)


def empty(name, pos=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    COLL.objects.link(o)
    set_parent(o, parent)
    o.matrix_world = Matrix.Translation(B(pos))
    return o


def set_parent(o, parent):
    if parent is not None:
        mw = o.matrix_world.copy()
        o.parent = parent
        o.matrix_world = mw


def from_bmesh(name, bm, material, parent=None, pivot=None, smooth=True, auto_smooth=None):
    """bm vertices are Godot world coords. Node is placed at pivot (default: bounds centre)."""
    if pivot is None:
        lo = Vector([min(v.co[i] for v in bm.verts) for i in range(3)])
        hi = Vector([max(v.co[i] for v in bm.verts) for i in range(3)])
        pivot = (lo + hi) / 2
    pivot = Vector(pivot)
    for v in bm.verts:
        v.co = B(v.co - pivot)
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    if isinstance(material, (list, tuple)):
        for m in material:
            me.materials.append(m)
    else:
        me.materials.append(material)
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    o.matrix_world = Matrix.Translation(B(pivot))
    set_parent(o, parent)
    if smooth and auto_smooth:
        weld_normals(o, auto_smooth)
    return o


def weld_normals(o, angle=40):
    # Sharp edges above `angle` keep hard normals; everything else smooth (applied as split normals).
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    for e in bm.edges:
        e.smooth = not (e.is_manifold and e.calc_face_angle(0) > math.radians(angle))
    bm.to_mesh(me)
    bm.free()


def mesh_object(name, verts, faces, material, parent=None, pivot=None, smooth=False):
    bm = bmesh.new()
    vs = [bm.verts.new(Vector(v)) for v in verts]
    for f in faces:
        bm.faces.new([vs[i] for i in f])
    return from_bmesh(name, bm, material, parent, pivot, smooth)


def transform_bm(bm, frame):
    for v in bm.verts:
        v.co = frame.at(v.co)


# --- primitive builders (local coords, then placed with a Frame) ----------------------------------

def rrect(w, h, r, seg=6):
    """Rounded rectangle outline (CCW) centred on the origin."""
    r = min(r, w / 2 - 1e-4, h / 2 - 1e-4)
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180),
                       (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def circle(r, n=32, cx=0, cy=0):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def slab_bm(outline, thickness, bevel, holes=(), bevel_res=3):
    """Extruded 2D outline with rounded (pillowed) edges. Local: outline in XY, thickness along +Z (0..t)."""
    cu = bpy.data.curves.new('tmp_slab', 'CURVE')
    cu.dimensions = '2D'
    cu.fill_mode = 'BOTH'
    bevel = min(bevel, thickness / 2 - 1e-4)
    cu.extrude = max(thickness / 2 - bevel, 0)
    cu.bevel_depth = bevel
    cu.bevel_resolution = bevel_res
    cu.offset = 0
    for loop in [outline, *holes]:
        sp = cu.splines.new('POLY')
        sp.points.add(len(loop) - 1)
        for p, (x, y) in zip(sp.points, loop):
            p.co = (x, y, 0, 1)
        sp.use_cyclic_u = True
    ob = bpy.data.objects.new('tmp_slab', cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bm = bmesh.new()
    bm.from_mesh(me)
    for v in bm.verts:
        v.co.z += thickness / 2
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    return bm


def slab(name, outline, thickness, bevel, material, frame, parent=None, holes=(), pivot=None, bevel_res=3):
    """Slab lying in frame's XY plane, thickness toward frame +Z (UPF turns +Z to world up)."""
    bm = slab_bm(outline, thickness, bevel, holes, bevel_res)
    transform_bm(bm, frame)
    return from_bmesh(name, bm, material, parent, pivot if pivot is not None else frame.o, smooth=True,
                      auto_smooth=50)


UPF = (-90, 0, 0)   # local +Z -> world +Y; local +Y -> world -Z (away from camera)


def box_bm(size, frame):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    transform_bm(bm, frame)
    return bm


def box(name, size, material, frame, parent=None, bevel=0.0, pivot=None):
    if bevel > 0:
        o = slab(name, rrect(size[0], size[1], bevel * 1.5, 3), size[2], bevel, material,
                 frame.child((0, 0, -size[2] / 2)), parent, pivot=pivot if pivot is not None else frame.o)
        return o
    return from_bmesh(name, box_bm(size, frame), material, parent, pivot if pivot is not None else frame.o,
                      smooth=False)


def sphere_bm(radius, frame, scale=(1, 1, 1), seg=24, rings=14):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1)
    for v in bm.verts:
        v.co = Vector((v.co.x * radius * scale[0], v.co.y * radius * scale[1], v.co.z * radius * scale[2]))
    transform_bm(bm, frame)
    return bm


def sphere(name, radius, material, frame, parent=None, scale=(1, 1, 1), seg=24, rings=14, smooth=True):
    return from_bmesh(name, sphere_bm(radius, frame, scale, seg, rings), material, parent, frame.o, smooth)


def tube(name, points, radius, material, parent=None, res=6, bevel_res=2, smooth=True):
    """Bezier cable through Godot points."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.resolution_u = res
    cu.bevel_depth = radius
    cu.bevel_resolution = bevel_res
    cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = Vector(p)
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new('tmp', cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    return from_bmesh(name, bm, material, parent, None, smooth)


# --- camera-projected print ---------------------------------------------------------------------

def camera_uvs(o):
    """UVs = where each vertex lands in the concept from the game camera."""
    me = o.data
    uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    mw = o.matrix_world
    for loop in me.loops:
        px, py = project(G(mw @ me.vertices[loop.vertex_index].co))
        uv.data[loop.index].uv = (px / CW, 1 - py / CH)


def decal(name, pts, plane, parent=None, cuts=6, offset=0.0, material=None):
    """Flat cut-out whose outline is `pts` (concept pixels), lying on `plane`, textured from the concept."""
    point, normal = plane
    world = [unproject(x, y, plane) + Vector(normal) * offset for x, y in pts]
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in world]
    f = bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=[f])
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bm.normal_update()
    # Face the camera.
    for face in bm.faces:
        if face.normal.dot(Vector(normal)) < 0:
            face.normal_flip()
    o = from_bmesh(name, bm, material or print_mat(), parent, None, smooth=False)
    camera_uvs(o)
    return o


def count_tris():
    t = 0
    for o in COLL.objects:
        if o.type == 'MESH':
            o.data.calc_loop_triangles()
            t += len(o.data.loop_triangles)
    return t
