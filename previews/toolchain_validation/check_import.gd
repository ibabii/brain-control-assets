extends SceneTree

func _initialize() -> void:
	var packed := load("res://previews/toolchain_validation/pipeline_probe.glb") as PackedScene
	if packed == null:
		push_error("GLB_IMPORT_FAILED")
		quit(1)
		return
	var scene := packed.instantiate()
	root.add_child(scene)
	var meshes := scene.find_children("*", "MeshInstance3D", true, false)
	if meshes.size() != 1:
		push_error("Expected one calibration mesh, got %s" % meshes.size())
		quit(1)
		return
	var mesh: MeshInstance3D = meshes[0]
	var size := mesh.mesh.get_aabb().size
	var expected := Vector3(0.19, 0.016, 0.022)
	var material := mesh.mesh.surface_get_material(0) as StandardMaterial3D
	if not size.is_equal_approx(expected) or material == null or material.resource_name != "ProbeMint":
		push_error("GLB_VALIDATION_FAILED size=%s material=%s" % [size, material])
		quit(1)
		return
	print("GODOT_IMPORT_OK size=%s materials=%s roughness=%.2f" % [size, material.resource_name, material.roughness])
	quit(0)
