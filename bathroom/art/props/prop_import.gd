@tool
extends EditorScenePostImport
## Post-import for holdable and sittable props (contract: coordination/interfaces.md "Character rig v1"):
## the glb empties `Grips/Left|Right` and `Seat` become Marker3D.


func _post_import(scene: Node) -> Object:
	for n in scene.find_children("*", "Node3D", true, false):
		if n.get_class() == "Node3D" and (n.name == "Seat" or n.get_parent().name == "Grips"):
			var m := Marker3D.new()
			m.name = n.name
			m.transform = n.transform
			n.replace_by(m, true)
			m.owner = scene
			n.free()
	return scene
