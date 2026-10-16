extends SceneTree
## Contact sheet from any PNGs (headless, no project needed):
##   Godot --headless -s scripts/tools/sheet.gd -- OUT.png TILE_W COLS in1.png in2.png ...
## Tiles keep their aspect; rows take the tallest tile. Absolute paths.
func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var tw := int(a[1])
	var cols := int(a[2])
	var tiles: Array[Image] = []
	for p in a.slice(3):
		var im := Image.load_from_file(p)
		im.resize(tw, int(im.get_height() * float(tw) / im.get_width()), Image.INTERPOLATE_LANCZOS)
		im.convert(Image.FORMAT_RGB8)
		tiles.append(im)
	var rows := ceili(tiles.size() / float(cols))
	var rh: Array[int] = []
	for r in rows:
		var h := 0
		for c in cols:
			var i := r * cols + c
			if i < tiles.size():
				h = maxi(h, tiles[i].get_height())
		rh.append(h)
	var gap := 6
	var total := 0
	for h in rh:
		total += h + gap
	var out := Image.create(cols * (tw + gap) - gap, total - gap, false, Image.FORMAT_RGB8)
	out.fill(Color(0.1, 0.1, 0.1))
	var y := 0
	for r in rows:
		for c in cols:
			var i := r * cols + c
			if i < tiles.size():
				out.blit_rect(tiles[i], Rect2i(Vector2i.ZERO, tiles[i].get_size()), Vector2i(c * (tw + gap), y))
		y += rh[r] + gap
	out.save_png(a[0])
	print("SHEET ", a[0], " ", out.get_size())
	quit()
