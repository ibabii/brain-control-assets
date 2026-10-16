@tool
extends EditorScenePostImport
## Post-import for human/art/human.glb (contract: coordination/interfaces.md "Character rig v1").
## Rig/Skeleton + Anim names, idle loop, hidden face parts, every mesh on render layer 2, markers on bones and the
## Ragdoll (PhysicalBoneSimulator3D, inactive) from human/art/human_rig.json written by scripts/human/build.py.

const SKEL_FROM := "Rig/Skeleton3D"
const SKEL_TO := "Rig/Skeleton"


func _post_import(scene: Node) -> Object:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://human/art/human_rig.json"))
	var rig: Node3D = scene.get_node("Rig")
	var skel: Skeleton3D = rig.get_node("Skeleton3D")
	skel.name = "Skeleton"
	var anim: AnimationPlayer = scene.get_node("AnimationPlayer")
	anim.name = "Anim"
	var lib := anim.get_animation_library("")
	for clip in lib.get_animation_list():           # the glTF importer strips a "_loop" suffix; keep the contract name
		if not data.clips.has(clip) and data.clips.has(clip + "_loop"):
			lib.rename_animation(clip, clip + "_loop")
	for clip in lib.get_animation_list():
		var a := lib.get_animation(clip)
		for t in a.get_track_count():
			a.track_set_path(t, NodePath(String(a.track_get_path(t)).replace(SKEL_FROM, SKEL_TO)))
		if clip in data.loops:
			a.loop_mode = Animation.LOOP_LINEAR
		_trim(a, clip, data, skel)
	for n in data.hidden:
		var h := scene.find_child(n, true, false)
		if h:
			h.visible = false
	for g in scene.find_children("*", "VisualInstance3D", true, false):
		g.layers = 1 << (int(data.render_layer) - 1)
	var to_skel := (rig.transform * skel.transform).affine_inverse()      # model space -> skeleton space
	for m in data.markers:
		var bone := skel.find_bone(m.bone)
		var att := BoneAttachment3D.new()
		att.name = m.name + "_Bone"
		att.bone_name = m.bone
		skel.add_child(att)
		att.owner = scene
		var marker := Marker3D.new()
		marker.name = m.name
		marker.transform = skel.get_bone_global_rest(bone).affine_inverse() * to_skel * _xf(m.pos, m.basis)
		att.add_child(marker)
		marker.owner = scene
	_ragdoll(scene, skel, to_skel, data)
	return scene


## The exporter samples every bone into every clip. Keep only the bones the json `clips` table lists for the clip
## (full: every non-finger bone, so blends never drift toward the A-pose bind; upper: one arm; hand: one hand's
## fingers), rotation tracks only, plus the Hips position.
func _trim(a: Animation, clip: String, data: Dictionary, skel: Skeleton3D) -> void:
	var bones: Array = data.clips[clip].bones if data.clips.has(clip) else []
	for t in range(a.get_track_count() - 1, -1, -1):
		var bone := a.track_get_path(t).get_concatenated_subnames()
		var type := a.track_get_type(t)
		var keep := bone in bones and (type == Animation.TYPE_ROTATION_3D or (type == Animation.TYPE_POSITION_3D
			and bone == "Hips"))
		if not keep:
			a.remove_track(t)
	var have := {}
	for t in a.get_track_count():
		if a.track_get_type(t) == Animation.TYPE_ROTATION_3D:
			have[a.track_get_path(t).get_concatenated_subnames()] = true
	for b in bones:                                   # the exporter drops channels at the bind rest: key them back
		if not have.has(b):
			var t := a.add_track(Animation.TYPE_ROTATION_3D)
			a.track_set_path(t, NodePath("%s:%s" % [SKEL_TO, b]))
			a.rotation_track_insert_key(t, 0.0, skel.get_bone_rest(skel.find_bone(b)).basis.get_rotation_quaternion())


func _ragdoll(scene: Node, skel: Skeleton3D, to_skel: Transform3D, data: Dictionary) -> void:
	var sim := PhysicalBoneSimulator3D.new()
	sim.name = "Ragdoll"
	skel.add_child(sim)
	sim.owner = scene
	for b in data.ragdoll:
		var bone := skel.find_bone(b.bone)
		var rest := skel.get_bone_global_rest(bone)
		var body_xf := to_skel * _frame(b.centre, b.axis, [1, 0, 0])
		var j: Dictionary = b.joint
		var joint_xf := to_skel * _frame(j.pos, j.along, j.bend, true)
		var pb := PhysicalBone3D.new()
		pb.name = b.name
		pb.bone_name = b.bone
		pb.mass = b.mass
		pb.collision_layer = 1 << (int(data.ragdoll_layer) - 1)
		pb.collision_mask = int(data.ragdoll_mask)
		pb.linear_damp = 0.1
		pb.angular_damp = 0.8
		pb.friction = 0.8
		pb.body_offset = rest.affine_inverse() * body_xf
		pb.joint_offset = body_xf.affine_inverse() * joint_xf
		match j.type:
			"cone":
				pb.joint_type = PhysicalBone3D.JOINT_TYPE_CONE
				pb.set("joint_constraints/swing_span", j.swing)
				pb.set("joint_constraints/twist_span", j.twist)
			"hinge":
				pb.joint_type = PhysicalBone3D.JOINT_TYPE_HINGE
				pb.set("joint_constraints/angular_limit_enabled", true)
				pb.set("joint_constraints/angular_limit_lower", j.lower)
				pb.set("joint_constraints/angular_limit_upper", j.upper)
			_:
				pb.joint_type = PhysicalBone3D.JOINT_TYPE_NONE
		pb.transform = rest * pb.body_offset
		sim.add_child(pb)
		pb.owner = scene
		var shape: Shape3D
		if b.get("shape", "capsule") == "sphere":
			shape = SphereShape3D.new()
			shape.radius = b.radius
		else:
			shape = CapsuleShape3D.new()
			shape.radius = b.radius
			shape.height = b.height
		var col := CollisionShape3D.new()
		col.name = "Shape"
		col.shape = shape
		pb.add_child(col)
		col.owner = scene


## Basis rows from the json are the marker's X, Y, Z axes (model space).
func _xf(pos: Array, basis: Array) -> Transform3D:
	var bs := Basis(_v(basis[0]), _v(basis[1]), _v(basis[2]))
	return Transform3D(bs, _v(pos))


## Frame at `pos` whose Y (body: capsule axis) or X (joint: along the bone, Z = bend axis) is `axis`.
func _frame(pos: Array, axis: Array, side: Array, joint := false) -> Transform3D:
	var a := _v(axis).normalized()
	var s := _v(side)
	s = (s - a * s.dot(a))
	if s.length() < 0.1:
		s = Vector3(0, 0, 1) - a * a.z
	s = s.normalized()
	var bs: Basis
	if joint:
		bs = Basis(a, s.cross(a), s)              # X along the bone, Z = hinge axis, Y = Z x X
	else:
		bs = Basis(s, a, s.cross(a))              # Y = capsule axis
	return Transform3D(bs, _v(pos))


func _v(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])
