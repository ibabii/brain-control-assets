extends Node3D
## The Human look-dev: neutral warm studio, one model, the colourway line-up, or the expression line-up.
## godot --path . res://previews/human/human_preview.tscn -- --capture NAME [--size 1200x900]
##   [--mode single|lineup|faces] [--shots "name@eye@look;..."]  (2-column contact sheet in screenshots/NAME.png)
## Expressions only move nodes and toggle visibility (the art contract): see EXPR.

const MODELS := {'A': 'res://previews/human/human_A.glb', 'B': 'res://previews/human/human_B.glb',
	'C': 'res://previews/human/human_C.glb'}
const HIDDEN := ['Open', 'Tongue', 'Teeth', 'Grimace', 'GrimaceLine', 'BlushL', 'BlushR']
## lid: upper-lid X rotation (deg, + = open); brow: (raise m, tilt deg, + = inner end up); look: gaze (yaw, pitch);
## pupil: scale; show: mouth/blush parts made visible (Smile hides when another mouth shows).
const EXPR := {
	'neutral': {'lid': 45.0, 'brow': [0.0, 0.0], 'look': [0.0, 0.0], 'pupil': 1.0, 'show': []},
	'happy': {'lid': 30.0, 'brow': [0.010, -8.0], 'look': [0.0, 4.0], 'pupil': 1.08, 'show': ['Open', 'Tongue'], 'mouth': 1.0},
	'panic': {'lid': 75.0, 'brow': [0.009, 18.0], 'look': [0.0, 0.0], 'pupil': 0.74, 'show': ['Open'], 'mouth': 1.35},
	'sleepy': {'lid': -22.0, 'brow': [-0.006, -4.0], 'look': [0.0, -6.0], 'pupil': 1.0, 'show': []},
	'embarrassed': {'lid': 20.0, 'brow': [0.008, 20.0], 'look': [-16.0, -8.0], 'pupil': 1.0,
		'show': ['Grimace', 'GrimaceLine', 'BlushL', 'BlushR']},
}

var camera: Camera3D
var humans: Array[Node3D] = []


func _ready() -> void:
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	_stage()
	var args := OS.get_cmdline_user_args()
	var mode := 'single'
	var mi := args.find('--mode')
	if mi >= 0:
		mode = args[mi + 1]
	match mode:
		'lineup':
			for i in 3:
				_add(MODELS.values()[i], Vector3((1 - i) * 0.9, 0, 0), 'neutral')
		'faces':
			var names := EXPR.keys()
			for i in names.size():
				_add(MODELS['A'], Vector3((2 - i) * 0.42, 0, 0), names[i])   # camera looks +Z: screen left = +X
		_:
			_add(MODELS['A'], Vector3.ZERO, 'neutral')
	camera = Camera3D.new()
	camera.fov = 30
	camera.near = 0.02
	add_child(camera)
	camera.current = true
	camera.position = Vector3(0, 1.0, -4.2)
	camera.look_at(Vector3(0, 0.9, 0))
	var ci := args.find('--capture')
	if ci >= 0:
		_capture(args[ci + 1])


func _add(path: String, pos: Vector3, expr: String) -> void:
	var h: Node3D = load(path).instantiate()
	h.position = pos
	add_child(h)
	humans.append(h)
	_expression(h, expr)


func _expression(h: Node3D, name: String) -> void:
	var e: Dictionary = EXPR[name]
	for n in HIDDEN:
		_find(h, n).visible = false
	_find(h, 'Smile').visible = true
	for n in e.show:
		_find(h, n).visible = true
		if n in ['Open', 'Grimace']:
			_find(h, 'Smile').visible = false
	for side in ['L', 'R']:
		var s := -1.0 if side == 'L' else 1.0
		var lid := _find(h, 'Lid' + side)
		lid.rotation_degrees.x = e.lid
		var brow := _find(h, 'Brow' + side)
		brow.position.y += e.brow[0]
		brow.rotation_degrees.z = -s * e.brow[1]
		var look := _find(h, 'Look' + side)
		look.rotation_degrees = Vector3(e.look[1], e.look[0], 0)
		for p in ['Pupil', 'Glint']:
			var n := _find(h, p + side)
			n.scale = Vector3(e.pupil, e.pupil, 1.0)   # flat scale: the decal stays on the eye
	var m: float = e.get('mouth', 1.0)
	for n in ['Open', 'Tongue']:
		_find(h, n).scale = Vector3(m, m * 1.25, 1.0) if m != 1.0 else Vector3.ONE


func _find(h: Node, n: String) -> Node3D:
	var x: Node3D = h.find_child(n, true, false)
	assert(x != null, 'missing node ' + n)
	return x


func _stage() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color('#E9DCC6')
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(1, 0.93, 0.86)
	env.ambient_light_energy = 0.55
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.ssao_enabled = true
	env.ssao_radius = 0.3
	env.ssao_intensity = 1.6
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var key := DirectionalLight3D.new()
	key.light_color = Color(1, 0.92, 0.8)
	key.light_energy = 1.25
	key.shadow_enabled = true
	key.shadow_blur = 1.5
	key.rotation_degrees = Vector3(-38, 150, 0)
	add_child(key)
	var rim := DirectionalLight3D.new()
	rim.light_color = Color(0.85, 0.92, 1)
	rim.light_energy = 0.45
	rim.rotation_degrees = Vector3(-20, -20, 0)
	add_child(rim)
	var floor_mesh := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(8, 8)
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color('#F1E4CF')
	fm.roughness = 0.8
	pm.material = fm
	floor_mesh.mesh = pm
	add_child(floor_mesh)
	var wall := MeshInstance3D.new()
	var wm := PlaneMesh.new()
	wm.size = Vector2(8, 4)
	var wmat := StandardMaterial3D.new()
	wmat.albedo_color = Color('#BAC6B2')
	wmat.roughness = 0.85
	wm.material = wmat
	wall.mesh = wm
	wall.rotation_degrees = Vector3(-90, 0, 0)
	wall.position = Vector3(0, 2, 1.6)
	add_child(wall)


func _vec(s: String) -> Vector3:
	var p := s.split(',')
	return Vector3(float(p[0]), float(p[1]), float(p[2]))


func _capture(name: String) -> void:
	var args := OS.get_cmdline_user_args()
	var size := Vector2i(1200, 900)
	var si := args.find('--size')
	if si >= 0:
		var p := args[si + 1].split('x')
		size = Vector2i(int(p[0]), int(p[1]))
	get_window().size = size
	var dir := 'res://previews/human/screenshots/'
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	for n in 10:
		await get_tree().process_frame
	var spec := 'front@0,1.0,-4.2@0,0.9,0'
	var sh := args.find('--shots')
	if sh >= 0:
		spec = args[sh + 1]
	var tiles: Array[Image] = []
	for item in spec.split(';', false):
		var part := item.split('@')
		camera.position = _vec(part[1])
		camera.look_at(_vec(part[2]))
		if part.size() > 3:
			camera.fov = float(part[3])
		for n in 4:
			await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		if spec.count('@') > 3:          # several shots: 800 px tiles; one shot keeps full size
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
