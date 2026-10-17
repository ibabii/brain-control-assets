extends Node3D
## E01 kitchen blockout mock (art_direction.md "E01 kitchen + props"): colour blocks only, no detail. Captured from
## Bernard's first-person camera (game: eye 1.62 m, pitch -30, vertical FOV 70; src/human/human_avatar.tscn).
## godot --path . res://previews/kitchen/kitchen_mock.tscn -- --capture NAME [--size 1280x720]
## Layout (hybrid, orchestrator 2026-10-16): mechanics' footprint (game locations/breakfast): Bernard at the origin
## facing -Z, room x -2..2 / z -1.15..2.55, counter on the back wall (front at z -0.5), hallway LEFT (x -2..-5, z
## 0.25..1.35) to the front door. AD rules on top: window on the RIGHT wall toward the front (never behind the props),
## fridge at the counter's left end; counter ends at x 0.75 so a round table fits the right-back corner, roommate at
## it facing Bernard across the tabletop.

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
	['beat 2: at the machine', Vector3(-0.3, 1.62, -0.05), 0.0, -30.0],
	['beat 7: toast pops, roommate in frame', Vector3(0.0, 1.62, 0.0), -40.0, -30.0],
	['oblique: table + toast arc', Vector3(-0.6, 2.2, 1.6), -38.0, -28.0],
	['beat 11: to the front door', Vector3(-1.7, 1.62, 0.8), 90.0, -30.0],
	['overview (ceiling + front wall off)', Vector3(-0.9, 5.4, 5.6), 0.0, -48.0],
]

const CLOSE := [         # --close: prop/set detail shots (name, eye, yaw, pitch)
	['machine + mug', Vector3(-0.12, 1.2, -0.32), 25.0, -32.0],
	['toaster + phone', Vector3(0.3, 1.2, -0.3), -5.0, -40.0],
	['nook + table', Vector3(0.6, 1.45, 0.3), -50.0, -28.0],
	['parcel', Vector3(1.6, 0.95, 0.05), -20.0, -40.0],
	['fridge', Vector3(-1.0, 1.4, 0.6), 40.0, -14.0],
	['front door from the hall', Vector3(-2.6, 1.5, 0.8), 90.0, -12.0],
]

var cam: Camera3D
var roommate: Node3D
const TABLE := Vector3(1.41, 0, -0.60)          # round café table, r 0.38, top 0.75; between Bernard and the roommate
const TABLE_R := 0.38
const SEAT := Vector3(1.79, 0, -0.92)           # roommate's Hips, in the corner of an L breakfast-nook bench
const SEAT_YAW := 130.0                         # faces Bernard (origin) within 14 deg; right elbow off the back wall
const COUNTER_END := 0.75


func _a(k: String, d: String) -> String:
	var args := OS.get_cmdline_user_args()
	return args[args.find(k) + 1] if k in args else d


func _ready() -> void:
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	_env()
	if '--art' in OS.get_cmdline_user_args():          # the built set + props (breakfast/art) instead of the blocks
		_art()
	else:
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
	var sun := DirectionalLight3D.new()               # warm low morning sun from the right, through the window
	sun.light_color = Color('#FFE2B8')
	sun.light_energy = 2.2
	sun.shadow_enabled = true
	sun.rotation_degrees = Vector3(-24, 70, 0)        # travels -X and a little -Z: rakes across the worktop
	add_child(sun)
	var fill := OmniLight3D.new()                     # soft room fill under the ceiling
	fill.position = Vector3(0, 2.4, 0.7)
	fill.light_color = Color('#FFF1DE')
	fill.light_energy = 1.2
	fill.omni_range = 6.0
	add_child(fill)


const HIDDEN := {'coffee_machine': ['Stream', 'Splash'], 'mug': ['Phone', 'Splats'], 'toast': ['Crumbs'],
	'toast_2': ['Crumbs']}


func _art() -> void:
	var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string('res://breakfast/art/layout.json'))
	var room: Node3D = load('res://breakfast/art/breakfast_room.tscn').instantiate()
	add_child(room)
	for n in room.find_children('*', 'MeshInstance3D', true, false):
		n.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_DOUBLE_SIDED   # single-sided shells block the sun
		if n.name in ['WindowSky', 'PorchLight']:
			n.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		if String(n.name).begins_with('Ceiling') or String(n.name).begins_with('FrontPaint') or n.name == 'LampDome' \
				or String(n.name).begins_with('LampRing') or String(n.name).begins_with('HallCeiling'):
			n.add_to_group('roof')
	for id: String in layout.props:
		var scene := 'toast' if id == 'toast_2' else id
		var prop: Node3D = load('res://breakfast/art/props/%s.tscn' % scene).instantiate()
		var a: Array = layout.props[id]
		prop.position = Vector3(a[0], a[1], a[2])
		prop.rotation_degrees.y = float(layout.prop_rotation_y.get(id, 0.0))
		add_child(prop)
		for part: String in HIDDEN.get(id, []):
			prop.get_node(part).visible = false
	for n in get_children():                          # the closed set: sun only through the window, softer fill
		if n is WorldEnvironment:
			n.environment.ambient_light_energy = 0.55
		elif n is DirectionalLight3D:
			n.light_energy = 2.6
		elif n is OmniLight3D:
			n.light_energy = 0.7
	for k in ['kitchen_lamp', 'pendant', 'hall_lamp']:
		var l := OmniLight3D.new()
		var a: Array = layout.lights[k]
		l.position = Vector3(a[0], a[1], a[2])
		l.light_color = Color(1, 0.86, 0.68)
		l.light_energy = 0.9 if k == 'kitchen_lamp' else 0.6
		l.omni_range = 4.0 if k == 'kitchen_lamp' else 2.5
		add_child(l)


func _room() -> void:
	for i in 8:                                       # terracotta/cream checker, 0.5 m tiles (x -2..2, z -1.15..2.55)
		for j in 8:
			box(Vector3(-1.75 + i * 0.5, -0.01, -0.9 + j * 0.5), Vector3(0.5, 0.02, 0.5),
				TERRACOTTA if (i + j) % 2 else CREAM, 0.85)
	var h := 2.6
	box(Vector3(0, h / 2, -1.2), Vector3(4.2, h, 0.1), CREAM)                     # back wall
	box(Vector3(0, h / 2, 2.6), Vector3(4.2, h, 0.1), CREAM).add_to_group('roof')    # front wall
	box(Vector3(0, h + 0.05, 0.7), Vector3(4.2, 0.1, 3.9), PORCELAIN).add_to_group('roof')   # ceiling
	# right wall with the window toward the front (z 1.0 .. 2.0, y 1.0 .. 2.0): out of the counter/table views
	box(Vector3(2.1, h / 2, -0.1), Vector3(0.1, h, 2.2), CREAM)
	box(Vector3(2.1, h / 2, 2.3), Vector3(0.1, h, 0.6), CREAM)
	box(Vector3(2.1, 0.5, 1.5), Vector3(0.1, 1.0, 1.0), CREAM)
	box(Vector3(2.1, 2.3, 1.5), Vector3(0.1, 0.6, 1.0), CREAM)
	box(Vector3(2.11, 1.5, 1.5), Vector3(0.02, 1.0, 1.0), '#FFF6E6', 0.9, 0.6)   # frosted pane (emissive, no glass)
	box(Vector3(2.05, 1.0, 1.5), Vector3(0.14, 0.04, 1.08), PORCELAIN)          # sill
	# left wall with the hallway opening (z 0.3 .. 1.3, 2.1 high)
	box(Vector3(-2.1, h / 2, -0.45), Vector3(0.1, h, 1.5), CREAM)
	box(Vector3(-2.1, h / 2, 1.95), Vector3(0.1, h, 1.3), CREAM)
	box(Vector3(-2.1, 2.35, 0.8), Vector3(0.1, 0.5, 1.0), CREAM)
	box(Vector3(-2.05, 1.05, 0.28), Vector3(0.16, 2.1, 0.05), PORCELAIN)         # door frame trim
	box(Vector3(-2.05, 1.05, 1.32), Vector3(0.16, 2.1, 0.05), PORCELAIN)


func _counter() -> void:
	box(Vector3(-0.35, 0.43, -0.85), Vector3(2.2, 0.86, 0.6), TEAL)               # deep teal lower cabinets (to x 0.75)
	for x in [-0.9, -0.2, 0.5]:                                                 # door gaps read as panels
		box(Vector3(x, 0.45, -0.545), Vector3(0.012, 0.7, 0.01), '#244A49')
	box(Vector3(-0.35, 0.9, -0.83), Vector3(2.26, 0.04, 0.66), '#F3E7D0', 0.7)     # warm cream worktop (brightest group)
	for i in 11:                                                                  # peach tile backsplash
		for j in 3:
			box(Vector3(-1.4 + i * 0.2, 1.0 + j * 0.15, -1.145), Vector3(0.19, 0.14, 0.01), PEACH, 0.75)
	box(Vector3(-0.35, 1.8, -0.97), Vector3(2.2, 0.7, 0.35), CREAM)              # cream uppers right above the tiles
	for x in [-0.9, -0.2, 0.5]:
		box(Vector3(x, 1.8, -0.794), Vector3(0.012, 0.6, 0.01), '#D9CBB2')
	box(Vector3(-1.75, 0.95, -0.8), Vector3(0.6, 1.9, 0.7), PORCELAIN, 0.7)       # fridge (counter's left end)
	box(Vector3(-1.52, 1.35, -0.444), Vector3(0.04, 0.4, 0.02), GRAPHITE)
	for p in [Vector3(-1.9, 1.55, -0.44), Vector3(-1.65, 1.62, -0.44), Vector3(-1.8, 1.2, -0.44)]:
		box(p, Vector3(0.05, 0.05, 0.015), CLAY)                                  # magnets
	box(Vector3(-1.72, 1.25, -0.443), Vector3(0.14, 0.2, 0.01), PORCELAIN)      # TODAY-style notepad
	# props at mechanics' marks (locations/breakfast/breakfast.gd PROPS)
	box(Vector3(0.08, 0.925, -0.64), Vector3(0.08, 0.012, 0.15), GRAPHITE)        # phone
	box(Vector3(-0.3, 1.07, -0.9), Vector3(0.24, 0.3, 0.26), TEAL)                # coffee machine body
	box(Vector3(-0.3, 1.08, -0.765), Vector3(0.2, 0.22, 0.01), CREAM)             # cream front panel
	box(Vector3(-0.3, 1.27, -0.92), Vector3(0.14, 0.1, 0.14), '#E9E1D2')          # matte bean hopper
	cyl(Vector3(-0.3, 0.97, -0.66), 0.045, 0.1, CREAM)                            # Bernard's mug
	cyl(Vector3(-0.3, 0.975, -0.66), 0.047, 0.018, PEACH)                         # its peach band
	box(Vector3(0.42, 1.02, -0.82), Vector3(0.28, 0.2, 0.18), PEACH)              # toaster
	box(Vector3(0.42, 1.125, -0.82), Vector3(0.2, 0.012, 0.03), GRAPHITE)         # slots
	cyl(Vector3(-1.2, 1.02, -0.85), 0.08, 0.2, CLAY)                              # kettle
	box(Vector3(-0.75, 0.65, -0.53), Vector3(0.22, 0.38, 0.02), PEACH, 0.9)      # tea towel


func _table() -> void:
	var c := TABLE                                                                # round, one pedestal: legs never meet his knees
	cyl(c + Vector3(0, 0.735, 0), TABLE_R, 0.04, HONEY)
	cyl(c + Vector3(0, 0.36, 0), 0.04, 0.72, HONEY)
	cyl(c + Vector3(0, 0.015, 0), 0.16, 0.03, HONEY)
	var f := Vector3(-sin(deg_to_rad(SEAT_YAW)), 0, -cos(deg_to_rad(SEAT_YAW)))     # roommate's facing
	var l := Vector3(f.z, 0, -f.x)                                                 # his left
	var plate := SEAT + f * 0.42 + l * 0.12
	cyl(plate + Vector3(0, 0.76, 0), 0.11, 0.015, PORCELAIN)                       # his plate with toast
	box(plate + Vector3(0, 0.775, 0), Vector3(0.09, 0.015, 0.09), '#D9A060')
	var mug := SEAT + f * 0.4 - l * 0.2
	cyl(mug + Vector3(0, 0.8, 0), 0.04, 0.09, CLAY)                                # his mug, by the right hand
	cyl(c + Vector3(-0.12, 0.79, 0.16), 0.09, 0.07, CREAM)                         # fruit bowl, window side
	for p in [Vector3(-0.15, 0.84, 0.18), Vector3(-0.08, 0.84, 0.14)]:
		cyl(c + p, 0.035, 0.06, CLAY)
	# L nook bench (seat 0.46) in the corner: a chair back can't fit there at a 2 m eye distance
	box(Vector3(1.79, 0.22, -0.94), Vector3(0.42, 0.44, 0.42), HONEY)              # corner block
	box(Vector3(1.86, 0.22, -0.515), Vector3(0.28, 0.44, 0.43), HONEY)             # shallower run along the right wall (clears his knee)
	box(Vector3(1.79, 0.45, -0.94), Vector3(0.42, 0.03, 0.42), PEACH, 0.9)         # seat cushions
	box(Vector3(1.86, 0.45, -0.515), Vector3(0.28, 0.03, 0.43), PEACH, 0.9)
	box(Vector3(1.97, 0.67, -0.73), Vector3(0.06, 0.4, 0.84), PEACH, 0.9)          # back cushions
	box(Vector3(1.79, 0.67, -1.12), Vector3(0.42, 0.4, 0.06), PEACH, 0.9)


func _chair(p: Vector3, yaw: float, w := 0.44) -> void:
	var n := Node3D.new()
	n.position = p
	n.rotation_degrees.y = yaw
	add_child(n)
	var parts := [[Vector3(0, 0.45, 0), Vector3(w, 0.04, 0.42)], [Vector3(0, 0.75, 0.19), Vector3(w, 0.5, 0.04)]]
	for dx in [-w / 2 + 0.03, w / 2 - 0.03]:
		for dz in [-0.18, 0.18]:
			parts.append([Vector3(dx, 0.22, dz), Vector3(0.04, 0.45, 0.04)])
	for q in parts:
		var b := box(Vector3.ZERO, q[1], HONEY)
		b.reparent(n, false)
		b.position = q[0]


func _hall() -> void:
	# hallway LEFT (x -2.1 .. -5.1, z 0.25 .. 1.35): cream walls with a peach dado, a teal front door with a chunky
	# knob and a small frosted pane, a coat on a hook, a shoe rack full of shoe pairs (no slippers)
	box(Vector3(-3.6, -0.01, 0.8), Vector3(3.0, 0.02, 1.1), '#B98A62', 0.85)      # wood floor
	for z in [0.2, 1.4]:
		box(Vector3(-3.6, 1.3, z), Vector3(3.0, 2.6, 0.1), CREAM)
		box(Vector3(-3.6, 0.45, z + (0.055 if z < 1 else -0.055)), Vector3(3.0, 0.9, 0.01), PEACH)    # dado
		box(Vector3(-3.6, 0.92, z + (0.06 if z < 1 else -0.06)), Vector3(3.0, 0.04, 0.02), PORCELAIN)
	box(Vector3(-3.6, 2.65, 0.8), Vector3(3.0, 0.1, 1.3), PORCELAIN).add_to_group('roof')
	box(Vector3(-5.15, 1.3, 0.8), Vector3(0.1, 2.6, 1.3), CREAM)
	box(Vector3(-5.09, 1.02, 0.8), Vector3(0.05, 2.04, 0.9), TEAL)                # front door
	box(Vector3(-5.06, 1.62, 0.8), Vector3(0.02, 0.32, 0.28), '#FFF6E6', 0.9, 0.5) # small frosted pane
	var knob := cyl(Vector3(-5.03, 1.0, 0.5), 0.035, 0.07, '#C9A24A')            # chunky knob
	knob.rotation_degrees.z = 90.0
	box(Vector3(-4.55, 1.75, 1.33), Vector3(0.3, 0.04, 0.04), HONEY)             # coat hook rail
	box(Vector3(-4.55, 1.35, 1.25), Vector3(0.34, 0.75, 0.14), '#6B7C8C')        # coat
	box(Vector3(-3.6, 0.25, 1.2), Vector3(0.9, 0.04, 0.3), HONEY)                # shoe rack: 2 shelves
	box(Vector3(-3.6, 0.52, 1.2), Vector3(0.9, 0.04, 0.3), HONEY)
	for i in 3:                                                                   # pairs: white soles, laces
		for k in 2:
			var col: String = [GRAPHITE, '#6B4E3A', '#3D5560', '#9C4E3A'][(i + 2 * k) % 4]
			for d in [-0.045, 0.045]:
				var x: float = -3.9 + i * 0.29 + d
				var y := 0.27 + k * 0.27
				box(Vector3(x, y + 0.012, 1.2), Vector3(0.075, 0.025, 0.24), PORCELAIN)      # sole
				box(Vector3(x, y + 0.05, 1.21), Vector3(0.07, 0.055, 0.2), col)               # upper
				box(Vector3(x, y + 0.08, 1.17), Vector3(0.04, 0.01, 0.07), PORCELAIN)          # laces


func _roommate() -> void:
	var over := {'parts': {'hair': 'hair_curly_m', 'top': 'tshirt_m', 'outer': 'overshirt_m'},
		'colors': {'top': '#EFE6D2', 'rib': '#D8CDB6', 'outer': '#26324A', 'bottom': '#4A4D52', 'hair': '#2A1E1A',
			'skin': '#C98B66'}}
	var r: Node3D = CharacterAssembler.build('male_base', over)
	add_child(r)
	r.rotation_degrees.y = SEAT_YAW                  # faces Bernard
	var ap: AnimationPlayer = r.get_node('Anim')
	ap.play('sit_table')                              # chair sit, hands resting on the tabletop
	ap.seek(0.5, true)
	ap.pause()
	var sk: Skeleton3D = r.find_children('*', 'Skeleton3D', true, false)[0]
	await get_tree().process_frame
	var hips := (sk.global_transform * sk.get_bone_global_pose(sk.find_bone('Hips'))).origin
	r.global_position += SEAT - Vector3(hips.x, 0, hips.z)
	roommate = r


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
	for s in (CLOSE if '--close' in OS.get_cmdline_user_args() else SHOTS):
		cam.position = s[1]
		cam.rotation_degrees = Vector3(s[3], s[2], 0)
		label.text = s[0]
		for n in get_tree().get_nodes_in_group('roof'):
			n.visible = not String(s[0]).begins_with('overview')
		for n in 4:
			await RenderingServer.frame_post_draw
		if String(s[0]).begins_with('beat 7') and roommate:
			var sk: Skeleton3D = roommate.find_children('*', 'Skeleton3D', true, false)[0]
			var hd := (sk.global_transform * sk.get_bone_global_pose(sk.find_bone('Head'))).origin
			var eye := hd + Vector3(0, 0.12, 0)
			var top := hd + Vector3(0, 0.36, 0)
			var chin := hd - Vector3(0, 0.02, 0)
			print('PROBE eye_dist %.2f m  head top %.0f%% from frame top  face %.0f%% of frame height  eye x %.0f%%' % [
				eye.distance_to(cam.global_position), 100.0 * cam.unproject_position(top).y / size.y,
				100.0 * (cam.unproject_position(chin).y - cam.unproject_position(top).y) / size.y,
				100.0 * cam.unproject_position(eye).x / size.x])
		if String(s[0]).begins_with('oblique') and roommate:
			# 3D clearance: knees/feet/hands vs the counter run (x <= COUNTER_END, z <= -0.55), the round table, the walls
			var sk: Skeleton3D = roommate.find_children('*', 'Skeleton3D', true, false)[0]
			for b in ['LeftLowerLeg', 'RightLowerLeg', 'LeftFoot', 'RightFoot', 'LeftToes', 'RightToes', 'LeftHand', 'RightHand', 'LeftLowerArm', 'RightLowerArm', 'Hips']:
				var q := (sk.global_transform * sk.get_bone_global_pose(sk.find_bone(b))).origin
				var dc := maxf(q.x - COUNTER_END, q.z + 0.55)
				var r := Vector2(q.x - TABLE.x, q.z - TABLE.z).length()
				var dt := maxf(r - TABLE_R, maxf(q.y - 0.755, 0.715 - q.y))           # >0 outside the top slab
				var nb := minf(maxf(1.58 - q.x, maxf(q.z + 0.73, q.y - 0.465)), maxf(1.72 - q.x, maxf(q.z + 0.3, q.y - 0.465)))  # >0 clear of the nook
				print('CLEAR %s (%.2f, %.2f, %.2f) counter %.2f table %.2f walls %.2f nook %.2f' % [b, q.x, q.y, q.z, dc, dt, minf(2.0 - q.x, q.z + 1.15), nb])
		tiles.append(get_viewport().get_texture().get_image())
	var w := tiles[0].get_width()
	var h := tiles[0].get_height()
	var sheet := Image.create(w * 2, h * ceili(tiles.size() / 2.0), false, tiles[0].get_format())
	for i in tiles.size():
		sheet.blit_rect(tiles[i], Rect2i(0, 0, w, h), Vector2i((i % 2) * w, (i / 2) * h))
	var dir := 'res://previews/kitchen/screenshots/'
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	sheet.save_png(dir + name + '.png')
	print('KITCHEN_SHEET ', dir + name + '.png')
	get_tree().quit()
