class_name CharacterAssembler
## Reference assembler for the "Characters" contract (coordination/interfaces.md), preview-only:
## base body + parts from character.json (or overrides) -> one Node3D on the base skeleton.
## Skinned part meshes move onto the base Skeleton (bind by bone name); rigid ones ride a BoneAttachment3D
## (part.json "attach", default Head), authored in character space at rest. "hides" turns off Body_<Region> meshes.
## Shapes (blend shapes) and paint (material -> colour slot) go to every mesh.

const ROOT := 'res://characters/'


static func build(base: String, over: Dictionary = {}) -> Node3D:
	var dir := ROOT + base + '/art/'
	var cj: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(dir + 'character.json'))
	var ch: Node3D = load(dir + base + '.tscn').instantiate()
	ch.name = base
	var sk: Skeleton3D = ch.find_children('*', 'Skeleton3D', true, false)[0]
	var parts: Dictionary = cj.parts.duplicate()
	parts.merge(over.get('parts', {}), true)
	var hidden: Array = []
	for slot in parts:
		if parts[slot] == '':
			continue
		var pdir: String = ROOT + 'parts/' + parts[slot] + '/art/'
		var pj: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(pdir + 'part.json'))
		hidden += pj.get('hides', [])
		var p: Node3D = load(pdir + parts[slot] + '.tscn').instantiate()
		var att := BoneAttachment3D.new()
		att.name = 'Part_' + slot
		sk.add_child(att)
		att.bone_name = pj.get('attach', 'Head')
		var rest_inv := sk.get_bone_global_rest(sk.find_bone(att.bone_name)).affine_inverse()
		for m: MeshInstance3D in p.find_children('*', 'MeshInstance3D', true, false):
			var xf := m.global_transform if m.is_inside_tree() else _xf(m, p)
			m.get_parent().remove_child(m)
			m.owner = null
			if m.skin:
				sk.add_child(m)
				m.transform = Transform3D()
				m.skeleton = m.get_path_to(sk)
			else:
				att.add_child(m)
				m.transform = rest_inv * xf
			for h in pj.get('hidden', []):
				if m.name == h:
					m.visible = false
		p.free()
	for m: MeshInstance3D in ch.find_children('Body_*', 'MeshInstance3D', true, false):
		m.visible = not m.name in hidden
	var shapes: Dictionary = cj.get('shapes', {}).duplicate()
	shapes.merge(over.get('shapes', {}), true)
	var colors: Dictionary = cj.get('colors', {}).duplicate()
	colors.merge(over.get('colors', {}), true)
	for m: MeshInstance3D in ch.find_children('*', 'MeshInstance3D', true, false):
		for s in shapes:
			var i := m.find_blend_shape_by_name(s)
			if i >= 0:
				m.set_blend_shape_value(i, shapes[s])
		for i in m.mesh.get_surface_count():
			var mat: Material = m.mesh.surface_get_material(i)
			if mat and cj.paint.has(mat.resource_name) and mat is StandardMaterial3D:
				var d: StandardMaterial3D = mat.duplicate()
				d.albedo_color = Color(colors[cj.paint[mat.resource_name]])
				m.set_surface_override_material(i, d)
	return ch


static func _xf(n: Node3D, root: Node3D) -> Transform3D:
	var t := Transform3D()
	var x: Node = n
	while x and x != root:
		if x is Node3D:
			t = (x as Node3D).transform * t
		x = x.get_parent()
	return t
