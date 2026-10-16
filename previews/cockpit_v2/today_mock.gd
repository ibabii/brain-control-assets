extends Node
## Preview only (mock, not delivered): the TODAY notebook (art + live page) moved as one rigid group to placement
## options, scaled so the page keeps its on-screen size. Also spawns the hand pose preview (reads --left/--lx/--t).
## Args: --nb A|B|C|D|now

const PAGE_PX := Vector2(181, 775)          # current page centre, 1080p seat px
const OPTIONS := {
	# centre px, how the depth is found, lean (deg, + = top away), yaw (deg, + = turned to the seat)
	"A": [Vector2(181, 655), "back", 15.0, 15.0],
	"B": [Vector2(175, 415), "books", 0.0, 10.0],
	"C": [Vector2(265, 565), "console", 0.0, 8.0],
	"D": [Vector2(175, 415), "wall", 0.0, 18.0],
}

func _ready() -> void:
	var root := get_tree().current_scene
	root.add_child.call_deferred(load("res://previews/hands/hand_pose_preview.tscn").instantiate())
	for n in 3:
		await get_tree().process_frame
	var opt := _arg("--nb", "now")
	if not OPTIONS.has(opt):
		return
	var o: Array = OPTIONS[opt]
	var cam := Camera3D.new()                          # fit from the seat even when the shot is oblique
	cam.position = Vector3(0, 1.36, 0.8)
	cam.rotation_degrees = Vector3(-14, 0, 0)
	cam.fov = 68
	root.add_child(cam)
	await get_tree().process_frame
	var k := get_viewport().get_visible_rect().size.y / 1080.0          # px scale vs 1080p (16:9 and Deck keep width)
	var kx := get_viewport().get_visible_rect().size.x / 1920.0
	var page := root.find_children("Today", "Node3D", true, false)[0] as Node3D
	var p0 := page.global_position
	var fwd := -cam.global_basis.z
	var r0 := (p0 - cam.global_position).dot(fwd)
	var target: Vector2 = o[0]
	var px := Vector2(target.x * kx, target.y * k)
	var dir := cam.project_ray_normal(px)
	var r1 := r0
	match o[1]:
		"back":
			r1 = r0 + 0.12
		"books":
			r1 = _depth_on_plane(cam, Vector2(px.x, (target.y + 185) * k), 1.095) - 0.0
		"console":
			r1 = _depth_on_plane(cam, Vector2(px.x, (target.y + 185) * k), 1.0)
		"wall":
			r1 = (-0.33 - cam.global_position.z) / dir.z * dir.dot(fwd)
	var p1 := cam.global_position + dir * (r1 / dir.dot(fwd))
	var s := r1 / r0
	var rot := Basis(Vector3.UP, deg_to_rad(o[3])) * Basis(Vector3.RIGHT, deg_to_rad(-o[2]))
	var nb := root.find_children("Notebook", "Node3D", true, false)[0] as Node3D
	var nodes: Array[Node3D] = [nb, page]
	var orig: Array[Transform3D] = [nb.global_transform, page.global_transform]
	var r_before := _rect(cam, page)
	var fpx := get_viewport().get_visible_rect().size.y / 2.0 / tan(deg_to_rad(cam.fov / 2.0))
	for it in 5:                                       # fit: same on-screen area as now, centre on the target
		var xf := Transform3D(rot.scaled(Vector3.ONE * s), p1) * Transform3D(Basis(), -p0)
		for i in 2:
			nodes[i].global_transform = xf * orig[i]
		var r := _rect(cam, page)
		s *= sqrt(r_before.get_area() / r.get_area())
		var d := px - r.get_center()
		var depth := (p1 - cam.global_position).dot(fwd)
		p1 += cam.global_basis.x * (d.x * depth / fpx) - cam.global_basis.y * (d.y * depth / fpx)
	var xf2 := Transform3D(rot.scaled(Vector3.ONE * s), p1) * Transform3D(Basis(), -p0)
	for i in 2:
		nodes[i].global_transform = xf2 * orig[i]
	print("TODAY_MOCK before ", r_before, " after ", _rect(cam, page))
	if opt == "D":                                     # clipboard on the wall: no stand
		for c in nb.find_children("Stand*", "", true, false):
			(c as Node3D).visible = false
	if opt in ["B", "D"]:                              # YouGotThis moves off the page: up onto the left monitor's top bezel
		_shift(["YouGotThis", "YouGotThisTape"], Vector3(0.2, 0.12, 0.0))
	if opt == "C":                                     # TaskNote nudged right of the page
		_shift(["TaskNote"], Vector3(0.09, 0.0, 0.0))
		for l in root.find_children("*", "Label3D", true, false):
			if (l as Label3D).text.begins_with("TASK"):
				(l as Node3D).global_position += Vector3(0.09, 0, 0)
	print("TODAY_MOCK %s centre %s scale %.2f depth %.2f -> %.2f" % [opt, p1, s, r0, r1])


func _rect(cam: Camera3D, page: Node3D) -> Rect2:
	var ink := page.get_node("Ink") as MeshInstance3D
	var b := ink.get_aabb()
	var r := Rect2(cam.unproject_position(ink.global_transform * b.position), Vector2.ZERO)
	for i in 8:
		r = r.expand(cam.unproject_position(ink.global_transform * b.get_endpoint(i)))
	return r


func _depth_on_plane(cam: Camera3D, px: Vector2, y: float) -> float:
	var d := cam.project_ray_normal(px)
	var t := (y - cam.global_position.y) / d.y
	return (d * t).dot(-cam.global_basis.z)


func _shift(names: Array, by: Vector3) -> void:
	for n in names:
		for c in get_tree().current_scene.find_children(n, "Node3D", true, false):
			(c as Node3D).global_position += by


func _arg(key: String, default: String) -> String:
	var a := OS.get_cmdline_user_args()
	var i := a.find(key)
	return a[i + 1] if i >= 0 and i + 1 < a.size() else default
