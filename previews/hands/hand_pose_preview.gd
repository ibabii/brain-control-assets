extends Node3D
## Places both hands on the console from their markers (like gameplay) and holds a clip frame.
## Use with the cockpit preview: --extra res://previews/hands/hand_pose_preview.tscn
##   [--left press_finger] [--right grip] [--t 1.0 (fraction of the clip)] [--lx -0.078 (left target x shift; A key)]

const CAP_S := Vector3(-0.329, 0.988, 0.112)      # S key cap top (left_keys at the LeftKeys anchor)
const KNOB := Vector3(0.33, 1.102, 0.149)         # joystick ball centre
const N := Vector3(0, 0.951057, 0.309017)         # console normal (tilt 18)
const F := Vector3(0, 0.309017, -0.951057)        # along the console, away from the player
const SHOULDER := {"l": Vector3(-0.42, 1.0, 0.7), "r": Vector3(0.42, 1.0, 0.7)}   # game LeftHand/RightHand origins


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var frac := float(_arg(args, "--t", "1.0"))
	_place("l", _arg(args, "--left", "press_finger"), CAP_S + Vector3(float(_arg(args, "--lx", "0")), 0, 0), frac)
	_place("r", _arg(args, "--right", "grip"), KNOB, frac)


func _place(side: String, clip: String, target: Vector3, frac: float) -> void:
	var hand: Node3D = load("res://hands/art/hand_%s.tscn" % side).instantiate()
	add_child(hand)
	var anim: AnimationPlayer = hand.find_child("Anim", true, false)
	var kind := clip.get_slice("_", clip.get_slice_count("_") - 1)
	var marker := "Grip" if clip.begins_with("grip") or clip.begins_with("idle_grip") else "Contact_" + kind.capitalize()
	var anchor_clip := "grip" if marker == "Grip" else "press_" + kind
	if marker != "Grip" and not kind in ["finger", "fingers", "palm", "fist"]:
		anchor_clip = "press_finger"
		marker = "Contact_Finger"
	var back: Vector3 = SHOULDER[side] - target                             # sleeve toward the game's shoulder (brain_hand._aim)
	back = (back - N * back.dot(N)).normalized()
	hand.transform = Transform3D(Basis(N.cross(back), N, back).orthonormalized(), Vector3.ZERO)
	var a := anim.get_animation(anchor_clip)
	anim.play(anchor_clip)
	anim.seek(a.get_marker_time("hit") if a.has_marker("hit") else a.length, true)
	await get_tree().process_frame
	var offset: Vector3 = hand.global_transform.affine_inverse() * hand.find_child(marker, true, false).global_position
	hand.global_position = target - hand.global_basis * offset
	var rest := get_parent().find_child("HandRest_" + side.to_upper(), true, false) as Marker3D
	if rest and (clip == "relaxed" or clip in ["idle_rest", "idle_drum", "idle_stretch", "idle_nails", "idle_wave", "idle_swat"]):
		hand.global_transform = rest.global_transform             # away idles: wrist on the desk rest spot
	anim.play(clip)
	anim.seek(anim.get_animation(clip).length * frac, true)
	anim.pause()


func _arg(args: PackedStringArray, key: String, default: String) -> String:
	var i := args.find(key)
	return args[i + 1] if i >= 0 and i + 1 < args.size() else default
