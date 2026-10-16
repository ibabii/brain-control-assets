extends Node3D
## Preview only (not delivered): the desk octopus rehung as a car-dice toy, to compare hang points.
## Use with the cockpit preview: --extra res://previews/cockpit_v2/octo_hang_mock.tscn
## Args: --octo ad|ad_out|ad_fwd|arm (hang point) --octo-swing DEG (+ = outward, away from the screens; - = toward them)

const BODY_W := 0.06
## hook, cord length, wire-arm root (null: hook hangs in the cables)
const VARIANTS := {
	"ad": [Vector3(1.02, 1.60, -0.47), 0.16, null],          # as specified: the body lands inside RightPanelBack
	"ad_out": [Vector3(1.15, 1.60, -0.47), 0.16, null],      # clears the back shell, but the cable bundle hides it
	"ad_fwd": [Vector3(1.12, 1.60, -0.30), 0.16, null],      # forward of the cables: visible from the seat
	"arm": [Vector3(1.0, 1.185, -0.2), 0.07, Vector3(0.972, 1.185, -0.272)],
}
const PARTS := ["Octopus", "OctopusTentacles", "OctopusEyes", "OctopusSmile"]


func _ready() -> void:
	await get_tree().process_frame
	var args := OS.get_cmdline_user_args()
	var v: Array = VARIANTS[_arg(args, "--octo", "ad")]
	var swing := float(_arg(args, "--octo-swing", "0"))
	var root := get_tree().current_scene
	var meshes: Array[MeshInstance3D] = []
	for n in PARTS:
		var m := _find_exact(root, n)
		if m:
			meshes.append(m)
	var box := AABB()
	for i in meshes.size():
		var b := meshes[i].global_transform * meshes[i].get_aabb()
		box = b if i == 0 else box.merge(b)
	var s := BODY_W / box.size.x
	var hook: Vector3 = v[0]
	var cord: float = v[1]
	var pivot := Node3D.new()
	add_child(pivot)
	pivot.global_position = hook
	pivot.rotation_degrees.z = swing                       # +Z tilt carries the body toward +X (outward)
	var body := Node3D.new()
	pivot.add_child(body)
	body.position = Vector3(0, -cord - box.size.y * s / 2, 0)
	var top := box.get_center() + Vector3(0, box.size.y / 2, 0)
	for m in meshes:
		var d := m.duplicate() as MeshInstance3D
		body.add_child(d)
		var t := m.global_transform
		t.origin -= box.get_center()
		d.transform = Transform3D(Basis().scaled(Vector3.ONE * s), Vector3.ZERO) * t
		m.visible = false                                  # the desk octopus goes away
	_cylinder(pivot, Vector3.ZERO, Vector3(0, -cord, 0), 0.0012, Color(0.23, 0.23, 0.21))
	_sphere(pivot, Vector3(0, -cord * 0.35, 0), 0.005, Color(0.85, 0.63, 0.3))        # honey bead
	_sphere(self, hook, 0.006, Color(0.3, 0.31, 0.3))                                    # cup hook
	if v[2] != null:
		_cylinder(self, v[2], hook, 0.0025, Color(0.55, 0.55, 0.52))                      # bent wire arm
		_cylinder(self, v[2] + Vector3(0, 0.012, 0), v[2] - Vector3(0, 0.012, 0), 0.012, Color(0.85, 0.8, 0.6))  # tape wrap
	print("OCTO_MOCK body centre ", body.global_position, " scale ", s, " top ", top)


func _find_exact(n: Node, name: String) -> MeshInstance3D:
	for c in n.find_children(name + "*", "MeshInstance3D", true, false):
		if c.name == name or c.name.begins_with(name + "_") or c.name == name + "001":
			return c
	return n.find_child(name, true, false) as MeshInstance3D


func _cylinder(parent: Node3D, a: Vector3, b: Vector3, r: float, col: Color) -> void:
	var m := MeshInstance3D.new()
	var c := CylinderMesh.new()
	c.top_radius = r
	c.bottom_radius = r
	c.height = a.distance_to(b)
	m.mesh = c
	m.material_override = _mat(col)
	parent.add_child(m)
	var up := (b - a).normalized()
	var side := up.cross(Vector3.FORWARD if absf(up.z) < 0.9 else Vector3.RIGHT).normalized()
	m.transform = Transform3D(Basis(side, up, side.cross(up)), (a + b) / 2)


func _sphere(parent: Node3D, p: Vector3, r: float, col: Color) -> void:
	var m := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = r
	sm.height = r * 2
	m.mesh = sm
	m.material_override = _mat(col)
	parent.add_child(m)
	m.position = p


func _mat(col: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = col
	m.roughness = 0.6
	return m


func _arg(args: PackedStringArray, key: String, default: String) -> String:
	var i := args.find(key)
	return args[i + 1] if i >= 0 and i + 1 < args.size() else default
