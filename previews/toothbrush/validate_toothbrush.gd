extends SceneTree
## Meaningful handoff checks on the imported model, independent of gameplay wrappers.

const MATERIALS := {
	"WC1_ClayPaint": ["c98778", 0.62],
	"WC1_TealGrip": ["2d5c5b", 0.86],
	"WC1_PorcelainBristles": ["f8f4ea", 0.9],
	"WC1_SagePaste": ["bac6b2", 0.72],
	"WC1_PorcelainPaste": ["f8f4ea", 0.72],
}
var failures: Array[String] = []


func check(ok: bool, description: String) -> void:
	if not ok:
		failures.append(description)
		push_error(description)


func _initialize() -> void:
	_validate.call_deferred()


func _validate() -> void:
	var packed := load("res://props/toothbrush/art/toothbrush_art.tscn") as PackedScene
	if packed == null:
		push_error("Cannot load toothbrush art and its relative GLB dependencies")
		quit(1)
		return
	var art := packed.instantiate() as Node3D
	root.add_child(art)
	check(art.name == "ToothbrushArt", "Root name must be ToothbrushArt")
	check(art.transform.is_equal_approx(Transform3D.IDENTITY), "Root must have identity rest transform")
	check(art.has_node("Paste"), "Paste must be a direct, separately toggleable child")
	check(art.has_node("GripPoint"), "GripPoint must exist")
	check(art.get_node("GripPoint").position.is_equal_approx(Vector3(0.17, -0.01, 0)), "Grip marker position changed")
	var all_nodes := art.find_children("*", "", true, false)
	all_nodes.append(art)
	for node in all_nodes:
		check(node.get_script() == null, "Art contains a runtime script: " + String(node.name))
		check(not node is AnimationPlayer and not node is CollisionObject3D and not node is CollisionShape3D,
			"Art contains animation or collision: " + String(node.name))
	var meshes := art.find_children("*", "MeshInstance3D", true, false)
	check(meshes.size() == 6, "Expected six mesh parts")
	var bounds := AABB()
	var first := true
	var triangles := 0
	var materials_seen := {}
	for node in meshes:
		var mesh := node as MeshInstance3D
		check(mesh.layers == 1, "Art mesh must use default render layer 1: " + String(mesh.name))
		var local_to_root := art.global_transform.affine_inverse() * mesh.global_transform
		var box := local_to_root * mesh.get_aabb()
		bounds = box if first else bounds.merge(box)
		first = false
		for surface in mesh.mesh.get_surface_count():
			var arrays := mesh.mesh.surface_get_arrays(surface)
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			triangles += indices.size() / 3
			var mat := mesh.mesh.surface_get_material(surface) as StandardMaterial3D
			check(mat != null, "Mesh must have imported StandardMaterial3D")
			if mat == null:
				continue
			check(MATERIALS.has(mat.resource_name), "Unexpected material " + mat.resource_name)
			if MATERIALS.has(mat.resource_name):
				var recipe: Array = MATERIALS[mat.resource_name]
				check(mat.albedo_color.to_html(false) == recipe[0], "Palette mismatch: " + mat.resource_name + " " + mat.albedo_color.to_html(false))
				check(absf(mat.roughness - recipe[1]) < 0.0001, "Roughness mismatch: " + mat.resource_name)
			check(mat.transparency == BaseMaterial3D.TRANSPARENCY_DISABLED, "Unexpected alpha blending")
			check(not mat.emission_enabled, "Unexpected emissive material")
			check(mat.cull_mode == BaseMaterial3D.CULL_BACK, "Closed meshes should have backface culling")
			materials_seen[mat.resource_name] = true
	check(absf(bounds.size.x - 0.194) < 0.0001, "Length/axis conversion must remain 0.194 m along X")
	check(absf(bounds.size.y - 0.0438) < 0.0001, "Bristles/paste should extend along +Y")
	check(absf(bounds.size.z - 0.021) < 0.0001, "Head/handle width should extend along Z")
	check(triangles == 1196, "Triangle count changed unexpectedly")
	check(materials_seen.size() == 5, "Expected five shared palette materials")
	var paste := art.get_node("Paste") as Node3D
	paste.visible = false
	var visible_without_paste := 0
	for node in meshes:
		if node.is_visible_in_tree():
			visible_without_paste += 1
	check(visible_without_paste == 4, "Hiding Paste must hide both paste pieces only")
	paste.visible = true
	for angle in [-14.0, 14.0]:
		art.rotation_degrees.y = angle
		check(art.scale.is_equal_approx(Vector3.ONE), "Swing must not change scale")
		check(art.get_node("GripPoint").position.is_equal_approx(Vector3(0.17, -0.01, 0)), "Swing must preserve local grip")
	art.rotation = Vector3.ZERO
	check(art.transform.is_equal_approx(Transform3D.IDENTITY), "Rest pose must be recoverable")
	print("TOOTHBRUSH_VALIDATION bounds=%s triangles=%s meshes=%s materials=%s failures=%s" %
		[bounds, triangles, meshes.size(), materials_seen.size(), failures.size()])
	quit(0 if failures.is_empty() else 1)
