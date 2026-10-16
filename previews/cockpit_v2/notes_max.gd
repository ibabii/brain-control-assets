extends Node
## Preview only: the five story slots at the art director's max lengths (art_direction.md "Note slots");
## prints each label's size against its paper box from layout.json.

const MAX := {
	"SameBrain": "TUB =\nSLIPPERY\nINTERVIEW?\nDON'T PANIC",
	"YouGotThis": "YOU MADE\nIT OUT.\nBARELY.",
	"MopFloor": "PARCEL =\nSOMEBODY\nELSE'S\nPROBLEM.",
	"Chaos": "NEVER\nAGAIN:\nBATHROOM\nDOORKNOBS",
	"SmallSteps": "9:40 AM\n5H LEFT",
}

func _ready() -> void:
	await get_tree().process_frame
	var slots: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://cockpit/art/layout.json"))["notes"]
	for id in MAX:
		var l0 := get_tree().current_scene.find_children(id, "Label3D", true, false)[0] as Label3D
		var b0 := l0.get_aabb()
		print("NOTE_DEFAULT %-10s text %.3f x %.3f" % [id, b0.size.x * l0.global_basis.x.length(), b0.size.y * l0.global_basis.y.length()])
	for id in MAX:
		var l := get_tree().current_scene.find_children(id, "Label3D", true, false)[0] as Label3D
		l.text = MAX[id]
		await get_tree().process_frame
		var box := l.get_aabb()
		var w := box.size.x * l.global_basis.x.length()
		var h := box.size.y * l.global_basis.y.length()
		var s: Array = slots[id]["size"]
		print("NOTE_FIT %-10s text %.3f x %.3f  box %.3f x %.3f  %s" % [id, w, h, s[0], s[1], "OK" if w <= s[0] * 1.02 and h <= s[1] * 1.02 else "OVER"])
