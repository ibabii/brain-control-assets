extends Node3D
## The Human rig look-dev (art: human/art/human.tscn). Modes:
##   pose    strong bone rotations side by side (deformation check)
##   ik      TwoBoneIK3D reaching (arms to a counter and overhead, a foot onto a step) with the json poles
##   hands   finger clips: grip, relaxed, spread
##   ragdoll drop onto the floor, captured after --t seconds (default 3)
## godot --path . res://previews/human/human_rig_preview.tscn -- --capture NAME --mode pose [--shots "name@eye@look[@fov];..."]

const POSES := {   # bone: [local axis, degrees] applied on top of the rest pose
	'arms_up': {'RightUpperArm': [Vector3.FORWARD, -100], 'LeftUpperArm': [Vector3.RIGHT, -110], 'LeftLowerArm': [Vector3.RIGHT, -60],
		'Head': [Vector3.UP, 30], 'Spine': [Vector3.RIGHT, -12]},
	'sit': {'LeftUpperLeg': [Vector3.RIGHT, -85], 'RightUpperLeg': [Vector3.RIGHT, -85], 'LeftLowerLeg': [Vector3.RIGHT, 90],
		'RightLowerLeg': [Vector3.RIGHT, 90], 'RightLowerArm': [Vector3.RIGHT, -80], 'Chest': [Vector3.RIGHT, 10]},
	'twist': {'Spine': [Vector3.UP, 25], 'Chest': [Vector3.UP, 20], 'Neck': [Vector3.FORWARD, 20], 'LeftUpperArm': [Vector3.FORWARD, 60],
		'RightUpperLeg': [Vector3.FORWARD, 30]},
}

var camera: Camera3D
var humans: Array[Node3D] = []
var data: Dictionary


func _ready() -> void:
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	data = JSON.parse_string(FileAccess.get_file_as_string('res://human/art/human_rig.json'))
	_stage()
	camera = Camera3D.new()
	camera.fov = 30
	camera.near = 0.02
	add_child(camera)
	camera.current = true
	var args := OS.get_cmdline_user_args()
	var mode := args[args.find('--mode') + 1] if '--mode' in args else 'pose'
	match mode:
		'pose':
			var i := 0
			for p in POSES:
				var h := _human(Vector3((1 - i) * 1.0, 0, 0))
				_pose(h, POSES[p])
				i += 1
		'ik':
			_ik_scene()
		'hands':
			var i := 0
			for c in ['grip', 'relaxed', 'spread']:
				var h := _human(Vector3((1 - i) * 0.7, 0, 0))
				_clip(h, 'hand_%s_L' % c)
				_clip(h, 'hand_%s_R' % c)
				i += 1
		'ragdoll':
			_ragdoll()
	if '--capture' in args:
		_capture(args[args.find('--capture') + 1])


func _human(pos: Vector3) -> Node3D:
	var h: Node3D = load('res://human/art/human.tscn').instantiate()
	h.position = pos
	add_child(h)
	humans.append(h)
	for v in h.find_children('*', 'VisualInstance3D', true, false):
		v.layers = 1                              # the preview camera sees layer 1 only
	return h


func _skel(h: Node3D) -> Skeleton3D:
	return h.get_node('Rig/Skeleton')


func _pose(h: Node3D, pose: Dictionary) -> void:
	var sk := _skel(h)
	for b in pose:
		var i := sk.find_bone(b)
		var q := Quaternion(pose[b][0], deg_to_rad(pose[b][1]))
		sk.set_bone_pose_rotation(i, sk.get_bone_rest(i).basis.get_rotation_quaternion() * q)


func _clip(h: Node3D, clip: String) -> void:
	var sk := _skel(h)
	var a: Animation = h.get_node('Anim').get_animation(clip)
	for t in a.get_track_count():
		var i := sk.find_bone(a.track_get_path(t).get_concatenated_subnames())
		if i >= 0 and a.track_get_type(t) == Animation.TYPE_ROTATION_3D:
			sk.set_bone_pose_rotation(i, a.rotation_track_interpolate(t, 0.0))


func _v(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])


## Left: hands on a counter top (0.87) in front; right: one hand overhead; both: right foot on a 20 cm step.
func _ik_scene() -> void:
	for k in 2:
		var h := _human(Vector3((0.5 - k) * 1.0, 0, 0))
		var sk := _skel(h)
		var ik := TwoBoneIK3D.new()
		sk.add_child(ik)
		var goals := []
		if k == 0:
			goals = [['Left', 'arm', Vector3(-0.2, 0.9, -0.38)], ['Right', 'arm', Vector3(0.2, 0.9, -0.38)]]
			var counter := MeshInstance3D.new()
			var bm := BoxMesh.new()
			bm.size = Vector3(0.8, 0.87, 0.4)
			counter.mesh = bm
			counter.position = h.position + Vector3(0, 0.435, -0.62)
			add_child(counter)
		else:
			goals = [['Right', 'arm', Vector3(0.18, 1.95, -0.1)], ['Left', 'arm', Vector3(-0.35, 1.25, -0.25)]]
		goals.append(['Right', 'leg', Vector3(0.14, 0.3, -0.3)])
		var step := MeshInstance3D.new()
		var sm := BoxMesh.new()
		sm.size = Vector3(0.3, 0.2, 0.35)
		step.mesh = sm
		step.position = h.position + Vector3(0.14, 0.1, -0.3)
		add_child(step)
		ik.setting_count = goals.size()
		for i in goals.size():
			var g: Array = goals[i]
			var chain: Array = data.ik[g[0]][g[1]]
			ik.set_root_bone_name(i, chain[0])
			ik.set_middle_bone_name(i, chain[1])
			ik.set_end_bone_name(i, chain[2])
			var t := Marker3D.new()
			t.position = g[2] + (Vector3(0, 0.095, 0) if g[1] == 'leg' else Vector3.ZERO)
			sk.add_child(t)
			ik.set_target_node(i, ik.get_path_to(t))
			var p := Marker3D.new()
			p.position = _v(data.ik[g[0]]['elbow_pole' if g[1] == 'arm' else 'knee_pole'])
			sk.add_child(p)
			ik.set_pole_node(i, ik.get_path_to(p))


func _ragdoll() -> void:
	var h := _human(Vector3.ZERO)
	h.rotation_degrees = Vector3(10, 25, 0)
	var floor := StaticBody3D.new()
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(10, 1, 10)
	col.shape = box
	col.position = Vector3(0, -0.5, 0)
	floor.add_child(col)
	add_child(floor)
	await get_tree().physics_frame
	_skel(h).get_node('Ragdoll').physical_bones_start_simulation()


func _stage() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color('#E9DCC6')
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(1, 0.93, 0.86)
	env.ambient_light_energy = 0.55
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var key := DirectionalLight3D.new()
	key.light_color = Color(1, 0.92, 0.8)
	key.light_energy = 1.2
	key.shadow_enabled = true
	key.rotation_degrees = Vector3(-38, 150, 0)
	add_child(key)
	var floor := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(8, 8)
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color('#F1E4CF')
	pm.material = fm
	floor.mesh = pm
	add_child(floor)


func _capture(name: String) -> void:
	var args := OS.get_cmdline_user_args()
	var size := Vector2i(1200, 900)
	if '--size' in args:
		var p := args[args.find('--size') + 1].split('x')
		size = Vector2i(int(p[0]), int(p[1]))
	get_window().size = size
	var wait := float(args[args.find('--t') + 1]) if '--t' in args else 0.3
	var dir := 'res://previews/human/screenshots/'
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	for n in 10:
		await get_tree().process_frame
	await get_tree().create_timer(wait).timeout
	var spec: String = args[args.find('--shots') + 1] if '--shots' in args else 'front@0,1.0,-5@0,0.9,0'
	var items := spec.split(';', false)
	var tiles: Array[Image] = []
	for item in items:
		var part := item.split('@')
		camera.position = Vector3(float(part[1].split(',')[0]), float(part[1].split(',')[1]), float(part[1].split(',')[2]))
		camera.look_at(Vector3(float(part[2].split(',')[0]), float(part[2].split(',')[1]), float(part[2].split(',')[2])))
		camera.fov = float(part[3]) if part.size() > 3 else 30.0
		for n in 4:
			await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		if items.size() > 1:
			img.resize(800, int(800.0 * img.get_height() / img.get_width()))
		tiles.append(img)
	var tw := tiles[0].get_width()
	var th := tiles[0].get_height()
	var cols := mini(2, tiles.size())
	var sheet := Image.create(tw * cols, th * ceili(tiles.size() / float(cols)), false, tiles[0].get_format())
	for i in tiles.size():
		sheet.blit_rect(tiles[i], Rect2i(0, 0, tw, th), Vector2i((i % cols) * tw, (i / cols) * th))
	sheet.save_png(dir + name + '.png')
	print('HUMAN_SHEET ', dir + name + '.png')
	get_tree().quit()
