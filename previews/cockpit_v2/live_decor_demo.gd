extends Node
## Preview only: drives the live decor like gameplay will. Pilot lights from layout.json (lit colour, emission energy)
## and the MENTAL BANDWIDTH fill (BandwidthFill scale.x).
## Args: --pilots PWR,OOPS (lit ones) --bandwidth 0.6

func _ready() -> void:
	await get_tree().process_frame
	var args := OS.get_cmdline_user_args()
	var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://cockpit/art/layout.json"))
	var root := get_tree().current_scene
	var lit := Color.html(layout["pilot_lights"]["lit"])
	var on := (args[args.find("--pilots") + 1] if args.has("--pilots") else "PWR,OOPS").split(",")
	for n in on:
		var bulb := root.find_child("PilotLights", true, false).get_node(n) as MeshInstance3D
		var m := (bulb.get_active_material(0) as BaseMaterial3D).duplicate() as BaseMaterial3D
		m.albedo_color = lit
		m.emission_enabled = true
		m.emission = lit
		m.emission_energy_multiplier = layout["pilot_lights"]["energy"]
		bulb.material_override = m
	var fill := root.find_child("BandwidthFill", true, false) as Node3D
	fill.scale.x = float(args[args.find("--bandwidth") + 1]) if args.has("--bandwidth") else 0.6
	print("LIVE_DECOR pilots ", on, " bandwidth ", fill.scale.x)
