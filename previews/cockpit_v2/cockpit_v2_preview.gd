extends Node3D
## Cockpit v2 look-dev: game camera, art, lighting, and the approved concept as an overlay.
## O cycles overlay (off / 50% / 100%), S toggles preview screen content, T toggles the task label.
## Capture: godot --path . res://previews/cockpit_v2/cockpit_v2_preview.tscn -- --capture <name> [--size 1672x941] [--fit adaptive|height]
## Fit "adaptive" (recommended for the game): keep the 16:9 framing whole; narrower windows reveal more top/bottom,
## wider ones more sides. "height" is Godot's default (narrow windows crop the sides).

const ART := preload('res://cockpit/art/cockpit_art.tscn')
const LIGHTING := preload('res://cockpit/art/cockpit_lighting.tscn')
const SCREENS := preload('res://previews/cockpit_v2/preview_screens.glb')
const CONCEPT := preload('res://concepts/cockpit/cockpit-warm-ceramic-v1.png')

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
	var i := args.find('--capture')
	if i >= 0:
		_capture.call_deferred(args[i + 1] if i + 1 < args.size() else 'look')

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
	await _shot(dir + name + '.png')
	if size == Vector2i(1672, 941):
		_set_overlay(1)
		await _shot(dir + name + '-overlay.png')
	get_tree().quit()
