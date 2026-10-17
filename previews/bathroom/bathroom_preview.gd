extends Node3D
## Bathroom look-dev with the game's greybox lights: room + props at layout.json, a stand-in mirror (SSR),
## optionally the Human at the `human` mark and every hidden effect shown.
## godot --path . res://previews/bathroom/bathroom_preview.tscn -- --capture NAME [--size 1200x675]
##   [--human [--human-model ID]] [--fx] [--fall --t 3] [--door DEG (Hinge open angle)] [--shots "name@eye@look[@fov];..."]   (2-column contact sheet in screenshots/NAME.png)
## Named views: fp (first-person at the sink), reveal (game reveal mark), door, mirror (from the glass back).

const VIEWS := {
	'fp': ['0,1.6,0.25', '0,1.45,-0.7', 70.0],
	'reveal': ['1.35,1.6,1.0', '-0.3,0.85,-0.2', 60.0],
	'door': ['1.0,1.65,2.45', '-0.5,0.9,-0.2', 70.0],
	'mirror': ['0,1.58,-0.62', '0.3,1.2,2.6', 70.0],
	'tub': ['-0.35,1.55,2.0', '-1.15,0.5,0.3', 60.0],
	'toilet': ['0.75,1.5,1.5', '1.2,0.8,-0.45', 60.0],
	'inmirror': ['0,1.6,-1.53', '0,1.58,2.6', 38.3, 0.88],   # the human eye reflected in the glass: what the mirror shows
	'hall': ['0.2,1.5,1.2', '1.0,1.1,3.0', 60.0],
	'gap': ['0.7,0.6,1.7', '1.0,0.0,2.6', 50.0],
}
const HIDDEN := ['Glob', 'Splats', 'Stream', 'Puddle', 'Drops']

var camera: Camera3D
var human: Node3D


func _ready() -> void:
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	var args := OS.get_cmdline_user_args()
	_lights()
	add_child(load('res://bathroom/art/bathroom_room.tscn').instantiate())
	var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string('res://bathroom/art/layout.json'))
	for id in layout.props:
		var p: Array = layout.props[id]
		var holder := Node3D.new()
		holder.name = id
		holder.position = Vector3(p[0], p[1], p[2])
		add_child(holder)
		holder.add_child(load('res://bathroom/art/props/%s.tscn' % id).instantiate())
		if not '--fx' in args:
			for n in HIDDEN:
				var h := holder.find_child(n, true, false)
				if h:
					h.visible = false
			if id == 'smudge':
				holder.visible = false
	_mirror(layout.mirror_glass)
	var hl := OmniLight3D.new()                        # the game's warm hall light (art ships the lamp mesh only)
	hl.position = Vector3(layout.hall_light[0], layout.hall_light[1], layout.hall_light[2])
	hl.light_color = Color(1.0, 0.82, 0.6)
	hl.light_energy = 1.6
	hl.omni_range = 3.0
	add_child(hl)
	if args.has('--door'):
		find_child('Hinge', true, false).rotation_degrees.y = float(args[args.find('--door') + 1])
	if '--human' in args:
		var hm := args[args.find('--human-model') + 1] if '--human-model' in args else ''   # character mock id
		human = load('res://previews/characters/mock/%s/human.glb' % hm if hm else 'res://previews/human/human_A.glb').instantiate()
		human.position = Vector3(0, 0, 0.2)
		add_child(human)
		_rest_pose(human)
		var rig: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(
				'res://previews/characters/mock/%s/human_rig.json' % hm if hm else 'res://human/art/human_rig.json'))
		for n in rig.hidden:                               # the rig json's start-hidden face parts
			var x := human.find_child(n, true, false)
			if x:
				x.visible = false
	if '--fall' in args:                                # rigged Human tipping toward the tub, ragdoll on
		var fh: Node3D = load('res://human/art/human.tscn').instantiate()
		fh.position = Vector3(-0.55, 0, 0.75)
		fh.rotation_degrees = Vector3(0, 0, 12)
		add_child(fh)
		_rest_pose(fh)
		_drop.call_deferred(fh)
	camera = Camera3D.new()
	camera.near = 0.02
	add_child(camera)
	camera.current = true
	_view('fp')
	var ci := args.find('--capture')
	if ci >= 0:
		_capture(args[ci + 1])


func _rest_pose(h: Node) -> void:                  # arms are bound in an A-pose; `rest` hangs them
	for ap in h.find_children('*', 'AnimationPlayer', true, false):
		ap.play('rest')
		ap.seek(0.0, true)


func _drop(h: Node3D) -> void:
	await get_tree().physics_frame
	h.get_node('Rig/Skeleton/Ragdoll').physical_bones_start_simulation()


func _lights() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.75, 0.85, 0.92)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.95, 0.97, 1)
	env.ambient_light_energy = 0.6
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.ssr_enabled = true
	env.ssao_enabled = true
	env.ssao_radius = 0.4
	env.ssao_intensity = 1.5
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-60, 25, 0)
	sun.light_energy = 0.6
	sun.shadow_enabled = true
	add_child(sun)
	var vl: Dictionary = JSON.parse_string(FileAccess.get_file_as_string('res://bathroom/art/layout.json')).vanity_light
	var spot := SpotLight3D.new()                      # the game's vanity light (layout.json vanity_light)
	add_child(spot)
	spot.position = Vector3(vl.pos[0], vl.pos[1], vl.pos[2])
	spot.look_at(Vector3(vl.aim[0], vl.aim[1], vl.aim[2]))
	spot.light_color = Color(vl.color[0], vl.color[1], vl.color[2])
	spot.light_energy = vl.energy
	spot.spot_range = vl.range
	spot.spot_angle = vl.angle
	spot.light_size = vl.light_size
	spot.shadow_enabled = true
	var lamp := OmniLight3D.new()
	lamp.position = Vector3(0, 2.4, 0.4)
	lamp.light_color = Color(1, 0.95, 0.85)
	lamp.light_energy = 1.4
	lamp.omni_range = 5.0
	lamp.shadow_enabled = true
	add_child(lamp)


## Stand-in for the game's planar-reflection glass (the art never ships glass).
func _mirror(g: Dictionary) -> void:
	var q := MeshInstance3D.new()
	var qm := QuadMesh.new()
	qm.size = Vector2(g.size[0], g.size[1])
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.8, 0.86, 0.88)        # flat stand-in: the game draws a planar reflection here
	m.roughness = 0.15
	m.metallic_specular = 1.0
	qm.material = m
	q.mesh = qm
	q.position = Vector3(g.center[0], g.center[1], g.center[2])
	add_child(q)


func _vec(s: String) -> Vector3:
	var p := s.split(',')
	return Vector3(float(p[0]), float(p[1]), float(p[2]))


func _view(name: String) -> void:
	var v: Array = VIEWS[name]
	if human:
		human.visible = name != 'fp'          # in game the body is on layer 2, hidden from the first-person camera
	camera.position = _vec(v[0])
	camera.look_at(_vec(v[1]))
	camera.fov = v[2]
	camera.near = v[3] if v.size() > 3 else 0.02           # inmirror: start at the glass


func _capture(name: String) -> void:
	var args := OS.get_cmdline_user_args()
	var size := Vector2i(1200, 675)
	var si := args.find('--size')
	if si >= 0:
		var p := args[si + 1].split('x')
		size = Vector2i(int(p[0]), int(p[1]))
	get_window().size = size
	var dir := 'res://previews/bathroom/screenshots/'
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	for n in 10:
		await get_tree().process_frame
	if '--t' in args:
		await get_tree().create_timer(float(args[args.find('--t') + 1])).timeout
	var spec := 'fp;reveal;door;mirror'
	var sh := args.find('--shots')
	if sh >= 0:
		spec = args[sh + 1]
	var items := spec.split(';', false)
	var tiles: Array[Image] = []
	for item in items:
		var part := item.split('@')
		if part.size() == 1:
			_view(part[0])
		else:
			camera.position = _vec(part[1])
			camera.look_at(_vec(part[2]))
			camera.fov = float(part[3]) if part.size() > 3 else 60.0
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
	print('BATHROOM_SHEET ', dir + name + '.png')
	get_tree().quit()
