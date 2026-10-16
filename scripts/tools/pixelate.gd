extends SceneTree
## Game-size check: shrink an image by FACTOR (e.g. head height -> 60 px), then blow it back up with nearest
## sampling so the real pixels show. Headless:  Godot --headless -s scripts/tools/pixelate.gd -- IN.png OUT.png FACTOR
func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var im := Image.load_from_file(a[0])
	var w := im.get_width()
	var h := im.get_height()
	var f := float(a[2])
	im.resize(maxi(1, int(w * f)), maxi(1, int(h * f)), Image.INTERPOLATE_LANCZOS)
	im.resize(w, h, Image.INTERPOLATE_NEAREST)
	im.save_png(a[1])
	print("PIXELATE ", a[1])
	quit()
