@tool
extends EditorScenePostImport
## Post-import for hands/art/hand_[rl].glb (contract: coordination/interfaces.md "Hand art").
## Renames to the agreed names (Rig/Skeleton, Anim), marks loops, adds the "hit" animation markers and
## the Contact_*/Grip markers on bones, using hands/art/hand_rig.json written by scripts/hands/build.py.

const SKEL_FROM := "Skeleton/Skeleton3D"
const SKEL_TO := "Rig/Skeleton"


func _post_import(scene: Node) -> Object:
	var side := "l" if get_source_file().ends_with("hand_l.glb") else "r"
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://hands/art/hand_rig.json"))[side]
	var rig: Node3D = scene.get_node("Skeleton")
	rig.name = "Rig"
	var skel: Skeleton3D = rig.get_node("Skeleton3D")
	skel.name = "Skeleton"
	var anim: AnimationPlayer = scene.get_node("AnimationPlayer")
	anim.name = "Anim"
	var lib := anim.get_animation_library("")
	for clip in lib.get_animation_list():
		var a := lib.get_animation(clip)
		for t in a.get_track_count():
			a.track_set_path(t, NodePath(String(a.track_get_path(t)).replace(SKEL_FROM, SKEL_TO)))
		if clip in data.loops:
			a.loop_mode = Animation.LOOP_LINEAR
		if data.hit.has(clip):
			a.add_marker("hit", data.hit[clip])
	var to_skel := (rig.transform * skel.transform).affine_inverse()
	for m in data.markers:
		_sample(skel, lib.get_animation(m.clip), m.time)
		var bone_pose := _global(skel, skel.find_bone(m.bone))
		var target := to_skel * Vector3(m.pos[0], m.pos[1], m.pos[2])
		var att := BoneAttachment3D.new()
		att.name = m.name + "_Bone"
		att.bone_name = m.bone
		skel.add_child(att)
		att.owner = scene
		var marker := Marker3D.new()
		marker.name = m.name
		marker.position = bone_pose.affine_inverse() * target
		att.add_child(marker)
		marker.owner = scene
	skel.reset_bone_poses()
	return scene


func _sample(skel: Skeleton3D, a: Animation, time: float) -> void:
	skel.reset_bone_poses()
	for t in a.get_track_count():
		var bone := skel.find_bone(a.track_get_path(t).get_concatenated_subnames())
		if bone < 0:
			continue
		match a.track_get_type(t):
			Animation.TYPE_ROTATION_3D:
				skel.set_bone_pose_rotation(bone, a.rotation_track_interpolate(t, time))
			Animation.TYPE_POSITION_3D:
				skel.set_bone_pose_position(bone, a.position_track_interpolate(t, time))
			Animation.TYPE_SCALE_3D:
				skel.set_bone_pose_scale(bone, a.scale_track_interpolate(t, time))


## Bone pose in skeleton space from the local poses just set (outside the tree the skeleton's own cache stays at rest).
func _global(skel: Skeleton3D, bone: int) -> Transform3D:
	var t := Transform3D(Basis(skel.get_bone_pose_rotation(bone)).scaled(skel.get_bone_pose_scale(bone)),
		skel.get_bone_pose_position(bone))
	var parent := skel.get_bone_parent(bone)
	return _global(skel, parent) * t if parent >= 0 else t
