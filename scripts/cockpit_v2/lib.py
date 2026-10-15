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


def on_surface(obj, frame, sink=0.0006):
    """frame moved along its +Z onto obj's surface (ray from above), sunk slightly so curved tops leave no gap."""
    from mathutils.bvhtree import BVHTree
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    t = BVHTree.FromObject(obj, dg)
    inv = obj.matrix_world.inverted()
    n = frame.dir((0, 0, 1)).normalized()
    start = inv @ B(frame.o + n * 0.05)
    hit = t.ray_cast(start, (inv.to_3x3() @ B(-n)).normalized(), 0.1)
    if hit[0] is None:
        raise ValueError('no surface under %s on %s' % (tuple(frame.o), obj.name))
    out = Frame()
    out.m = frame.m
    out.o = frame.o + n * (0.05 - hit[3] - sink)
    return out

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
    """The approved concept, only for the look-dev preview screens (never in the shipped art)."""
    global _concept
    if _concept is None:
        _concept = bpy.data.images.load(CONCEPT)
        _concept.name = 'ConceptPrint'
        _concept.pack()
    return _concept


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


def _area(loop):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1])) / 2


def _inset(loop, d, sign):
    """Move each point `d` to the left of the loop direction (into the solid for CCW outlines and CW holes)."""
    if d <= 0:
        return list(loop)
    n = len(loop)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(loop[i - 1]), Vector(loop[i]), Vector(loop[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0, n1 = Vector((-e0.y, e0.x)) * sign, Vector((-e1.y, e1.x)) * sign
        m = n0 + n1
        m = m.normalized() if m.length > 1e-9 else n1
        out.append(tuple(p1 + m * (d / max(m.dot(n1), 0.3))))
    # Corner arcs no wider than the inset collapse onto one point: drop the duplicates.
    clean = [q for i, q in enumerate(out) if (Vector(q) - Vector(out[i - 1])).length > 1e-5]
    return clean if len(clean) >= 3 else out


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
    # The bevel grows the outline by `bevel`; inset first so the finished slab matches the outline exactly.
    outline = list(outline)
    sign = 1 if _area(outline) > 0 else -1
    outline, holes = _inset(outline, bevel, sign), [_inset(h, bevel, sign) for h in holes]
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


# --- tape -----------------------------------------------------------------------------------------

def tape_mat():
    """Masking tape: warm beige, a bit darker than paper, slightly see-through."""
    m = mat('MaskingTape', '#CBB98E', 0.5)
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Alpha'].default_value = 0.8
    m.surface_render_method = 'BLENDED'
    return m


def tape_strip(name, frame, size, parent, seed=0, nx=14, ny=4):
    """Flat tape strip on frame's XY plane (torn ends); conform_tapes() later drapes it onto what is under it."""
    rng = np.random.default_rng(abs(int(seed)))
    w, h = size
    tear = [rng.uniform(-0.003, 0.003, ny + 1) for _ in range(2)]
    bm = bmesh.new()
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u = i / nx
            x = -w / 2 + w * u + (tear[0][j] * (1 - u) + tear[1][j] * u if i in (0, nx) else 0.0)
            row.append(bm.verts.new((x, -h / 2 + h * j / ny, 0.0)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    transform_bm(bm, frame)
    o = from_bmesh(name, bm, tape_mat(), parent, pivot=frame.o, smooth=True)
    o['tape_normal'] = list(B(frame.dir((0, 0, 1))))
    o['tape_axis'] = list(B(frame.dir((1, 0, 0))))
    o['tape_centre'] = list(B(frame.o))
    o['tape_seed'] = abs(int(seed))
    return o


def _orient(nrm, outside):
    return nrm if nrm.dot(outside) >= 0 else -nrm


def _walk(t, start, n0, d0, length, step=0.0015, hug=0.0012):
    """Roll the tape centre line from `start` along `d0` like pressing tape down: each step turns the direction (in
    the plane of travel and normal) by the smallest angle that keeps the tape on a surface, so it folds over convex
    edges and into concave corners and never jumps a gap. With no surface in reach the end hangs on straight.
    Returns [(s, point, normal, tangent)]."""
    from mathutils import Matrix
    p, nrm, d = start + n0 * 0.0002, n0, d0              # start just above the surface: 'outside' must be known
    out = [(0.0, p, nrm, d)]
    s_ = 0.0
    angles = [0]
    for k in range(1, 7):
        angles += [12 * k, -12 * k]                        # + folds over (toward -normal), - climbs a corner
    while s_ < length:
        axis = d.cross(-nrm).normalized()
        found = None
        for ang in angles:
            dd = Matrix.Rotation(math.radians(ang), 3, axis) @ d
            if dd.dot(d0) < -0.1:                          # tape can't fold back on itself
                continue
            q = p + dd * step
            loc, m, _, dist = t.find_nearest(q, hug * 3)
            if loc is None:
                continue
            m = _orient(m, p - loc)                        # mesh normals aren't reliable: outside = where we came from
            if (q - loc).dot(m) < -1e-5 and dist > 1e-4:   # crossed into the surface
                continue
            if dist <= hug:
                found = (loc + m * 0.0002, m, dd)
                break
        if found is None:
            q = p + d * step
            p, s_ = q, s_ + step
            out.append((s_, p, nrm, d))
            continue
        q, m, dd = found
        d = (q - p).normalized()
        p, nrm = q, m
        s_ += step
        out.append((s_, p, nrm, d))
    return out


def _at(path, s_):
    for (s0, p0, n0, d0), (s1, p1, n1, d1) in zip(path, path[1:]):
        if s1 >= s_:
            f = (s_ - s0) / max(s1 - s0, 1e-9)
            return p0.lerp(p1, f), n0.lerp(n1, f).normalized(), d0.lerp(d1, f).normalized()
    s0, p0, n0, d0 = path[-1]
    return p0 + d0 * (s_ - s0), n0, d0


def conform_tapes(offset=0.0005):
    """Apply every tape strip like real tape: pressed on at its middle, then smoothed outward along its length over
    the surfaces it meets, dropping onto lower surfaces and folding round rims and bezel edges (never floating)."""
    from mathutils.bvhtree import BVHTree
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    tapes = [o for o in COLL.all_objects if 'tape_normal' in o]
    verts, tris = [], []
    for o in COLL.all_objects:
        if o.type != 'MESH' or 'tape_normal' in o or 'Preview' in o.name:
            continue
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        me.calc_loop_triangles()
        base = len(verts)
        mw = o.matrix_world
        verts += [mw @ v.co for v in me.vertices]
        tris += [tuple(base + i for i in lt.vertices) for lt in me.loop_triangles]
        e.to_mesh_clear()
    t = BVHTree.FromPolygons(verts, tris)
    # BVH queries break ties (concave corners, shared edges) differently per build, so a walk can come out a little
    # different each time. Cache each strip's result by its inputs: rebuilds stay byte-stable for the handoff.
    import hashlib
    import json
    cache_path = os.path.join(ROOT, 'source', 'cockpit', 'tape_cache.json')
    try:
        cache = json.load(open(cache_path))
    except (OSError, ValueError):
        cache = {}
    scene_key = '%d/%d/%.4f' % (len(verts), len(tris), sum(v.x + 2 * v.y + 3 * v.z for v in verts))
    used = {}
    for o in tapes:
        mw = o.matrix_world
        key = hashlib.sha1(json.dumps([o.name, scene_key, o['tape_seed'], [round(x, 6) for v in o.data.vertices
                                                                           for x in mw @ v.co]]).encode()).hexdigest()
        if key in cache:
            inv = mw.inverted()
            for v, w in zip(o.data.vertices, cache[key]):
                v.co = inv @ Vector(w)
            o.data.update()
            used[key] = cache[key]
            continue
        _conform_one(o, t, offset)
        used[key] = [list(mw @ v.co) for v in o.data.vertices]
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'w') as f:
        json.dump(used, f)


def _conform_one(o, t, offset):
    """Roll one strip onto the surfaces in BVH `t` (see conform_tapes)."""
    n = Vector(o['tape_normal']).normalized()
    ax = Vector(o['tape_axis']).normalized()
    c = Vector(o['tape_centre'])
    side = n.cross(ax)
    rng = np.random.default_rng(o['tape_seed'])
    mw = o.matrix_world
    me = o.data
    flat = [mw @ v.co for v in me.vertices]
    xs = [(p - c).dot(ax) for p in flat]
    ys = [(p - c).dot(side) for p in flat]
    hit = t.ray_cast(c + n * 0.012, -n, 0.05)
    if hit[0] is not None:
        c0, n0 = hit[0], _orient(hit[1], n)
    else:
        loc, m, _, _ = t.find_nearest(c, 0.05)
        c0, n0 = (loc, _orient(m, n)) if loc is not None else (c, n)
    a0 = (ax - n0 * ax.dot(n0)).normalized()
    span = max(abs(x) for x in xs) + 0.002
    fwd, back = _walk(t, c0, n0, a0, span), _walk(t, c0, n0, -a0, span)
    inv = mw.inverted()
    for v, x, y in zip(me.vertices, xs, ys):
        p, nrm, d = _at(fwd, x) if x >= 0 else _at(back, -x)
        if x < 0:
            d = -d
        q = p + nrm.cross(d).normalized() * y               # across the width
        loc, m, _, dist = t.find_nearest(q, 0.006)
        if loc is not None:
            m = _orient(m, p + nrm * 0.01 - loc)
            q = loc
            nrm = m
        new = q + nrm * (offset + rng.uniform(0, 0.00045))         # tiny wrinkles
        v.co = inv @ new
    me.update()


# --- camera-projected print ---------------------------------------------------------------------

def count_tris():
    t = 0
    for o in COLL.objects:
        if o.type == 'MESH':
            o.data.calc_loop_triangles()
            t += len(o.data.loop_triangles)
    return t


# --- stable export ------------------------------------------------------------------------------

def glb_signature(path, decimals=5):
    """Content hash of a GLB, independent of how the exporter lays out or shares buffers: nodes, meshes, materials,
    images, skins and animations with every reference resolved to its data (floats rounded)."""
    import hashlib
    import json
    import struct
    with open(path, 'rb') as f:
        data = f.read()
    off, js, binary = 12, None, b''
    while off < len(data):
        n, kind = struct.unpack_from('<II', data, off)
        chunk = data[off + 8:off + 8 + n]
        if kind == 0x4E4F534A:
            js = json.loads(chunk)
        else:
            binary = chunk
        off += 8 + n
    views = js.get('bufferViews', [])
    dtype = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
    comps = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT2': 4, 'MAT3': 9, 'MAT4': 16}

    def acc(i):
        a = js['accessors'][i]
        if 'bufferView' not in a:
            return 'empty%d' % a['count']
        v = views[a['bufferView']]
        arr = np.frombuffer(binary, dtype[a['componentType']], a['count'] * comps[a['type']],
                            v.get('byteOffset', 0) + a.get('byteOffset', 0))
        if a['componentType'] == 5126:
            arr = np.round(arr.astype(np.float64), decimals)
        return hashlib.sha1(arr.tobytes()).hexdigest()

    def rows(i):
        a = js['accessors'][i]
        v = views[a['bufferView']]
        arr = np.frombuffer(binary, dtype[a['componentType']], a['count'] * comps[a['type']],
                            v.get('byteOffset', 0) + a.get('byteOffset', 0)).reshape(a['count'], comps[a['type']])
        return np.round(arr.astype(np.float64), decimals)

    def prim_sig(p):                     # vertex order, index width and triangle order don't matter
        cols = [rows(v) for _, v in sorted(p['attributes'].items())]
        cols += [rows(v) for t in p.get('targets', []) for _, v in sorted(t.items())]
        vert = np.concatenate(cols, axis=1)
        _, ids = np.unique(vert, axis=0, return_inverse=True)        # canonical id per distinct vertex
        ids = ids.ravel()
        if 'indices' in p:
            a = js['accessors'][p['indices']]
            v = views[a['bufferView']]
            t = np.frombuffer(binary, dtype[a['componentType']], a['count'], v.get('byteOffset', 0) + a.get('byteOffset', 0))
            t = ids[t.astype(np.int64)].reshape(-1, 3)
        else:
            t = ids.reshape(-1, 3)
        if len(t):
            r = np.argmin(t, axis=1)
            t = np.stack([np.roll(row, -k) for row, k in zip(t, r)])
            t = t[np.lexsort(t.T[::-1])]
        return hashlib.sha1(np.unique(vert, axis=0).tobytes() + t.astype(np.int64).tobytes()).hexdigest()

    def rnd(x):
        return [round(v, decimals) for v in x] if isinstance(x, list) else x

    def image(i):
        im = js['images'][i]
        v = views[im['bufferView']] if 'bufferView' in im else None
        return hashlib.sha1(binary[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]).hexdigest() if v else im.get('uri')

    def resolve_tex(m):
        if isinstance(m, dict):
            return {k: (image(js['textures'][v]['source']) if k == 'index' and isinstance(v, int) else resolve_tex(v))
                    for k, v in m.items()}
        return [resolve_tex(x) for x in m] if isinstance(m, list) else m
    mats = [resolve_tex(m) for m in js.get('materials', [])]
    meshes = [[{'geo': prim_sig(p), 'mat': mats[p['material']] if 'material' in p else None} for p in m['primitives']]
              for m in js.get('meshes', [])]
    nodes = js.get('nodes', [])
    sig = {'nodes': [{'name': n.get('name'), 'mesh': meshes[n['mesh']] if 'mesh' in n else None,
                      'children': sorted(nodes[c].get('name', '') for c in n.get('children', [])),
                      **{k: rnd(n[k]) for k in ('translation', 'rotation', 'scale', 'matrix') if k in n},
                      'extras': n.get('extras')} for n in nodes],
           'skins': [{'joints': [nodes[j].get('name') for j in s_['joints']],
                      'ibm': acc(s_['inverseBindMatrices']) if 'inverseBindMatrices' in s_ else None}
                     for s_ in js.get('skins', [])],
           'anims': sorted(json.dumps({'name': a.get('name'), 'ch': sorted(
               json.dumps([nodes[c['target']['node']].get('name'), c['target']['path'],
                           acc(a['samplers'][c['sampler']]['input']), acc(a['samplers'][c['sampler']]['output']),
                           a['samplers'][c['sampler']].get('interpolation')]) for c in a['channels'])})
               for a in js.get('animations', []))}
    return hashlib.sha256(json.dumps(sig, sort_keys=True).encode()).hexdigest()


def export_glb(filepath, **kw):
    """bpy glTF export that keeps the existing file when only float noise changed (stable bytes for handoffs)."""
    import shutil
    import tempfile
    tmp = os.path.join(tempfile.mkdtemp(), os.path.basename(filepath))   # outside the project: editors watch it
    bpy.ops.export_scene.gltf(filepath=tmp, **kw)
    same = os.path.exists(filepath) and glb_signature(filepath) == glb_signature(tmp)
    if same:
        print('GLB unchanged', os.path.basename(filepath))
    else:
        shutil.move(tmp, filepath)
    shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)
    return not same
