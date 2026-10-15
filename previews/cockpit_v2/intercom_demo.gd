extends Node3D
## Preview only (not delivered): draws a line on the intercom Display with the 5x7 glyphs
## (cockpit/art/intercom/dotmatrix_5x7.json) through a dot shader and lights one caller lamp, roughly as gameplay will.
## Use with the cockpit preview: --extra res://previews/cockpit_v2/intercom_demo.tscn
## Args: --ic-text "..." --ic-lamp Brain|Heart|Stomach|Gary --ic-cells N (default 20) --ic-dark (cockpit lights at 4%) --ic-energy E (lit dot brightness; glow test)
## Brain lines use peach-pink dots, every other caller amber (game-ux).

const SHADER := """
shader_type spatial;
render_mode unshaded;
uniform sampler2D text_tex : filter_nearest;
uniform vec2 grid = vec2(120.0, 9.0);      // dots across, dots down (cells * 6, 7 + 2)
uniform vec3 lit : source_color = vec3(1.0, 0.62, 0.22);
uniform vec3 off : source_color = vec3(0.13, 0.09, 0.05);
uniform float energy = 1.0;               // >1.6 crosses the cockpit glow threshold
void fragment() {
	vec2 g = UV * grid;                       // Godot UV (0,0) = top-left of the display
	float on = texture(text_tex, (floor(g) + 0.5) / grid).r;
	float m = smoothstep(0.47, 0.34, length(fract(g) - 0.5));
	ALBEDO = mix(vec3(0.03), mix(off, lit * energy, on), m);
}
"""

func _ready() -> void:
	await get_tree().process_frame
	var args := OS.get_cmdline_user_args()
	var text := 'WE NEED TO TALK.'
	var lamp := 'Heart'
	if args.has('--ic-text'):
		text = args[args.find('--ic-text') + 1]
	if args.has('--ic-lamp'):
		lamp = args[args.find('--ic-lamp') + 1]
	var cells := int(args[args.find('--ic-cells') + 1]) if args.has('--ic-cells') else 20
	var font: Dictionary = JSON.parse_string(FileAccess.get_file_as_string('res://cockpit/art/intercom/dotmatrix_5x7.json'))['glyphs']
	var img := Image.create(cells * 6, 9, false, Image.FORMAT_L8)
	var up := text.to_upper()
	var pad := (cells - mini(up.length(), cells)) / 2          # centred
	for i in mini(up.length(), cells):
		var rows: Array = font.get(up[i], font['?'])
		for y in 7:
			for x in 5:
				if rows[y][x] == '1':
					img.set_pixel((pad + i) * 6 + x, y + 1, Color.WHITE)
	var root := get_tree().current_scene
	var display := root.find_child('Display', true, false) as MeshInstance3D
	var mat := ShaderMaterial.new()
	mat.shader = Shader.new()
	mat.shader.code = SHADER
	mat.set_shader_parameter('text_tex', ImageTexture.create_from_image(img))
	mat.set_shader_parameter('grid', Vector2(cells * 6, 9))
	if lamp == 'Brain':
		mat.set_shader_parameter('lit', Color(1.0, 0.66, 0.58))
		mat.set_shader_parameter('off', Color(0.13, 0.08, 0.07))
	if args.has('--ic-energy'):
		mat.set_shader_parameter('energy', float(args[args.find('--ic-energy') + 1]))
	display.material_override = mat
	var lit: Dictionary = JSON.parse_string(FileAccess.get_file_as_string('res://cockpit/art/layout.json'))['intercom']['lamp_lit']
	_glow(root.find_child(lamp, true, false) as MeshInstance3D, Color.html(lit[lamp]))
	_glow(root.find_child('Lamp', true, false) as MeshInstance3D, Color(0.94, 0.63, 0.25))   # answering machine "1"
	if args.has('--ic-dark'):
		for l in root.find_children('*', 'Light3D', true, false):
			(l as Light3D).light_energy *= 0.04
		for w in root.find_children('*', 'WorldEnvironment', true, false):
			var env := (w as WorldEnvironment).environment
			env.ambient_light_energy *= 0.04
			env.background_energy_multiplier *= 0.04

func _glow(l: MeshInstance3D, col: Color) -> void:
	if l:
		var glow := (l.get_active_material(0) as BaseMaterial3D).duplicate() as BaseMaterial3D
		glow.albedo_color = col
		glow.emission_enabled = true
		glow.emission = col
		glow.emission_energy_multiplier = 2.5
		l.material_override = glow
