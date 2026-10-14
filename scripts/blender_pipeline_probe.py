"""Calibration fixture executed through Blender MCP. Dimensions test glTF's axis conversion."""
import bpy
import json

root = bpy.context.scene["brain_control_assets_root"]
probe = bpy.data.objects.get("PipelineProbe")
if probe is not None:
    bpy.data.objects.remove(probe, do_unlink=True)
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
probe = bpy.context.object
probe.name = "PipelineProbe"
# Blender Z-up -> glTF/Godot Y-up: expected Godot size (0.19, 0.016, 0.022).
probe.dimensions = (0.19, 0.022, 0.016)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
material = bpy.data.materials.get("ProbeMint") or bpy.data.materials.new("ProbeMint")
material.use_nodes = True
shader = material.node_tree.nodes.get("Principled BSDF")
shader.inputs["Base Color"].default_value = (0.45, 0.62, 0.52, 1.0)
shader.inputs["Roughness"].default_value = 0.65
probe.data.materials.clear()
probe.data.materials.append(material)
bpy.ops.wm.save_as_mainfile(filepath=root + "/.local/assets_workspace.blend")
export_path = root + "/previews/toolchain_validation/pipeline_probe.glb"
bpy.ops.export_scene.gltf(
    filepath=export_path, export_format="GLB", use_selection=True,
    export_yup=True, export_apply=True, export_cameras=False, export_lights=False,
)
probe.data.calc_loop_triangles()
print("BLENDER_EXPORT_OK", json.dumps({"path": export_path, "blender_dimensions": list(probe.dimensions),
                                       "triangles": len(probe.data.loop_triangles), "material": material.name}))
