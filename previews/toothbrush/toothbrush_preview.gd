extends Node3D
## Standalone art preview: no dependency on gameplay scenes or autoloads.
## 1 hero, 2 first-person, 3 mirror projection, 4 reveal distance; P paste; arrows swing.

const ART := preload("res://props/toothbrush/art/toothbrush_art.tscn")
const REST := Vector3(0.03, 1.47, -0.24)
const EYE := Vector3(0, 1.62, 0)
const MODES := ["Hero detail", "First person · 70° FOV", "Mirror-equivalent projection · 1.1 m", "Reveal distance · 2 m"]

@export var capture_on_start := false

var art: Node3D
var camera: Camera3D
var grip_reference: MeshInstance3D
var caption: Label
var detail: Label
var mode := 0
var paste_visible := true


func _ready() -> void:
	# Preview captures use actual window pixels, including the 666×540 mirror test.
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	get_window().content_scale_size = Vector2i.ZERO
	art = ART.instantiate()
	add_child(art)
	art.position = REST
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("F1E4CF")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("F8F4EA")
	environment.ambient_light_energy = 0.55
	var world := WorldEnvironment.new()
	world.environment = environment
	add_child(world)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-35, -25, 0)
	key.light_color = Color(1.0, 0.96, 0.9)
	key.light_energy = 1.0
	key.shadow_enabled = true
	add_child(key)
	camera = Camera3D.new()
	camera.near = 0.01
	camera.current = true
	add_child(camera)
	grip_reference = MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 0.035
	sphere.height = 0.07
	grip_reference.mesh = sphere
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color("EAA78B")
	mat.roughness = 0.9
	grip_reference.material_override = mat
	grip_reference.position = REST + Vector3(0.17, -0.01, 0)
	add_child(grip_reference)
	var ui := CanvasLayer.new()
	add_child(ui)
	var overlay := Control.new()
	ui.add_child(overlay)
	overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	caption = Label.new()
	overlay.add_child(caption)
	caption.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	caption.offset_left = 24
	caption.offset_right = -24
	caption.offset_top = 20
	caption.offset_bottom = 82
	caption.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	caption.add_theme_font_size_override("font_size", 26)
	caption.add_theme_color_override("font_color", Color("2D5C5B"))
	detail = Label.new()
	overlay.add_child(detail)
	detail.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	detail.offset_left = 24
	detail.offset_right = -24
	detail.offset_top = 94
	detail.offset_bottom = 185
	detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	detail.add_theme_font_size_override("font_size", 17)
	detail.add_theme_color_override("font_color", Color("454C48"))
	_set_mode(0)
	if capture_on_start or "--capture-toothbrush" in OS.get_cmdline_user_args():
		_capture_sequence.call_deferred()


func _set_mode(value: int) -> void:
	mode = value
	art.rotation_degrees = Vector3.ZERO
	art.position = REST
	art.get_node("Paste").visible = paste_visible
	grip_reference.visible = mode == 1
	camera.scale = Vector3.ONE
	camera.fov = 50.0
	match mode:
		0:
			camera.position = REST + Vector3(0.17, 0.10, 0.20)
			camera.look_at(REST + Vector3(0.075, 0.01, 0))
		1:
			camera.position = EYE
			camera.rotation_degrees = Vector3(-12, 0, 0)
			camera.fov = 70.0
		2:
			# Eye reflected across the game's mirror plane Z=-0.665.
			camera.position = Vector3(0, 1.62, -1.33)
			camera.look_at(Vector3(0, 1.34, 0))
			camera.fov = 70.0
			# Reflection parity. Projection only; no bathroom/real mirror copied.
			camera.scale.x = -1.0
		3:
			var target := REST + Vector3(0.08, 0.0, 0)
			camera.position = target + Vector3(1.4, 0.2, 1.4).normalized() * 2.0
			camera.look_at(target)
	caption.text = "TOOTHBRUSH · %s" % MODES[mode]
	detail.text = "warm ceramic v1  |  19.4 cm  |  1,196 triangles\n1–4 views · P paste · arrow keys swing · R reset"
	if mode == 1:
		detail.text += "\nSphere marks the existing gameplay grip; hand art is separate."
	elif mode == 2:
		detail.text += "\nReflected eye position; actual bathroom mirror is checked during integration."


func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:
		return
	match event.keycode:
		KEY_1: _set_mode(0)
		KEY_2: _set_mode(1)
		KEY_3: _set_mode(2)
		KEY_4: _set_mode(3)
		KEY_P:
			paste_visible = not paste_visible
			art.get_node("Paste").visible = paste_visible
		KEY_LEFT: art.rotation_degrees.y = -14.0
		KEY_RIGHT: art.rotation_degrees.y = 14.0
		KEY_R: _set_mode(mode)


func _save_frame(filename: String) -> void:
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	var err := image.save_png("res://previews/toothbrush/screenshots/" + filename)
	print("TOOTHBRUSH_CAPTURE ", filename, " error=", err)


func _capture_sequence() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://previews/toothbrush/screenshots"))
	var names := ["hero.png", "first-person.png", "mirror-projection.png", "reveal-distance.png"]
	for i in MODES.size():
		get_window().size = Vector2i(666, 540) if i == 2 else Vector2i(1280, 720)
		_set_mode(i)
		await _save_frame(names[i])
	get_window().size = Vector2i(1280, 720)
	_set_mode(1)
	art.rotation_degrees.y = -14.0
	await _save_frame("swing-left.png")
	art.rotation_degrees.y = 14.0
	await _save_frame("swing-right.png")
	_set_mode(0)
	paste_visible = false
	art.get_node("Paste").visible = false
	await _save_frame("without-paste.png")
	paste_visible = true
	_set_mode(0)
	print("TOOTHBRUSH_PREVIEW_COMPLETE")
