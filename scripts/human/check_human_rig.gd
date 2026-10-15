extends SceneTree
## Human rig contract check (coordination/interfaces.md "Human rig"), headless:
## names, clips, markers, render layer 2, hidden face parts; TwoBoneIK3D reach + pole side for both arms and legs;
## a ragdoll drop onto a floor that must settle without exploding.
## godot --headless --path . -s scripts/human/check_human_rig.gd

const CLIPS := ["rest", "idle", "hand_grip_L", "hand_grip_R", "hand_relaxed_L", "hand_relaxed_R", "hand_spread_L",
	"hand_spread_R"]
const MARKERS := ["Grip_L", "Grip_R", "Sole_L", "Sole_R", "EyeCam", "Foam"]
const FACE := ["EyeL", "EyeR", "LookL", "LookR", "LidL", "LidR", "BrowL", "BrowR", "Mouth", "Smile", "Open", "Tongue",
	"Teeth", "Grimace", "GrimaceLine", "BlushL", "BlushR"]

var fails := 0


func _initialize() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://human/art/human_rig.json"))
	var h: Node3D = load("res://human/art/human.tscn").instantiate()
	root.add_child(h)
	await process_frame
	var skel: Skeleton3D = h.get_node_or_null("Rig/Skeleton")
	var anim: AnimationPlayer = h.get_node_or_null("Anim")
	_ok(skel != null and anim != null, "Rig/Skeleton and Anim")
	for b in data.bones:
		_ok(skel.find_bone(b) >= 0, "bone " + b)
	for c in CLIPS:
		_ok(anim.has_animation(c), "clip " + c)
	_ok(anim.get_animation("idle").loop_mode == Animation.LOOP_LINEAR, "idle loops")
	for c in CLIPS.slice(2):
		var a := anim.get_animation(c)
		var only_fingers := true
		for t in a.get_track_count():
			var bn := a.track_get_path(t).get_concatenated_subnames()
			only_fingers = only_fingers and ["Thumb", "Index", "Middle", "Ring"].any(func(f): return f in bn)
		_ok(only_fingers, "%s keys finger bones only" % c)
	for m in MARKERS:
		_ok(h.find_child(m, true, false) is Marker3D, "marker " + m)
	for f in FACE:
		_ok(h.find_child(f, true, false) != null, "face part " + f)
	for n in data.hidden:
		_ok(not (h.find_child(n, true, false) as Node3D).visible, n + " starts hidden")
	var wrong := h.find_children("*", "VisualInstance3D", true, false).filter(func(v): return v.layers != 2)
	_ok(wrong.is_empty(), "every mesh on render layer 2 (%d not)" % wrong.size())
	var grip: Marker3D = h.find_child("Grip_R", true, false)
	var gb := grip.global_basis
	_ok(gb.x.cross(gb.y).dot(gb.z) > 0.99, "Grip_R basis right-handed")
	_ok(gb.y.dot(Vector3(1, 0, 0)) > 0.8, "Grip_R +Y = back of the hand (out, +X at rest)")
	var gl: Marker3D = h.find_child("Grip_L", true, false)
	_ok(gl.global_basis.y.dot(Vector3(-1, 0, 0)) > 0.8 and gl.global_basis.x.cross(gl.global_basis.y).dot(gl.global_basis.z) > 0.99,
		"Grip_L back of the hand -X, right-handed")
	await _ik(h, skel, data)
	await _ragdoll(h, skel)
	print("HUMAN RIG CHECK ", "PASS" if fails == 0 else "FAIL (%d)" % fails)
	quit(1 if fails else 0)


## Each arm and leg reaches a target 10 cm off its rest end; the end lands within 1 cm and the middle joint bends
## toward its pole.
func _ik(h: Node3D, skel: Skeleton3D, data: Dictionary) -> void:
	var ik := TwoBoneIK3D.new()
	skel.add_child(ik)
	var tests := []
	var i := 0
	for side in ["Left", "Right"]:
		for limb in ["arm", "leg"]:
			var chain: Array = data.ik[side][limb]
			var end := skel.get_bone_global_rest(skel.find_bone(chain[2])).origin
			var off := Vector3(0, 0.12, -0.12) if limb == "arm" else Vector3(0, 0.15, -0.08)
			var target := Marker3D.new()
			target.position = end + off
			skel.add_child(target)
			var pole := Marker3D.new()
			var pole_pos: Array = data.ik[side]["elbow_pole" if limb == "arm" else "knee_pole"]
			pole.position = Vector3(pole_pos[0], pole_pos[1], pole_pos[2])
			skel.add_child(pole)
			tests.append([chain, target, pole])
			i += 1
	ik.setting_count = tests.size()
	for k in tests.size():
		var t: Array = tests[k]
		ik.set_root_bone_name(k, t[0][0])
		ik.set_middle_bone_name(k, t[0][1])
		ik.set_end_bone_name(k, t[0][2])
		ik.set_target_node(k, ik.get_path_to(t[1]))
		ik.set_pole_node(k, ik.get_path_to(t[2]))
	var posed := {}                     # modifier results are only readable inside skeleton_updated
	var grab := func():
		for t in tests:
			for b in t[0]:
				posed[b] = skel.get_bone_global_pose(skel.find_bone(b)).origin
	skel.skeleton_updated.connect(grab)
	for n in 6:
		await process_frame
	skel.skeleton_updated.disconnect(grab)
	for t in tests:
		var root_p: Vector3 = posed[t[0][0]]
		var mid: Vector3 = posed[t[0][1]]
		var end: Vector3 = posed[t[0][2]]
		var miss: float = end.distance_to(t[1].position)
		_ok(miss < 0.01, "IK %s reaches (off %.1f cm)" % [t[0][2], miss * 100])
		var line := (end - root_p).normalized()
		var bend := (mid - root_p) - line * (mid - root_p).dot(line)
		var to_pole: Vector3 = (t[2].position - root_p) - line * (t[2].position - root_p).dot(line)
		_ok(bend.dot(to_pole) > 0, "IK %s bends toward its pole" % t[0][1])
	ik.queue_free()
	await process_frame


## Drop from standing onto a floor: settles low, every body finite, bone lengths kept (joints hold).
func _ragdoll(h: Node3D, skel: Skeleton3D) -> void:
	var floor := StaticBody3D.new()
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(10, 1, 10)
	col.shape = box
	col.position = Vector3(0, -0.5, 0)
	floor.add_child(col)
	root.add_child(floor)
	var sim: PhysicalBoneSimulator3D = skel.get_node("Ragdoll")
	var rest_len := {}
	for b in ["LeftLowerLeg", "RightLowerArm", "Head", "LeftFoot", "Spine"]:
		var i := skel.find_bone(b)
		rest_len[b] = skel.get_bone_global_rest(i).origin.distance_to(skel.get_bone_global_rest(skel.get_bone_parent(i)).origin)
	h.rotation_degrees.x = 8                                  # tip forward a little so it falls
	await physics_frame
	var posed := {}
	var grab := func():
		for b in rest_len:
			var i := skel.find_bone(b)
			posed[b] = skel.get_bone_global_pose(i).origin.distance_to(skel.get_bone_global_pose(skel.get_bone_parent(i)).origin)
	sim.physical_bones_start_simulation()
	for n in 300:
		await physics_frame
	skel.skeleton_updated.connect(grab)
	await process_frame
	await process_frame
	skel.skeleton_updated.disconnect(grab)
	var finite := true
	var top := -INF
	for pb in sim.get_children():
		finite = finite and pb.global_position.is_finite()
		top = maxf(top, pb.global_position.y)
	_ok(finite, "ragdoll stays finite")
	_ok(top < 0.45, "ragdoll settles on the floor (highest body %.2f m)" % top)
	for b in rest_len:
		_ok(posed.has(b) and absf(posed[b] - rest_len[b]) < 0.03, "ragdoll keeps %s attached (%.3f vs %.3f)" % [
			b, posed.get(b, -1.0), rest_len[b]])
	sim.physical_bones_stop_simulation()


func _ok(cond: bool, what: String) -> void:
	if not cond:
		fails += 1
		print("  FAIL ", what)
	elif "(" in what:
		print("  ok   ", what)
