class_name CharacterAssembler
## Reference assembler for the "Characters" contract (coordination/interfaces.md), preview-only:
## base body + parts from character.json (or overrides) -> one Node3D on the base skeleton.
## Skinned part meshes move onto the base Skeleton (bind by bone name); the rest of the part (face tree, hair) rides
## a BoneAttachment3D whole (part.json "attach", default Head), authored in character space at rest (as the game's
## CharacterBuilder). "hides" turns off Body_<Region> meshes.
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
	var pshapes: Dictionary = {}                     # part.json "shapes" (a hat's Hair_Hat), under the character's
	for slot in parts:
		if parts[slot] == '':
			continue
		var pdir: String = ROOT + 'parts/' + parts[slot] + '/art/'
		var pj: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(pdir + 'part.json'))
		hidden += pj.get('hides', [])
		pshapes.merge(pj.get('shapes', {}), true)
		var p: Node3D = load(pdir + parts[slot] + '.tscn').instantiate()
		_add_bones(sk, p, pj.get('bones', []))
		var att := BoneAttachment3D.new()
		att.name = 'Part_' + slot
		sk.add_child(att)
		att.bone_name = pj.get('attach', 'Head')
		for m: MeshInstance3D in p.find_children('*', 'MeshInstance3D', true, false):
			if m.skin:
				m.get_parent().remove_child(m)
				m.owner = null
				sk.add_child(m)
				m.transform = Transform3D()
				m.skeleton = m.get_path_to(sk)
		att.add_child(p)                               # the rest (face tree, hair) rides the bone whole, like the game
		p.transform = sk.get_bone_global_rest(sk.find_bone(att.bone_name)).affine_inverse() * p.transform
		for h in pj.get('hidden', []):
			var n := p.find_child(h, true, false) as Node3D
			if n:
				n.visible = false
	for m: MeshInstance3D in ch.find_children('Body_*', 'MeshInstance3D', true, false):
		m.visible = not m.name in hidden
	var shapes: Dictionary = pshapes
	shapes.merge(cj.get('shapes', {}), true)
	shapes.merge(over.get('shapes', {}), true)
	var colors: Dictionary = cj.get('colors', {}).duplicate()
	colors.merge(over.get('colors', {}), true)
	colors.hair = hair_for(Color(colors.skin), Color(colors.hair)).to_html(false)
	if colors.get('blush', 'auto') == 'auto':
		colors.blush = auto_blush(Color(colors.skin)).to_html(false)
	for m: MeshInstance3D in ch.find_children('*', 'MeshInstance3D', true, false):
		for s in shapes:
			var i := m.find_blend_shape_by_name(s)
			if i >= 0:
				m.set_blend_shape_value(i, shapes[s])
		for i in m.mesh.get_surface_count():
			var mat: Material = m.get_active_material(i)       # override-aware, like the game's paint
			if mat and cj.paint.has(mat.resource_name) and mat is StandardMaterial3D:
				var slot: PackedStringArray = cj.paint[mat.resource_name].split('*')   # "hair*0.82": shaded slot
				var d: StandardMaterial3D = mat.duplicate()
				d.albedo_color = Color(colors[slot[0]]).darkened(1.0 - float(slot[1])) if slot.size() > 1 \
					else Color(colors[slot[0]])
				m.set_surface_override_material(i, d)
	return ch


## CIE L* (0..100) of an sRGB colour.
static func lstar(c: Color) -> float:
	var lin := func(x: float) -> float: return x / 12.92 if x <= 0.04045 else pow((x + 0.055) / 1.055, 2.4)
	var y: float = 0.2126 * lin.call(c.r) + 0.7152 * lin.call(c.g) + 0.0722 * lin.call(c.b)
	return 116.0 * (pow(y, 1.0 / 3.0) if y > 0.008856 else 7.787 * y + 16.0 / 116.0) - 16.0


## Hair never reads as the skin (contract): |L*(hair) - L*(skin)| >= presets hair_contrast, else the passing preset
## hair closest in L* to the asked one (ties: darker).
static func hair_for(skin: Color, hair: Color) -> Color:
	var pj: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ROOT + 'presets.json'))
	var need: float = pj.get('hair_contrast', 18)
	var ls := lstar(skin)
	if absf(lstar(hair) - ls) >= need:
		return hair
	var best := hair
	var best_d := INF
	for h in pj.hair:
		var lh := lstar(Color(h))
		if absf(lh - ls) < need:
			continue
		var d := absf(lh - lstar(hair)) + (0.001 * lh)
		if d < best_d:
			best_d = d
			best = Color(h)
	return best


## Blush from the skin (contract): rose on light skin, deeper berry on dark, 60% of the way from the skin.
static func auto_blush(skin: Color) -> Color:
	var t := clampf((skin.get_luminance() - 0.3) / 0.45, 0.0, 1.0)
	return skin.lerp(Color('#8E2E4A').lerp(Color('#F08A8A'), t), 0.6)



## Part-declared bones (part.json `bones`: name, parent): added to the body skeleton with their rest from the
## part scene's own skeleton (same names), so bases carry no hair/accessory bones.
static func _add_bones(sk: Skeleton3D, part: Node3D, bones: Array) -> void:
	if bones.is_empty():
		return
	var ps: Skeleton3D = part.find_children('*', 'Skeleton3D', true, false)[0]
	for b in bones:
		if sk.find_bone(b.name) >= 0:
			continue
		var i := sk.get_bone_count()
		sk.add_bone(b.name)
		sk.set_bone_parent(i, sk.find_bone(b.parent))
		sk.set_bone_rest(i, ps.get_bone_rest(ps.find_bone(b.name)))
		sk.reset_bone_pose(i)
