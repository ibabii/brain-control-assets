extends Node3D
## Character-system phase 1 mock (coordination/character_system_plan.md): line-ups of the mock bodies
## (previews/characters/mock/<id>/, scripts/characters/mock_build.sh) in a stage, posed or playing a clip.
## godot --path . res://previews/characters/mock_preview.tscn -- --capture NAME --models id,id,..
##   [--clip NAME --times "0,0.5"] [--from ID]  clip from ID's library on every model (shared clips, motion-normalised)
##   [--tones "#hex,.."]   skin tone per model (one model + several tones = that model repeated)
##   [--chest "0,0.5,1"]   Chest_Size per model (one model + several values = repeated)
##   [--stage grey|flat|kitchen|bathroom] [--spacing M] [--ragdoll --t S [--follow]] [--size WxH] [--cols N]
##   [--shots "name@eye@look[@fov];..."]   (contact sheet in screenshots/NAME.png)
##   [--bend "Bone:deg,.."]   swing bones about their X (spring chain test)
##   [--faces "rest,wink,.."]  expression per model (head part.json `expressions`, applied like the game)
## T-pose = the bind pose (no clip). Everything here is preview-only.

const MOCK := 'res://previews/characters/mock/'
var camera: Camera3D
var humans: Array[Node3D] = []
var args: PackedStringArray


func _ready() -> void:
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	args = OS.get_cmdline_user_args()
	var stage := _arg('--stage', 'grey')
	match stage:
		'kitchen':
			_kitchen()
		'bathroom':
			_bathroom()
		'flat':
			_flat()
		_:
			_grey()
	var ids := _arg('--models', 'bernard_b').split(',')
	var tones := _arg('--tones', '').split(',', false)
	var chest := _arg('--chest', '').split(',', false)
	var faces := _arg('--faces', '').split(',', false)
	var n := maxi(maxi(ids.size(), faces.size()), maxi(tones.size(), chest.size()))
	var spacing := float(_arg('--spacing', '0.9'))
	var x0 := float(_arg('--x', '0'))
	for i in n:
		var id := ids[mini(i, ids.size() - 1)]
		var h: Node3D = _load(id)
		h.position = Vector3(x0 + ((n - 1) / 2.0 - i) * spacing, 0, float(_arg('--z', '0')))   # camera at -Z: screen left = +X
		h.rotation_degrees.y = float(_arg('--yaw', '0'))
		add_child(h)
		humans.append(h)
		for v in h.find_children('*', 'VisualInstance3D', true, false):
			v.layers = 1
		if tones.size():
			_tone(h, Color(tones[mini(i, tones.size() - 1)]))
		if chest.size():
			_chest(h, float(chest[mini(i, chest.size() - 1)]))
		if faces.size():
			_face(h, id.split(':')[0], faces[mini(i, faces.size() - 1)])
	if '--clip' in args:
		_share(_arg('--from', ''))
	else:
		for h in humans:
			_bind_pose(h)
	if '--ragdoll' in args:
		_floor()
		for h in humans:
			h.rotation_degrees.x += 9.0
			_ragdoll.call_deferred(h)
	camera = Camera3D.new()
	camera.near = 0.02
	add_child(camera)
	camera.current = true
	if '--capture' in args:
		_capture(_arg('--capture', 'mock'))


## Phase 1 mock id, or a phase 2 base with overrides: male_base:Build_Heavy=1:top=:c.skin=B9784F
## (shape=value, slot=part id ('' = none), c.<colour slot>=hex).
func _load(id: String) -> Node3D:
	if not id.contains('_base'):
		return load(MOCK + id + '/human.glb').instantiate()
	var bits := id.split(':')
	var over := {'parts': {}, 'shapes': {}, 'colors': {}}
	for b in bits.slice(1):
		var kv := b.split('=')
		if kv[0].begins_with('c.'):
			over.colors[kv[0].substr(2)] = '#' + kv[1]
		elif kv[0] in ['head', 'hair', 'top', 'bottom', 'shoes']:
			over.parts[kv[0]] = kv[1]
		else:
			over.shapes[kv[0]] = float(kv[1])
	return CharacterAssembler.build(bits[0], over)


func _arg(k: String, d: String) -> String:
	return args[args.find(k) + 1] if k in args else d


## Every model plays --clip; with --from, from that model's library (the shared-clip test).
func _share(src_id: String) -> void:
	var lib: AnimationLibrary = null
	if src_id != '':
		var src: Node3D = _load(src_id)
		lib = src.get_node('Anim').get_animation_library('').duplicate()   # its own copy: the source body plays it too
		src.free()
	for h in humans:
		var ap: AnimationPlayer = h.get_node('Anim')
		var name := _arg('--clip', 'idle')
		if lib:
			if not ap.has_animation_library('shared'):
				ap.add_animation_library('shared', lib)
			name = 'shared/' + name
		ap.play(name)
		ap.pause()


## The T-pose: the skin's bind (the Skeleton rest is the arms-down design pose, like RESET).
func _bind_pose(h: Node3D) -> void:
	var sk: Skeleton3D = h.get_node('Rig/Skeleton')
	var mi: MeshInstance3D = h.find_children('*', 'MeshInstance3D', true, false).filter(func(m): return m.skin != null)[0]
	var glob := {}
	for i in mi.skin.get_bind_count():
		glob[sk.find_bone(mi.skin.get_bind_name(i))] = mi.skin.get_bind_pose(i).affine_inverse()
	for b in sk.get_bone_count():                      # parents come first in the bone order
		if not glob.has(b):
			continue
		var p := sk.get_bone_parent(b)
		var pg: Transform3D = glob[p] if glob.has(p) else (sk.get_bone_global_rest(p) if p >= 0 else Transform3D())
		var local: Transform3D = pg.affine_inverse() * glob[b]
		sk.set_bone_pose_rotation(b, local.basis.get_rotation_quaternion())
		sk.set_bone_pose_position(b, local.origin)


## Skin tone: every surface whose material is the shared Skin material (head, neck, hands).
func _tone(h: Node3D, c: Color) -> void:
	for m in h.find_children('*', 'MeshInstance3D', true, false):
		for s in m.get_surface_override_material_count():
			var mat: Material = m.mesh.surface_get_material(s)
			if mat and mat.resource_name.contains('Skin'):
				var d: StandardMaterial3D = mat.duplicate()
				d.albedo_color = c
				m.set_surface_override_material(s, d)


func _chest(h: Node3D, v: float) -> void:
	for m in h.find_children('*', 'MeshInstance3D', true, false):
		var i: int = m.find_blend_shape_by_name('Chest_Size')
		if i >= 0:
			m.set_blend_shape_value(i, v)


func _ragdoll(h: Node3D) -> void:
	await get_tree().physics_frame
	h.get_node('Rig/Skeleton/Ragdoll').physical_bones_start_simulation()


func _floor() -> void:
	var floor := StaticBody3D.new()
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(20, 1, 20)
	col.shape = box
	col.position = Vector3(0, -0.5, 0)
	floor.add_child(col)
	add_child(floor)


func _env(bg: Color, amb: Color, amb_e: float) -> Environment:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = bg
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = amb
	env.ambient_light_energy = amb_e
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	return env


func _box(size: Vector3, pos: Vector3, c: Color) -> void:
	var m := MeshInstance3D.new()
	var b := BoxMesh.new()
	b.size = size
	var mat := StandardMaterial3D.new()
	mat.albedo_color = c
	b.material = mat
	m.mesh = b
	m.position = pos
	add_child(m)


## Flat light for shape reviews: strong ambient, a weak frontal fill, no shadows.
func _flat() -> void:
	_env(Color('#D9D9D9'), Color(1, 1, 1), 0.85)
	var fill := DirectionalLight3D.new()
	fill.light_energy = 0.45
	fill.rotation_degrees = Vector3(-15, 180, 0)
	add_child(fill)
	_box(Vector3(20, 0.1, 20), Vector3(0, -0.05, 0), Color('#E6E6E6'))


func _grey() -> void:
	_env(Color('#D9D9D9'), Color(1, 0.97, 0.93), 0.55)
	var key := DirectionalLight3D.new()
	key.light_color = Color(1, 0.94, 0.85)
	key.light_energy = 1.2
	key.shadow_enabled = true
	key.rotation_degrees = Vector3(-38, 150, 0)
	add_child(key)
	var fill := DirectionalLight3D.new()
	fill.light_energy = 0.6
	fill.rotation_degrees = Vector3(-30, -20, 0)
	add_child(fill)
	_box(Vector3(20, 0.1, 20), Vector3(0, -0.05, 0), Color('#E6E6E6'))


## The game's kitchen greybox lighting (brain-control-simulator locations/kitchen/kitchen.tscn, read-only copy):
## sky background, warm ambient 0.55, one sun (-50, 30) with shadows, peach walls, cream floor, green counter.
func _kitchen() -> void:
	_env(Color(0.72, 0.84, 0.95), Color(1, 0.96, 0.9), 0.55)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	sun.shadow_enabled = true
	add_child(sun)
	_box(Vector3(8, 0.1, 8), Vector3(0, -0.05, 0), Color(0.93, 0.88, 0.78))
	_box(Vector3(8, 3, 0.1), Vector3(0, 1.5, 2.2), Color(0.98, 0.83, 0.62))         # wall behind the line-up
	_box(Vector3(0.1, 3, 8), Vector3(-3.5, 1.5, 0), Color(0.98, 0.83, 0.62))
	_box(Vector3(2.4, 0.9, 0.6), Vector3(2.6, 0.45, 1.6), Color(0.36, 0.62, 0.55))


## The bathroom art with the bathroom preview's greybox lights (previews/bathroom/bathroom_preview.gd).
func _bathroom() -> void:
	var env := _env(Color(0.75, 0.85, 0.92), Color(0.95, 0.97, 1), 0.6)
	env.ssao_enabled = true
	add_child(load('res://bathroom/art/bathroom_room.tscn').instantiate())
	var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string('res://bathroom/art/layout.json'))
	for id in layout.props:
		var p: Array = layout.props[id]
		var holder := Node3D.new()
		holder.position = Vector3(p[0], p[1], p[2])
		add_child(holder)
		holder.add_child(load('res://bathroom/art/props/%s.tscn' % id).instantiate())
		for n in ['Glob', 'Splats', 'Stream', 'Puddle', 'Drops']:
			var x := holder.find_child(n, true, false)
			if x:
				x.visible = false
		if id == 'smudge':
			holder.visible = false
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-60, 25, 0)
	sun.light_energy = 0.6
	sun.shadow_enabled = true
	add_child(sun)
	var lamp := OmniLight3D.new()
	lamp.position = Vector3(0, 2.4, 0.4)
	lamp.light_color = Color(1, 0.95, 0.85)
	lamp.light_energy = 1.4
	lamp.omni_range = 5.0
	lamp.shadow_enabled = true
	add_child(lamp)


func _capture(name: String) -> void:
	var size := Vector2i(1200, 1200)
	if '--size' in args:
		var p := _arg('--size', '').split('x')
		size = Vector2i(int(p[0]), int(p[1]))
	get_window().size = size
	var dir := 'res://previews/characters/screenshots/'
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	for n in 10:
		await get_tree().process_frame
	await get_tree().create_timer(float(_arg('--t', '0.3'))).timeout
	var items := _arg('--shots', 'front@0,0.95,-12@0,0.95,0@10').split(';', false)
	var times: Array = [-1.0]
	if '--times' in args:
		times = Array(_arg('--times', '0').split(',')).map(func(x): return float(x))
	var tiles: Array[Image] = []
	var multi := times.size() * items.size() > 1
	var c := Vector3.ZERO                               # --follow: shots are offsets from the bodies' Hips
	if '--follow' in args:                             # (the simulated body: the Physical Bone, not the bone pose)
		for h in humans:
			c += (h.find_child('Physical Bone Hips', true, false) as Node3D).global_position / humans.size()
		c.y = 0.0
	for t in times:
		if t >= 0.0:
			for h in humans:
				var ap: AnimationPlayer = h.get_node('Anim')
				ap.seek(t, true)
		if '--bend' in args:                           # --bend "Bone:deg,Bone:deg": swing bones about X (spring test)
			for h in humans:
				var sk: Skeleton3D = h.find_children('*', 'Skeleton3D', true, false)[0]
				for b in _arg('--bend', '').split(','):
					var kv := b.split(':')
					var i := sk.find_bone(kv[0])
					sk.set_bone_pose_rotation(i, sk.get_bone_rest(i).basis.get_rotation_quaternion()
						* Quaternion(Vector3.RIGHT, deg_to_rad(float(kv[1]))))
		for item in items:
			var part: PackedStringArray = item.split('@')
			var e := part[1].split(',')
			var l := part[2].split(',')
			camera.position = c + Vector3(float(e[0]), float(e[1]), float(e[2]))
			camera.look_at(c + Vector3(float(l[0]), float(l[1]), float(l[2])))
			camera.fov = float(part[3]) if part.size() > 3 else 30.0
			for n in 4:
				await RenderingServer.frame_post_draw
			var img := get_viewport().get_texture().get_image()
			if multi:
				img.resize(800, int(800.0 * img.get_height() / img.get_width()))
			tiles.append(img)
	var tw := tiles[0].get_width()
	var th := tiles[0].get_height()
	var cols := mini(int(_arg('--cols', '2')), tiles.size())
	var sheet := Image.create(tw * cols, th * ceili(tiles.size() / float(cols)), false, tiles[0].get_format())
	for i in tiles.size():
		sheet.blit_rect(tiles[i], Rect2i(0, 0, tw, th), Vector2i((i % cols) * tw, (i / cols) * th))
	sheet.save_png(dir + name + '.png')
	print('MOCK_SHEET ', dir + name + '.png')
	get_tree().quit()


## Expression from the head part's table, with the game's rules (src/human/human_avatar.gd): one mouth shows
## (Smile unless the expression shows another), lids only where the expression shows them (the game adds blinks),
## LidHalf off unless shown; brow [raise, tilt], pupil, look, mouth scale, lid (deg, or [L, R]).
func _face(h: Node3D, base: String, name: String) -> void:
	var cj: Dictionary = JSON.parse_string(FileAccess.get_file_as_string('res://characters/%s/art/character.json' % base))
	var head: String = cj.parts.head
	var pj: Dictionary = JSON.parse_string(FileAccess.get_file_as_string('res://characters/parts/%s/art/part.json' % head))
	var e: Dictionary = pj.expressions[name]
	var f := func(n: String) -> Node3D: return h.find_child(n, true, false) as Node3D
	var show: Array = e.get('show', [])
	var mouths: Array = pj.get('mouths', ['Smile', 'Open', 'O', 'Flat', 'Grimace', 'Wobble'])
	var mouth := 'Smile'
	for m in show:
		if m in mouths:
			mouth = m
	for m in mouths:
		if f.call(m):
			f.call(m).visible = m == mouth
	for n in ['LidL', 'LidR', 'LidHalfL', 'LidHalfR', 'ShutL', 'ShutR', 'BlushHotL', 'BlushHotR']:
		if f.call(n):
			f.call(n).visible = n in show
	for n in show:
		if f.call(n):
			f.call(n).visible = true
	for n in e.get('hide', []):
		if f.call(n):
			f.call(n).visible = false
	var brow: Array = e.get('brow', [0.0, 0.0])
	var lid = e.get('lid', null)
	for side in ['L', 'R']:
		var s := -1.0 if side == 'L' else 1.0
		var b: Node3D = f.call('Brow' + side)
		b.position.y += brow[0]
		b.rotation_degrees.z += -s * brow[1]
		if lid != null:
			f.call('Lid' + side).rotation_degrees.x = lid[0 if side == 'L' else 1] if lid is Array else lid
		if e.get('look') != null:
			var g: Array = e.look[0 if side == 'L' else 1]
			f.call('Look' + side).rotation_degrees = Vector3(g[1], g[0], 0)
		for p in ['Pupil', 'Glint']:
			f.call(p + side).scale = Vector3(e.get('pupil', 1.0), e.get('pupil', 1.0), 1.0)
	var m: float = e.get('mouth', 1.0)
	for n in ['Open', 'Tongue']:
		if m != 1.0:
			f.call(n).scale = Vector3(m, m * 1.25, 1.0)
