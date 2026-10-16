extends Node
## Preview only: each note slot's text box in screen px (from layout.json) and the cap height the box allows for a
## given layout (Patrick Hand: cap 0.5 em, caps ~0.55 em wide, lines 1.09 em). Run at 1920x1080.
## Needs: SameBrain 18 px for 2 lines x 10 chars; others 14 px for <= 4 words (3 lines x 9 chars).

const NEED := {"SameBrain": [2, 10, 18], "Clock": [2, 7, 14]}
const DEFAULT := [3, 9, 14]

func _ready() -> void:
	for n in 6:
		await get_tree().process_frame
	var cam := get_viewport().get_camera_3d()
	var slots: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://cockpit/art/layout.json"))["notes"]
	for id in slots:
		var s: Dictionary = slots[id]
		if s["kind"] != "label":
			continue
		var b: Array = s["basis"]
		var x := Vector3(b[0][0], b[0][1], b[0][2])
		var y := Vector3(b[1][0], b[1][1], b[1][2])
		var c := Vector3(s["position"][0], s["position"][1], s["position"][2])
		var w: float = s["size"][0]
		var h: float = s["size"][1]
		var px_w := cam.unproject_position(c + x * w / 2).distance_to(cam.unproject_position(c - x * w / 2))
		var px_h := cam.unproject_position(c + y * h / 2).distance_to(cam.unproject_position(c - y * h / 2))
		var need: Array = NEED.get(id, DEFAULT)
		var cap_w: float = px_w / (need[1] * 0.55) * 0.5
		var cap_h: float = px_h / (need[0] * 1.09) * 0.5
		var cap_now: float = 0.5 * s["line_height"] / 1.18 * px_h / h
		print("NOTE_PX %-11s box %4d x %3d px  cap now %4.1f  max %4.1f (w %4.1f h %4.1f) need %d %s" % [id, px_w, px_h,
			cap_now, minf(cap_w, cap_h), cap_w, cap_h, need[2], "OK" if minf(cap_w, cap_h) >= need[2] else "SHORT"])
	get_tree().quit()
