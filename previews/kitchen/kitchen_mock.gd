extends Node3D
## E01 kitchen blockout mock (art_direction.md "E01 kitchen + props"): colour blocks only, no detail. Captured from
## Bernard's first-person camera (game: eye 1.62 m, pitch -30, vertical FOV 70; src/human/human_avatar.tscn).
## godot --path . res://previews/kitchen/kitchen_mock.tscn -- --capture NAME [--size 1280x720]
## Layout: Bernard starts at (0, 0.5) facing -Z; counter on the back wall (z -3), window on the left wall, table
## right of centre (roommate seated facing Bernard), doorway right-front (2.2, 0.8) -> 2 m hallway -> front door.

const CREAM := '#F1E4CF'
const TEAL := '#2D5C5B'
const PEACH := '#EAA78B'
const HONEY := '#C9925A'          # honey wood (warmer/darker than the hoodie's honey ochre)
const CLAY := '#C98778'
const PORCELAIN := '#F8F4EA'
const GRAPHITE := '#454C48'
const TERRACOTTA := '#C87F5E'

# shots: name, eye position, yaw (deg, + = left), pitch (deg)
const SHOTS := [
	['beat 2: at the machine', Vector3(-0.8, 1.62, -1.95), 0.0, -30.0],
	['beat 7: toast pops, roommate in frame', Vector3(-0.55, 1.62, -0.65), -34.0, -30.0],
	['beat 11: to the front door', Vector3(2.2, 1.62, 0.8), -90.0, -30.0],
	['overview (ceiling + front wall off)', Vector3(-0.6, 5.2, 4.6), 0.0, -48.0],
]

var cam: Camera3D


func _ready() -> void:
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	_env()
	_room()
	_counter()
	_table()
	_hall()
	_roommate()
	cam = Camera3D.new()
	cam.fov = 70.0
	add_child(cam)
	cam.current = true
	_capture()


func _mat(c: String, rough := 0.8, emit := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(c)
	m.roughness = maxf(rough, 0.6)                    # no reflective surfaces
	if emit > 0.0:
		m.emission_enabled = true
		m.emission = Color(c)
		m.emission_energy_multiplier = emit
	return m


func box(pos: Vector3, size: Vector3, c: String, rough := 0.8, emit := 0.0) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var b := BoxMesh.new()
	b.size = size
	mi.mesh = b
	mi.position = pos
	mi.material_override = _mat(c, rough, emit)
	add_child(mi)
	return mi


func cyl(pos: Vector3, r: float, h: float, c: String) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var b := CylinderMesh.new()
	b.top_radius = r
	b.bottom_radius = r
	b.height = h
	mi.mesh = b
	mi.position = pos
	mi.material_override = _mat(c)
	add_child(mi)
	return mi


func _env() -> void:
	var we := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color('#DDE6EA')
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color('#B9C6D6')          # soft cool fill
	e.ambient_light_energy = 1.0
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	we.environment = e
	add_child(we)
	var sun := DirectionalLight3D.new()               # warm low morning sun from the left, through the window
	sun.light_color = Color('#FFE2B8')
	sun.light_energy = 2.2
	sun.shadow_enabled = true
	sun.rotation_degrees = Vector3(-24, -100, 0)
	add_child(sun)
	var fill := OmniLight3D.new()                     # soft room fill under the ceiling
	fill.position = Vector3(0, 2.3, -0.6)
	fill.light_color = Color('#FFF1DE')
	fill.light_energy = 1.2
	fill.omni_range = 6.0
	add_child(fill)


func _room() -> void:
	for i in 12:                                      # terracotta/cream checker, 0.5 m tiles
		for j in 10:
			box(Vector3(-2.75 + i * 0.5, -0.01, -2.75 + j * 0.5), Vector3(0.5, 0.02, 0.5),
				TERRACOTTA if (i + j) % 2 else CREAM, 0.85)
	var h := 2.6
	box(Vector3(0, h / 2, -3.05), Vector3(6.2, h, 0.1), CREAM)                    # back wall
	box(Vector3(0, h / 2, 2.05), Vector3(6.2, h, 0.1), CREAM).add_to_group('roof')    # front wall
	box(Vector3(0, h + 0.05, -0.5), Vector3(6.2, 0.1, 5.2), PORCELAIN).add_to_group('roof')   # ceiling
	# left wall with the window (z -2.3 .. -1.3, y 1.0 .. 2.0)
	box(Vector3(-3.05, h / 2, 0.35), Vector3(0.1, h, 3.3), CREAM)
	box(Vector3(-3.05, h / 2, -2.65), Vector3(0.1, h, 0.7), CREAM)
	box(Vector3(-3.05, 0.5, -1.8), Vector3(0.1, 1.0, 1.0), CREAM)
	box(Vector3(-3.05, 2.3, -1.8), Vector3(0.1, 0.6, 1.0), CREAM)
	box(Vector3(-3.06, 1.5, -1.8), Vector3(0.02, 1.0, 1.0), '#FFF6E6', 0.9, 0.6)  # frosted pane (emissive, no glass)
	box(Vector3(-3.0, 1.0, -1.8), Vector3(0.14, 0.04, 1.08), PORCELAIN)          # sill
	# right wall with the doorway (z 0.35 .. 1.25, 2.1 high)
	box(Vector3(3.05, h / 2, -1.33), Vector3(0.1, h, 3.36), CREAM)
	box(Vector3(3.05, h / 2, 1.65), Vector3(0.1, h, 0.8), CREAM)
	box(Vector3(3.05, 2.35, 0.8), Vector3(0.1, 0.5, 0.9), CREAM)
	box(Vector3(3.0, 1.05, 0.33), Vector3(0.16, 2.1, 0.05), CLAY)               # door frame
	box(Vector3(3.0, 1.05, 1.27), Vector3(0.16, 2.1, 0.05), CLAY)


func _counter() -> void:
	box(Vector3(-0.5, 0.43, -2.7), Vector3(3.4, 0.86, 0.6), TEAL)                # deep teal lower cabinets
	for x in [-1.95, -1.1, -0.25, 0.6]:                                          # door gaps read as panels
		box(Vector3(x, 0.45, -2.395), Vector3(0.012, 0.7, 0.01), '#244A49')
	box(Vector3(-0.5, 0.88, -2.68), Vector3(3.46, 0.04, 0.66), PORCELAIN, 0.7)    # worktop (brightest group)
	for i in 17:                                                                  # peach tile backsplash
		for j in 4:
			box(Vector3(-2.15 + i * 0.2, 1.0 + j * 0.15, -2.995), Vector3(0.19, 0.14, 0.01), PEACH, 0.75)
	box(Vector3(-0.5, 1.88, -2.82), Vector3(3.4, 0.7, 0.35), CREAM)              # cream uppers
	box(Vector3(1.65, 0.95, -2.6), Vector3(0.8, 1.9, 0.7), PORCELAIN, 0.7)        # fridge
	box(Vector3(1.65, 1.35, -2.244), Vector3(0.05, 0.4, 0.02), GRAPHITE)
	for p in [Vector3(1.4, 1.55, -2.24), Vector3(1.85, 1.62, -2.24), Vector3(1.55, 1.2, -2.24)]:
		box(p, Vector3(0.05, 0.05, 0.015), CLAY)                                  # magnets
	box(Vector3(1.85, 1.25, -2.243), Vector3(0.14, 0.2, 0.01), PORCELAIN)       # TODAY-style notepad
	# props on the worktop, left to right: phone spot, coffee machine, mug spot, (clear), toaster
	box(Vector3(-1.45, 0.91, -2.62), Vector3(0.08, 0.012, 0.15), GRAPHITE)        # phone
	box(Vector3(-0.8, 1.05, -2.72), Vector3(0.24, 0.3, 0.26), TEAL)               # coffee machine body
	box(Vector3(-0.8, 1.06, -2.585), Vector3(0.2, 0.22, 0.01), CREAM)             # cream front panel
	box(Vector3(-0.8, 1.25, -2.74), Vector3(0.14, 0.1, 0.14), '#E9E1D2')          # matte bean hopper
	cyl(Vector3(-0.45, 0.95, -2.55), 0.045, 0.1, CREAM)                           # Bernard's mug
	cyl(Vector3(-0.45, 0.955, -2.55), 0.047, 0.018, PEACH)                        # its peach band
	box(Vector3(0.8, 1.0, -2.62), Vector3(0.28, 0.2, 0.18), PEACH)                # toaster
	box(Vector3(0.8, 1.105, -2.62), Vector3(0.2, 0.012, 0.03), GRAPHITE)          # slots
	cyl(Vector3(-2.0, 1.0, -2.62), 0.08, 0.2, CLAY)                               # kettle
	box(Vector3(0.1, 0.65, -2.38), Vector3(0.22, 0.38, 0.02), PEACH, 0.9)        # tea towel


func _table() -> void:
	var c := Vector3(0.9, 0, -0.9)
	box(c + Vector3(0, 0.74, 0), Vector3(1.0, 0.05, 0.75), HONEY)
	for dx in [-0.44, 0.44]:
		for dz in [-0.32, 0.32]:
			box(c + Vector3(dx, 0.36, dz), Vector3(0.06, 0.72, 0.06), HONEY)
	cyl(c + Vector3(-0.25, 0.8, 0.1), 0.12, 0.07, CREAM)                            # fruit bowl
	for p in [Vector3(-0.29, 0.86, 0.12), Vector3(-0.21, 0.86, 0.08)]:
		cyl(c + p, 0.035, 0.06, CLAY)
	_chair(Vector3(0.9, 0, -1.55), 0.0)                                            # the roommate's, back to the counter
	_chair(Vector3(0.22, 0, -0.9), 90.0)


func _chair(p: Vector3, yaw: float) -> void:
	var n := Node3D.new()
	n.position = p
	n.rotation_degrees.y = yaw
	add_child(n)
	var parts := [[Vector3(0, 0.45, 0), Vector3(0.44, 0.04, 0.42)], [Vector3(0, 0.75, -0.2), Vector3(0.44, 0.5, 0.04)]]
	for dx in [-0.19, 0.19]:
		for dz in [-0.18, 0.18]:
			parts.append([Vector3(dx, 0.22, dz), Vector3(0.04, 0.45, 0.04)])
	for q in parts:
		var b := box(Vector3.ZERO, q[1], HONEY)
		b.reparent(n, false)
		b.position = q[0]


func _hall() -> void:
	# 2 m hallway past the doorway (x 3.1 .. 5.1, z 0.25 .. 1.35), front door at the end, coat hook + shoe rack
	box(Vector3(4.1, -0.01, 0.8), Vector3(2.1, 0.02, 1.2), '#B98A62', 0.85)       # wood floor
	box(Vector3(4.1, 1.3, 0.2), Vector3(2.1, 2.6, 0.1), CREAM)
	box(Vector3(4.1, 1.3, 1.4), Vector3(2.1, 2.6, 0.1), CREAM)
	box(Vector3(4.1, 2.65, 0.8), Vector3(2.1, 0.1, 1.3), PORCELAIN).add_to_group('roof')
	box(Vector3(5.15, 1.3, 0.8), Vector3(0.1, 2.6, 1.3), CREAM)
	box(Vector3(5.09, 1.02, 0.8), Vector3(0.04, 2.04, 0.9), CLAY)                # front door
	box(Vector3(5.05, 1.0, 1.12), Vector3(0.05, 0.05, 0.1), GRAPHITE)           # handle
	box(Vector3(4.6, 1.75, 1.33), Vector3(0.3, 0.04, 0.04), HONEY)               # coat hook rail
	box(Vector3(4.6, 1.35, 1.25), Vector3(0.32, 0.75, 0.14), '#6B7C8C')          # coat
	box(Vector3(3.8, 0.25, 1.2), Vector3(0.9, 0.04, 0.3), HONEY)                 # shoe rack: 2 shelves
	box(Vector3(3.8, 0.5, 1.2), Vector3(0.9, 0.04, 0.3), HONEY)
	for i in 4:                                                                   # full of shoes (no slippers)
		for k in 2:
			var col: String = [GRAPHITE, '#6B4E3A', PORCELAIN, '#3D5560'][(i + k) % 4]
			box(Vector3(3.45 + i * 0.22, 0.31 + k * 0.25, 1.2), Vector3(0.1, 0.08, 0.24), col)


func _roommate() -> void:
	var over := {'parts': {'hair': 'hair_curly_m', 'top': 'tshirt_m', 'outer': 'overshirt_m'},
		'colors': {'top': '#EFE6D2', 'rib': '#D8CDB6', 'outer': '#26324A', 'bottom': '#4A4D52', 'hair': '#2A1E1A',
			'skin': '#C98B66'}}
	var r: Node3D = CharacterAssembler.build('male_base', over)
	add_child(r)
	r.rotation_degrees.y = 180.0                      # faces Bernard (+Z)
	var ap: AnimationPlayer = r.get_node('Anim')
	ap.play('sit_tub')
	ap.seek(ap.current_animation_length, true)
	var sk: Skeleton3D = r.find_children('*', 'Skeleton3D', true, false)[0]
	await get_tree().process_frame
	var hips := (sk.global_transform * sk.get_bone_global_pose(sk.find_bone('Hips'))).origin
	r.global_position += Vector3(0.9, 0, -1.5) - Vector3(hips.x, 0, hips.z) + Vector3(0, 0.56 - hips.y, 0)


func _capture() -> void:
	var size := Vector2i(1280, 720)
	var args := OS.get_cmdline_user_args()
	if '--size' in args:
		var p := args[args.find('--size') + 1].split('x')
		size = Vector2i(int(p[0]), int(p[1]))
	get_window().size = size
	var name := args[args.find('--capture') + 1] if '--capture' in args else 'kitchen_mock'
	for n in 12:
		await get_tree().process_frame
	var cl := CanvasLayer.new()
	add_child(cl)
	var label := Label.new()
	label.position = Vector2(14, 8)
	label.add_theme_font_size_override('font_size', size.y / 22)
	label.add_theme_color_override('font_color', Color('#2E2624'))
	cl.add_child(label)
	var tiles: Array[Image] = []
	for s in SHOTS:
		cam.position = s[1]
		cam.rotation_degrees = Vector3(s[3], s[2], 0)
		label.text = s[0]
		for n in get_tree().get_nodes_in_group('roof'):
			n.visible = not String(s[0]).begins_with('overview')
		for n in 4:
			await RenderingServer.frame_post_draw
		tiles.append(get_viewport().get_texture().get_image())
	var w := tiles[0].get_width()
	var h := tiles[0].get_height()
	var sheet := Image.create(w * 2, h * 2, false, tiles[0].get_format())
	for i in tiles.size():
		sheet.blit_rect(tiles[i], Rect2i(0, 0, w, h), Vector2i((i % 2) * w, (i / 2) * h))
	var dir := 'res://previews/kitchen/screenshots/'
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	sheet.save_png(dir + name + '.png')
	print('KITCHEN_SHEET ', dir + name + '.png')
	get_tree().quit()
