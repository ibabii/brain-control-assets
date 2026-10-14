extends SceneTree
## Checks the control art contract (coordination/interfaces.md). Run:
## Godot --headless --path . --script res://previews/cockpit_v2/check_controls.gd

const PRESS := {'left_keys': 0.012, 'panic_button': 0.015, 'simon_pad': 0.012, 'arrow_keys': 0.012}
var fails := 0

func _init() -> void:
	for name in ['left_keys', 'panic_button', 'joystick', 'lever', 'simon_pad', 'arrow_keys']:
		var root: Node3D = load('res://cockpit/art/controls/%s.glb' % name).instantiate()
		var aabb := AABB()
		var first := true
		for n in _all(root):
			if n is MeshInstance3D:
				var b: AABB = n.transform * n.mesh.get_aabb() if n.get_parent() == root else n.get_parent().transform * (n.transform * n.mesh.get_aabb())
				aabb = b if first else aabb.merge(b)
				first = false
			if n.get_script() != null or n is AnimationPlayer or n is CollisionObject3D:
				_fail(name, '%s has script/animation/collision' % n.name)
			if n.name.begins_with('Cap_'):
				_check_cap(name, n)
		if name in ['joystick', 'lever']:
			for p in ['Pivot', 'Pivot/Knob']:
				if not root.has_node(p):
					_fail(name, 'missing ' + p)
		if name in ['joystick', 'lever', 'simon_pad', 'arrow_keys'] and (aabb.size.x > 0.24 or aabb.size.z > 0.19):
			_fail(name, 'footprint %.3f x %.3f exceeds 0.24 x 0.19' % [aabb.size.x, aabb.size.z])
		if name in PRESS:
			# Pressed cap top must stay at least 3 mm above every housing surface it sits over.
			for c in root.get_children():
				if not c.name.begins_with('Cap_'):
					continue
				var pressed_top: float = c.position.y - PRESS[name]
				for h in root.get_children():
					if h is MeshInstance3D and not h.name.begins_with('Cap_'):
						var hb: AABB = h.transform * h.mesh.get_aabb()
						var over := hb.has_point(Vector3(c.position.x, hb.get_center().y, c.position.z))
						if over and h.name.begins_with('Ring_') and h.name.trim_prefix('Ring_') == c.name.trim_prefix('Cap_'):
							over = false   # the cap's own ring has a hole for it
						if over and pressed_top < hb.end.y + 0.003:
							_fail(name, '%s pressed top %.4f not above %s top %.4f' % [c.name, pressed_top, h.name, hb.end.y])
		print('CONTROL %s size=(%.3f, %.3f, %.3f) caps=%s' % [name, aabb.size.x, aabb.size.y, aabb.size.z,
			root.get_children().filter(func(c): return c.name.begins_with('Cap_')).map(func(c): return c.name)])
		root.free()
	print('CONTROLS_CHECK ', 'PASS' if fails == 0 else 'FAIL %d' % fails)
	quit(1 if fails else 0)

func _check_cap(module: String, n: Node) -> void:
	if not n is MeshInstance3D:
		_fail(module, '%s is not a MeshInstance3D' % n.name)
		return
	var mesh: Mesh = (n as MeshInstance3D).mesh
	if mesh.get_surface_count() != 1:
		_fail(module, '%s has %d surfaces' % [n.name, mesh.get_surface_count()])
	var top: float = mesh.get_aabb().end.y
	if absf(top) > 0.0015:
		_fail(module, '%s origin is %.4f below its top face' % [n.name, top])

func _all(n: Node) -> Array:
	var out := [n]
	for c in n.get_children():
		out.append_array(_all(c))
	return out

func _fail(module: String, msg: String) -> void:
	fails += 1
	print('CONTROL_FAIL %s: %s' % [module, msg])
