extends SceneTree
## Checks hands/art/hand_[rl].tscn against the contract and hand_rig.json:
## names, every clip, "hit" markers, and each marker landing on its Blender target at its clip time.
## godot --headless --path . -s scripts/hands/check_hand_rig.gd

const CLIPS := ["relaxed", "grip", "grip_tight", "grip_yank", "idle_hover_ripple", "idle_hover_tap",
	"idle_grip_thumbtap", "idle_grip_drum", "idle_rest", "idle_drum", "idle_stretch", "idle_nails", "idle_wave"]
const TYPES := ["finger", "fingers", "palm", "fist"]
const TOL := 0.0015

var fails := 0


func _initialize() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://hands/art/hand_rig.json"))
	for side in ["r", "l"]:
		var hand: Node3D = load("res://hands/art/hand_%s.tscn" % side).instantiate()
		root.add_child(hand)
		var anim: AnimationPlayer = hand.find_child("Anim", true, false)
		var skel: Skeleton3D = hand.find_child("Skeleton", true, false)
		_ok(anim != null and skel != null and skel.find_bone("palm") >= 0, "%s: Anim + Skeleton(palm)" % side)
		var names := CLIPS.duplicate()
		for t in TYPES:
			names += ["hover_" + t, "press_" + t, "release_" + t]
		for n in names:
			_ok(anim.has_animation(n), "%s: clip %s" % [side, n])
		for t in TYPES:
			_ok(anim.get_animation("press_" + t).has_marker("hit"), "%s: press_%s hit marker" % [side, t])
		for m in data[side].markers:
			anim.play(m.clip)
			anim.seek(m.time, true)
			skel.force_update_all_bone_transforms()
			var marker: Marker3D = hand.find_child(m.name, true, false)
			await process_frame
			var got := hand.global_transform.affine_inverse() * marker.global_position
			var want := Vector3(m.pos[0], m.pos[1], m.pos[2])
			_ok(got.distance_to(want) < TOL, "%s: %s at %s t=%.2f (off %.1f mm)" % [
				side, m.name, m.clip, m.time, got.distance_to(want) * 1000])
		hand.queue_free()
	print("HAND RIG CHECK ", "PASS" if fails == 0 else "FAIL (%d)" % fails)
	quit(1 if fails else 0)


func _ok(cond: bool, what: String) -> void:
	if not cond:
		fails += 1
		print("  FAIL ", what)
	elif "off" in what:
		print("  ok   ", what)
