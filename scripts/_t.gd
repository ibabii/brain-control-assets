extends SceneTree
func _initialize() -> void:
	var h: Node3D = load("res://human/art/human.tscn").instantiate()
	root.add_child(h)
	var floor := StaticBody3D.new()
	var col := CollisionShape3D.new(); var box := BoxShape3D.new(); box.size = Vector3(10, 1, 10)
	col.shape = box; col.position = Vector3(0, -0.5, 0); floor.add_child(col); root.add_child(floor)
	h.rotation_degrees.x = 8
	await physics_frame
	var skel: Skeleton3D = h.get_node("Rig/Skeleton")
	var sim: PhysicalBoneSimulator3D = skel.get_node("Ragdoll")
	sim.physical_bones_start_simulation()
	for n in 400:
		await physics_frame
		if n % 50 == 0:
			var s := ''
			for pb in sim.get_children(): s += '%s %.2f ' % [pb.name.trim_prefix('Physical Bone ').left(6), pb.global_position.y]
			print('T', n, ' ', s)
	quit()
