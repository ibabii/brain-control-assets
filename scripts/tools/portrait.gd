extends SceneTree
## Round icon from a square render: circle mask (soft edge) + ring, saved at SIZE, plus a 64 px check blown back up.
## Godot --headless -s scripts/tools/portrait.gd -- IN.png OUT.png SIZE RING_HEX
func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var im := Image.load_from_file(a[0])
	var n := mini(im.get_width(), im.get_height())
	im = im.get_region(Rect2i((im.get_width() - n) / 2, (im.get_height() - n) / 2, n, n))
	var size := int(a[2])
	im.resize(size, size, Image.INTERPOLATE_LANCZOS)
	im.convert(Image.FORMAT_RGBA8)
	var ring := Color(a[3])
	var r := size / 2.0
	var rw := size * 0.035
	for y in size:
		for x in size:
			var d := Vector2(x + 0.5 - r, y + 0.5 - r).length()
			var c := im.get_pixel(x, y)
			if d > r - rw:
				c = ring
			c.a = clampf(r - d, 0.0, 1.0)
			im.set_pixel(x, y, c)
	im.save_png(a[1])
	var small := im.duplicate()
	small.resize(64, 64, Image.INTERPOLATE_LANCZOS)
	small.resize(size, size, Image.INTERPOLATE_NEAREST)
	small.save_png(a[1].replace('.png', '_64check.png'))
	print('PORTRAIT ', a[1])
	quit()
