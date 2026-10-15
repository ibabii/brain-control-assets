@tool
extends EditorScenePostImport
## Post-import for bathroom/art/bathroom_room.glb: adds `Collision` (StaticBody3D, layer 1, mask 0) with one box per
## entry of layout.json "colliders" (floor, walls, vanity, tub shell, toilet, shelves) for the Human's ragdoll.


func _post_import(scene: Node) -> Object:
	var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://bathroom/art/layout.json"))
	var body := StaticBody3D.new()
	body.name = "Collision"
	body.collision_layer = 1
	body.collision_mask = 0
	scene.add_child(body)
	body.owner = scene
	for c in layout.colliders:
		var box := BoxShape3D.new()
		box.size = Vector3(c.size[0], c.size[1], c.size[2])
		var col := CollisionShape3D.new()
		col.name = c.name
		col.shape = box
		col.position = Vector3(c.centre[0], c.centre[1], c.centre[2])
		body.add_child(col)
		col.owner = scene
	return scene
