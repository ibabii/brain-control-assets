extends Node3D
## Organ-cam check: an organ (organs/art) on a plain backdrop, its loop sampled at --times; contact sheet.
## godot --path . res://previews/organs/organ_preview.tscn -- --organ heart --times 0,0.15 --capture NAME
##   [--bg "#hex"] [--size 512x512] [--swatch "#hex"]  (lamp colour square top-left + PROBE of the body mid-tone)

func _a(k: String, d: String) -> String:
	var args := OS.get_cmdline_user_args()
	return args[args.find(k) + 1] if k in args else d


func _ready() -> void:
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	var id := _a('--organ', 'heart')
	var we := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(_a('--bg', '#E9E1D2'))
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(1, 0.97, 0.93)
	e.ambient_light_energy = 0.18
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	we.environment = e
	add_child(we)
	var key := DirectionalLight3D.new()
	key.light_color = Color(1, 0.97, 0.93)
	key.light_energy = 0.52
	key.rotation_degrees = Vector3(-25, 205, 0)
	add_child(key)
	var fill := DirectionalLight3D.new()
	fill.light_energy = 0.2
	fill.rotation_degrees = Vector3(-10, 150, 0)
	add_child(fill)
	var organ: Node3D = load('res://organs/art/%s.tscn' % id).instantiate()
	add_child(organ)
	var cam := Camera3D.new()
	cam.fov = 30.0
	cam.position = Vector3(0, 0.17, -0.78)
	cam.rotation_degrees = Vector3(0, 180, 0)
	add_child(cam)
	cam.current = true
	var size := Vector2i(512, 512)
	if '--size' in OS.get_cmdline_user_args():
		var p := _a('--size', '512x512').split('x')
		size = Vector2i(int(p[0]), int(p[1]))
	get_window().size = size
	var ap: AnimationPlayer = organ.find_children('*', 'AnimationPlayer', true, false)[0]
	var anim: String = ap.get_animation_list()[0]
	print('ORGAN_ANIM ', id, ' ', anim, ' ', ap.get_animation(anim).length)
	ap.play(anim)
	ap.pause()
	var tiles: Array[Image] = []
	for t in Array(_a('--times', '0').split(',')).map(func(x): return float(x)):
		ap.seek(t, true)
		for n in 4:
			await RenderingServer.frame_post_draw
		var im := get_viewport().get_texture().get_image()
		if '--swatch' in OS.get_cmdline_user_args():
			_probe(im, im.get_pixel(2, 2))
			im.fill_rect(Rect2i(8, 8, size.x / 7, size.x / 7), Color(_a('--swatch', '#000000')))
		tiles.append(im)
	var sheet := Image.create(size.x * tiles.size(), size.y, false, tiles[0].get_format())
	for i in tiles.size():
		sheet.blit_rect(tiles[i], Rect2i(Vector2i.ZERO, size), Vector2i(i * size.x, 0))
	var dir := 'res://previews/organs/screenshots/'
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	sheet.save_png(dir + _a('--capture', id) + '.png')
	print('ORGAN_SHEET ', dir + _a('--capture', id) + '.png')
	get_tree().quit()


## Body mid-tone: the median-luminance pixel among those far from the backdrop and not ink-dark.
func _probe(im: Image, bg: Color) -> void:
	var px: Array[Color] = []
	for y in range(0, im.get_height(), 2):
		for x in range(0, im.get_width(), 2):
			var c := im.get_pixel(x, y)
			if absf(c.r - bg.r) + absf(c.g - bg.g) + absf(c.b - bg.b) > 0.12 and c.get_luminance() > 0.3:
				px.append(c)
	px.sort_custom(func(a: Color, b: Color) -> bool: return a.get_luminance() < b.get_luminance())
	print('PROBE mid #', px[px.size() / 2].to_html(false) if px.size() else 'none', ' n ', px.size())
