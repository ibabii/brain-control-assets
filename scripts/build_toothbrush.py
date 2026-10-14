"""Build the warm ceramic v1 toothbrush in Blender; execute via Blender MCP.

Coordinates in the design functions are Godot X/Y/Z. g() converts to Blender Z-up.
Only the WC_Toothbrush_V1 collection is replaced on rebuild.
"""
import bpy
import bmesh
import math
import json
from mathutils import Vector

ROOT = bpy.context.scene.get("brain_control_assets_root")
assert ROOT == "/Users/nataliiamykytenko/Documents/Projects/gamedev/brain-control-assets", "Wrong assets workspace"
STYLE = "warm_ceramic_v1"
COLORS = {"clay": "C98778", "teal": "2D5C5B", "porcelain": "F8F4EA", "sage": "BAC6B2"}

old = bpy.data.collections.get("WC_Toothbrush_V1")
if old:
    for obj in list(old.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(old)
collection = bpy.data.collections.new("WC_Toothbrush_V1")
bpy.context.scene.collection.children.link(collection)


def g(v):
    return (v[0], -v[2], v[1])


def signed_power(value, power):
    return math.copysign(abs(value) ** power, value)


def material(name, color_id, roughness):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    srgb = [int(COLORS[color_id][i:i+2], 16) / 255 for i in (0, 2, 4)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in srgb]
    bsdf.inputs["Base Color"].default_value = (*linear, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0
    mat.diffuse_color = (*linear, 1)
    mat.use_backface_culling = True
    mat["palette_id"] = color_id
    mat["style_id"] = STYLE
    return mat


clay = material("WC1_ClayPaint", "clay", 0.62)
teal = material("WC1_TealGrip", "teal", 0.86)
bristle_mat = material("WC1_PorcelainBristles", "porcelain", 0.9)
paste_mat = material("WC1_SagePaste", "sage", 0.72)
stripe_mat = material("WC1_PorcelainPaste", "porcelain", 0.72)


def empty(name, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = g(location)
    return obj


root = empty("ToothbrushArt")
root["style_id"] = STYLE
root["origin_note"] = "Head-centred pivot; Godot handle +X, bristles +Y, width Z"
paste_root = empty("Paste", root)
grip_point = empty("GripPoint", root, (0.17, -0.01, 0))
grip_point.empty_display_size = 0.006


def mesh_object(name, vertices, faces, mat, parent=root, smooth=True):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata([g(v) for v in vertices], [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = smooth
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.parent = parent
    mesh.materials.append(mat)
    return obj


def loft_x(name, stations, mat, parent=root, segments=12, exponent=0.7):
    # Stations: x, half-height Y, half-width Z, centre Y.
    verts, faces = [], []
    for x, height, width, cy in stations:
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            verts.append((x, cy + height * signed_power(math.cos(angle), exponent),
                          width * signed_power(math.sin(angle), exponent)))
    for row in range(len(stations) - 1):
        for i in range(segments):
            a = row * segments + i
            b = row * segments + (i + 1) % segments
            faces.append((a, b, b + segments, a + segments))
    faces.append(tuple(range(segments - 1, -1, -1)))
    last = (len(stations) - 1) * segments
    faces.append(tuple(last + i for i in range(segments)))
    return mesh_object(name, verts, faces, mat, parent)


handle = loft_x("Handle", [
    (0.012, 0.0030, 0.0060, 0.0050),
    (0.020, 0.0034, 0.0050, 0.0045),
    (0.031, 0.0038, 0.0043, 0.0030),
    (0.049, 0.0044, 0.0050, 0.0010),
    (0.073, 0.0050, 0.0068, -0.0015),
    (0.100, 0.0055, 0.0084, -0.0040),
    (0.126, 0.0060, 0.0100, -0.0050),
    (0.148, 0.0060, 0.0105, -0.0050),
    (0.162, 0.0055, 0.0090, -0.0050),
    (0.172, 0.0040, 0.0060, -0.0050),
    (0.176, 0.0013, 0.0020, -0.0050),
], clay)

# Soft oval head: four bevel rings, capped with flat faces.
verts, faces = [], []
segments = 16
for y, scale in [(0.001, 0.85), (0.003, 1.0), (0.008, 1.0), (0.010, 0.86)]:
    for i in range(segments):
        a = 2 * math.pi * i / segments
        verts.append((0.018 * signed_power(math.cos(a), 0.7) * scale, y,
                      0.010 * signed_power(math.sin(a), 0.7) * scale))
for row in range(3):
    for i in range(segments):
        a = row * segments + i
        b = row * segments + (i + 1) % segments
        faces.append((a, b, b + segments, a + segments))
faces.extend([tuple(range(segments - 1, -1, -1)), tuple(48 + i for i in range(segments))])
head = mesh_object("Head", verts, faces, clay)
head.data.polygons[-1].use_smooth = False
head.data.polygons[-2].use_smooth = False

grip = loft_x("Grip", [
    (0.099, 0.0004, 0.0020, 0.0020),
    (0.106, 0.0010, 0.0050, 0.0020),
    (0.122, 0.0012, 0.0068, 0.0021),
    (0.142, 0.0012, 0.0068, 0.0021),
    (0.157, 0.0010, 0.0056, 0.0020),
    (0.164, 0.0004, 0.0018, 0.0020),
], teal, segments=8)

# Bristles are twelve broad tufts combined into one mesh/draw surface.
verts, faces = [], []
segments = 8
for x in [-0.012, -0.004, 0.004, 0.012]:
    for z in [-0.006, 0.0, 0.006]:
        base = len(verts)
        top = 0.026 if abs(z) < 0.001 else 0.0245
        for y, radius in [(0.0105, 0.0025), (top - 0.001, 0.0027), (top, 0.0022)]:
            for i in range(segments):
                angle = 2 * math.pi * i / segments
                verts.append((x + math.cos(angle) * radius, y, z + math.sin(angle) * radius))
        for row in range(2):
            for i in range(segments):
                a = base + row * segments + i
                b = base + row * segments + (i + 1) % segments
                faces.append((a, b, b + segments, a + segments))
        faces.append(tuple(base + i for i in range(segments - 1, -1, -1)))
        faces.append(tuple(base + 16 + i for i in range(segments)))
bristles = mesh_object("Bristles", verts, faces, bristle_mat)

# Mint paste ribbon rests above the tufts, separately toggleable as Paste.
paste = loft_x("PasteBody", [
    (-0.0130, 0.0010, 0.0012, 0.0280),
    (-0.0100, 0.0027, 0.0036, 0.0290),
    (-0.0050, 0.0031, 0.0041, 0.0292),
    (0.0010, 0.0030, 0.0040, 0.0290),
    (0.0060, 0.0025, 0.0032, 0.0287),
    (0.0110, 0.0013, 0.0020, 0.0297),
    (0.0140, 0.0002, 0.0003, 0.0320),
], paste_mat, paste_root, segments=10, exponent=1.0)
stripe = loft_x("PasteStripe", [
    (-0.0100, 0.0002, 0.0003, 0.0317),
    (-0.0060, 0.0005, 0.0008, 0.0323),
    (0.0010, 0.0005, 0.0008, 0.0320),
    (0.0060, 0.0004, 0.0006, 0.0312),
    (0.0100, 0.0002, 0.0003, 0.0316),
], stripe_mat, paste_root, segments=6, exponent=1.0)

# Hide other workspace objects for preview without deleting them.
for obj in bpy.context.scene.objects:
    if obj not in list(collection.objects):
        obj.hide_set(True)
        obj.hide_render = True
bpy.ops.object.select_all(action="DESELECT")
for obj in collection.objects:
    obj.hide_set(False)
    obj.hide_render = False
    obj.select_set(True)
bpy.context.view_layer.objects.active = handle
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 1.0
bpy.context.scene.name = "ToothbrushArt"

def export_selected(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
                             export_yup=True, export_apply=True,
                             export_cameras=False, export_lights=False)

export_selected(ROOT + "/props/toothbrush/art/toothbrush_body.glb", [root, handle, head, grip, bristles])
export_selected(ROOT + "/props/toothbrush/art/toothbrush_paste.glb", [paste_root, paste, stripe])
for obj in collection.objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = handle
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.region_3d.view_location = Vector((0.079, 0.0, 0.010))
            area.spaces.active.region_3d.view_distance = 0.28
            area.spaces.active.region_3d.view_rotation = Vector((0.25, -1.0, 0.7)).to_track_quat("Z", "Y")
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/source/toothbrush/toothbrush_v1.blend")

counts = {}
for obj in collection.objects:
    if obj.type == "MESH":
        obj.data.calc_loop_triangles()
        counts[obj.name] = len(obj.data.loop_triangles)
print("TOOTHBRUSH_BUILT", json.dumps({"style": STYLE, "triangles": counts, "total_triangles": sum(counts.values()),
                                     "body_length_m": 0.194, "grip_godot": [0.17, -0.01, 0],
                                     "source": ROOT + "/source/toothbrush/toothbrush_v1.blend"}))
