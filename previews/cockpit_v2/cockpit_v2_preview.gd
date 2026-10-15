extends Node3D
## Cockpit v2 look-dev: game camera, art, lighting, and the approved concept as an overlay.
## O cycles overlay (off / 50% / 100%), S toggles preview screen content, T toggles the task label.
## Capture: godot --path . res://previews/cockpit_v2/cockpit_v2_preview.tscn -- --capture <name> [--size 1672x941] [--fit adaptive|height]
##   [--eye x,y,z --look x,y,z]  inspect from another point (no overlay).
##   [--extra res://path.glb]  add a scene (e.g. previews/hands/sheet_teal.glb).
##   [--shots "seat;name@eye@look;..."]  several views in one run + a contact sheet (see _multi).
## Fit "adaptive" (recommended for the game): keep the 16:9 framing whole; narrower windows reveal more top/bottom,
## wider ones more sides. "height" is Godot's default (narrow windows crop the sides).

const ART := preload('res://cockpit/art/cockpit_art.tscn')
const LIGHTING := preload('res://cockpit/art/cockpit_lighting.tscn')
const SCREENS := preload('res://previews/cockpit_v2/preview_screens.glb')
const CONCEPT := preload('res://concepts/cockpit/cockpit-warm-ceramic-v1.png')
## Control art on the Console anchors from layout.json (console.anchors).
const CONTROLS := {
	'res://cockpit/art/controls/left_keys.glb': 'LeftKeys',
	'res://cockpit/art/controls/panic_button.glb': 'PanicButton',
	'res://cockpit/art/controls/joystick.glb': 'RightSlot',
}

var overlay: TextureRect
var screens: Node3D
var task: Label3D
var alphas := [0.0, 0.5, 1.0]
var alpha_i := 0
var camera: Camera3D
var fit := 'adaptive'
const FOV_V := 68.0
const FOV_H := 100.3   # horizontal FOV of 68 deg vertical at 16:9

func _ready() -> void:
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	add_child(LIGHTING.instantiate())
	add_child(ART.instantiate())
	var xa := OS.get_cmdline_user_args().find('--extra')
	if xa >= 0:
		add_child(load(OS.get_cmdline_user_args()[xa + 1]).instantiate())
	var console := Node3D.new()
	console.position = Vector3(0, 0.95, 0.1)
	console.rotation_degrees = Vector3(18, 0, 0)
	add_child(console)
	var anchors: Dictionary = JSON.parse_string(FileAccess.get_file_as_string('res://cockpit/art/layout.json'))['console']['anchors']
	for path in CONTROLS:
		var module: Node3D = load(path).instantiate()
		var a: Array = anchors[CONTROLS[path]]
		module.position = Vector3(a[0], a[1], a[2])
		console.add_child(module)
	screens = SCREENS.instantiate()
	add_child(screens)
	camera = Camera3D.new()
	camera.position = Vector3(0, 1.36, 0.8)
	camera.rotation_degrees = Vector3(-14, 0, 0)
	camera.fov = 68
	camera.near = 0.02
	add_child(camera)
	camera.current = true
	task = Label3D.new()
	task.text = 'TASK: Mop the\nkitchen floor\n(again...)'
	task.rotation_degrees = Vector3(-10, 25, 0)
	task.position = Vector3(-0.74, 1.0, -0.12) + task.basis * Vector3(0.025, -0.012, 0.006)
	task.pixel_size = 0.0004
	task.font_size = 40
	task.outline_size = 0
	task.modulate = Color(0.15, 0.12, 0.1)
	add_child(task)
	var ui := CanvasLayer.new()
	add_child(ui)
	overlay = TextureRect.new()
	overlay.texture = CONCEPT
	overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	overlay.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	overlay.stretch_mode = TextureRect.STRETCH_SCALE
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(overlay)
	_set_overlay(0)
	var args := OS.get_cmdline_user_args()
	var f := args.find('--fit')
	if f >= 0:
		fit = args[f + 1]
	get_viewport().size_changed.connect(_apply_fit)
	_apply_fit()
	var e := args.find('--eye')
	if e >= 0:
		camera.position = _vec(args[e + 1])
		camera.look_at(_vec(args[args.find('--look') + 1]))
	var i := args.find('--capture')
	if i >= 0:
		_capture.call_deferred(args[i + 1] if i + 1 < args.size() else 'look')

func _vec(s: String) -> Vector3:
	var p := s.split(',')
	return Vector3(float(p[0]), float(p[1]), float(p[2]))

func _apply_fit() -> void:
	var size := get_viewport().get_visible_rect().size
	var narrow := size.x / size.y < 16.0 / 9.0
	if fit == 'adaptive' and narrow:
		camera.keep_aspect = Camera3D.KEEP_WIDTH
		camera.fov = FOV_H
	else:
		camera.keep_aspect = Camera3D.KEEP_HEIGHT
		camera.fov = FOV_V
	# The overlay only lines up at 16:9.
	overlay.visible = alphas[alpha_i] > 0.0 and absf(size.x / size.y - 16.0 / 9.0) < 0.02

func _set_overlay(i: int) -> void:
	alpha_i = i
	overlay.modulate.a = alphas[i]
	overlay.visible = alphas[i] > 0.0

func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:
		return
	match event.keycode:
		KEY_O: _set_overlay((alpha_i + 1) % alphas.size())
		KEY_S: screens.visible = not screens.visible
		KEY_T: task.visible = not task.visible

func _shot(path: String) -> void:
	for n in 4:
		await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(path)
	print('COCKPIT_V2_CAPTURE ', path)

func _capture(name: String) -> void:
	var args := OS.get_cmdline_user_args()
	var size := Vector2i(1672, 941)
	var si := args.find('--size')
	if si >= 0:
		var p := args[si + 1].split('x')
		size = Vector2i(int(p[0]), int(p[1]))
	get_window().size = size
	var dir := 'res://previews/cockpit_v2/screenshots/'
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	for n in 10:
		await get_tree().process_frame
	var sh := args.find('--shots')
	if sh >= 0:
		await _multi(dir, name, args[sh + 1])
		get_tree().quit()
		return
	await _shot(dir + name + '.png')
	if size == Vector2i(1672, 941) and not '--eye' in args:
		_set_overlay(1)
		await _shot(dir + name + '-overlay.png')
	get_tree().quit()


## --shots "seat;left@-0.55,1.35,0.25@-0.8,1.3,-0.38;..." : many views in one run (one Godot start, one import).
## "seat" = the game camera. Writes <dir>/<name>_<shot>.png and a 2-column contact sheet <name>.png (each
## tile 800 px wide), so one image read reviews every view.
func _multi(dir: String, name: String, spec: String) -> void:
	var tiles: Array[Image] = []
	for item in spec.split(';', false):
		var part := item.split('@')
		if part.size() == 3:
			camera.position = _vec(part[1])
			camera.look_at(_vec(part[2]))
		else:
			camera.position = Vector3(0, 1.36, 0.8)
			camera.rotation_degrees = Vector3(-14, 0, 0)
		await _shot(dir + name + '_' + part[0] + '.png')
		var img := get_viewport().get_texture().get_image()
		img.resize(800, int(800.0 * img.get_height() / img.get_width()))
		tiles.append(img)
	var tw := tiles[0].get_width()
	var th := tiles[0].get_height()
	var cols := mini(2, tiles.size())
	var sheet := Image.create(tw * cols, th * ceili(tiles.size() / float(cols)), false, tiles[0].get_format())
	for i in tiles.size():
		sheet.blit_rect(tiles[i], Rect2i(0, 0, tw, th), Vector2i((i % cols) * tw, (i / cols) * th))
	sheet.save_png(dir + name + '.png')
	print('COCKPIT_V2_SHEET ', dir + name + '.png')
