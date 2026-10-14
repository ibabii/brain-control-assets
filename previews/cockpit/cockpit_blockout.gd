extends Node3D
## Art composition lab. Placeholder screens/controls are not gameplay implementations.
const ART := preload('res://cockpit/art/cockpit_blockout.glb')
const GAUGES := ['Coordination', 'Confidence', 'Balance', 'Focus', 'Embarrassment']
const KEY_COLORS := ['ff5fa2', '6bdc5a', '3aa8ff', 'ffb03a']
var art: Node3D
var camera: Camera3D
var screen_labels: Array[Label3D] = []
var notes: Array[Node3D] = []
var menu := true
var clearances: Node3D
var right_module: Node3D
var variant := false
var caption: Label

func _ready() -> void:
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	get_window().content_scale_size = Vector2i.ZERO
	var container := ART.instantiate()
	add_child(container)
	art = container.get_node('CockpitBlockout')
	var world := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color('454C48')
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color('F8F4EA')
	environment.ambient_light_energy = 0.65
	world.environment = environment
	add_child(world)
	var key := OmniLight3D.new()
	key.position = Vector3(-0.5, 1.9, 0.75)
	key.light_color = Color(1.0, 0.96, 0.91)
	key.light_energy = 1.1
	key.omni_range = 5
	key.shadow_enabled = true
	add_child(key)
	var fill := OmniLight3D.new()
	fill.position = Vector3(0.8, 1.5, 0.7)
	fill.light_energy = 0.45
	fill.omni_range = 4
	add_child(fill)
	camera = Camera3D.new()
	camera.position = Vector3(0, 1.36, 0.8)
	camera.rotation_degrees = Vector3(-14, 0, 0)
	camera.fov = 68
	camera.near = 0.01
	camera.current = true
	add_child(camera)
	_make_screen('FrontScreen', Vector2(1.28, .72), true)
	_make_screen('LeftPanel', Vector2(.34, .46), false, 'LEFT\nRHYTHM')
	_make_screen('RightPanel', Vector2(.34, .46), false, 'RIGHT\nMEMORY')
	_make_gauges()
	_make_controls()
	label3d(art.get_node('Dressing'), 'TASK\nBrush teeth', Vector3(-.74,1.0,-.115), 54, .0007, Color('454C48'))
	label3d(art.get_node('Dressing'), 'small\nsteps', Vector3(-1,1.77,-.384), 54, .0008, Color('454C48'))
	label3d(art.get_node('Dressing'), "it's\nokay", Vector3(.97,1.75,-.394), 54, .0008, Color('454C48'))
	label3d(art.get_node('Dressing'), 'SAME BRAIN\nDIFFERENT DAY', Vector3(-.38,1.93,-.534), 44, .0005, Color('454C48'))
	clearances = Node3D.new()
	add_child(clearances)
	var slot := Node3D.new()
	clearances.add_child(slot)
	slot.transform = art.get_node('ConsoleHousing').global_transform
	_wire_box(slot, Vector3(.3,-.10,0), Vector3(.34,.44,.29))
	_wire_box(clearances, Vector3(0,1.43,-.56), Vector3(1.28,.72,.04))
	clearances.visible = false
	var ui := CanvasLayer.new()
	add_child(ui)
	caption = Label.new()
	caption.text = 'COMPOSITION BLOCKOUT · placeholder screens / controls · hands deferred\nM menu/gameplay · C clearance guides · V proposed slot spacing'
	caption.add_theme_font_size_override('font_size', 14)
	caption.add_theme_color_override('font_color',Color('F8F4EA'))
	caption.add_theme_color_override('font_outline_color',Color('454C48'))
	caption.add_theme_constant_override('outline_size',4)
	caption.position = Vector2(16,16)
	ui.add_child(caption)
	print('COCKPIT_PREVIEW_READY camera=',camera.position,' fov=',camera.fov)
	if '--capture-cockpit' in OS.get_cmdline_user_args():
		_capture.call_deferred()

func material(color: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = .62
	return mat

func mesh_node(parent: Node3D, mesh: Mesh, pos: Vector3, color: Color) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.mesh = mesh
	node.position = pos
	node.material_override = material(color)
	parent.add_child(node)
	return node

func box(parent: Node3D, pos: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	return mesh_node(parent,mesh,pos,color)

func label3d(parent: Node3D, text: String, pos: Vector3, font: int, pixel: float, color: Color) -> Label3D:
	var node := Label3D.new()
	node.text = text
	node.position = pos
	node.font_size = font
	node.pixel_size = pixel
	node.modulate = color
	node.outline_size = 0
	node.no_depth_test = false
	parent.add_child(node)
	return node

func _make_screen(name: String, size: Vector2, main: bool, text := '') -> void:
	var parent := art.get_node('ScreenHousings/' + name) as Node3D
	var quad := QuadMesh.new()
	quad.size = size
	var face := mesh_node(parent,quad,Vector3.ZERO,Color('2D5C5B'))
	(face.material_override as StandardMaterial3D).shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	var label := label3d(parent,'RISE & BRUSH\n\nA small morning adventure\n\n←  Episode 01  →\n\nENTER to start' if main else text,Vector3(0,.035,.006),64,.0013 if main else .0007,Color('F1E4CF'))
	screen_labels.append(label)
	if not main:
		for i in 4:
			box(parent,Vector3(-.10+i*.066,-.12,.007),Vector3(.045,.012,.002),Color(KEY_COLORS[i]))

func _make_gauges() -> void:
	var group := art.get_node('GaugeHousing') as Node3D
	for i in 5:
		var x: float = (i-2)*.24
		var face := CylinderMesh.new()
		face.top_radius = .07
		face.bottom_radius = .07
		face.height = .003
		var node := mesh_node(group,face,Vector3(x,0,.013),Color('F1E4CF'))
		node.rotation_degrees.x = 90
		for tick in 9:
			var angle := deg_to_rad(-120+tick*30)
			var mark := box(group,Vector3(x+sin(angle)*.059,cos(angle)*.059,.016),Vector3(.002,.009,.001),Color('454C48'))
			mark.rotation.z = -angle
		var pivot := Node3D.new()
		group.add_child(pivot)
		pivot.position = Vector3(x,0,.019)
		pivot.rotation_degrees.z = (i-2)*25
		box(pivot,Vector3(0,.026,0),Vector3(.004,.052,.002),Color('C98778'))
		var bulb := SphereMesh.new()
		bulb.radius = .009
		bulb.height = .018
		mesh_node(group,bulb,Vector3(x,0,.021),Color('C98778'))
		label3d(group,GAUGES[i],Vector3(x,-.122,.022),56,.0006,Color('454C48'))

func _make_controls() -> void:
	var console := art.get_node('ConsoleHousing') as Node3D
	for i in 4:
		box(console,Vector3(-.27+(i-1.5)*.075,.0125,0),Vector3(.065,.025,.065),Color(KEY_COLORS[i]))
		var label := label3d(console,['A','S','D','F'][i],Vector3(-.27+(i-1.5)*.075,.026,0),64,.0005,Color('454C48'))
		label.rotation_degrees.x = -90
	var cap := CylinderMesh.new()
	cap.top_radius = .055
	cap.bottom_radius = .055
	cap.height = .03
	mesh_node(console,cap,Vector3(.02,.04,-.06),Color('ff3b3b'))
	var text := label3d(console,'SPACE',Vector3(.02,.056,-.06),48,.00035,Color('454C48'))
	text.rotation_degrees.x = -90
	right_module = Node3D.new()
	console.add_child(right_module)
	right_module.position.x = .3
	var shaft := CylinderMesh.new()
	shaft.top_radius = .009
	shaft.bottom_radius = .012
	shaft.height = .13
	mesh_node(right_module,shaft,Vector3(0,.095,0),Color('454C48'))
	var knob := SphereMesh.new()
	knob.radius = .028
	knob.height = .056
	mesh_node(right_module,knob,Vector3(0,.16,0),Color('3ee0d0'))

func _wire_box(parent: Node3D, centre: Vector3, size: Vector3) -> void:
	var corners: Array[Vector3] = []
	for x in [-1,1]:
		for y in [-1,1]:
			for z in [-1,1]:corners.append(centre+Vector3(x,y,z)*size*.5)
	var mesh := ImmediateMesh.new()
	mesh.surface_begin(Mesh.PRIMITIVE_LINES)
	for i in 8:
		for bit in [1,2,4]:
			var j: int = i ^ bit
			if j > i:
				mesh.surface_add_vertex(corners[i])
				mesh.surface_add_vertex(corners[j])
	mesh.surface_end()
	var node := mesh_node(parent,mesh,Vector3.ZERO,Color('D9A04C'))
	(node.material_override as StandardMaterial3D).shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED

func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:return
	if event.keycode == KEY_M:_toggle_menu()
	if event.keycode == KEY_C:clearances.visible = not clearances.visible
	if event.keycode == KEY_V:_toggle_variant()
	if event.keycode == KEY_F:
		camera.fov = 74.0 if camera.fov < 70 else 68.0
		caption.text = 'COMPOSITION STUDY · FOV %d° · right slot %s\nM menu/gameplay · C clearance · V slot spacing · F field of view' % [camera.fov, '+8 cm outward' if variant else 'current anchor']

func _toggle_variant() -> void:
	variant = not variant
	right_module.position.x = .38 if variant else .3
	art.get_node('ConsoleHousing/RightSlotRim').position.x = right_module.position.x
	(clearances.get_child(0) as Node3D).position.x = .08 if variant else 0.0
	caption.text = ('PROPOSED SPACING · right slot +8 cm outward' if variant else 'CURRENT GAME ANCHORS · composition blockout') + '\nM menu/gameplay · C clearance guides · V slot spacing comparison'
	print('COCKPIT_SLOT_LAYOUT ', 'PROPOSED +8 cm outward' if variant else 'CURRENT game anchor')

func _toggle_menu() -> void:
	menu = not menu
	screen_labels[0].text = 'RISE & BRUSH\n\nA small morning adventure\n\n←  Episode 01  →\n\nENTER to start' if menu else 'HUMAN WORLD\n\nLive view occupies this area\n\nGameplay-screen size reference'

func _frame(filename: String) -> void:
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var err := get_viewport().get_texture().get_image().save_png('res://previews/cockpit/screenshots/'+filename)
	print('COCKPIT_CAPTURE ',filename,' error=',err)

func _capture() -> void:
	get_window().size = Vector2i(1280,720)
	await _frame('menu-16x9.png')
	_toggle_variant()
	await _frame('proposed-slot-spacing-16x9.png')
	camera.fov = 74
	caption.text = 'PROPOSED FRAMING · FOV 74° + slot 8 cm outward\nComposition study; game camera and mechanics unchanged'
	await _frame('proposed-roomier-framing-16x9.png')
	get_window().size = Vector2i(960,720)
	await _frame('proposed-roomier-framing-4x3.png')
	get_window().size = Vector2i(1280,720)
	camera.fov = 68
	_toggle_variant()
	_toggle_menu()
	await _frame('gameplay-layout-16x9.png')
	_toggle_menu()
	get_window().size = Vector2i(960,720)
	await _frame('menu-4x3.png')
	get_window().size = Vector2i(1280,720)
	clearances.visible = true
	await _frame('clearances-16x9.png')
	clearances.visible = false
	print('COCKPIT_CAPTURE_COMPLETE')
