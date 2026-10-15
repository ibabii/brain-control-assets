extends Node3D
## Two flies for look-dev with the cockpit preview (--extra res://previews/fly/fly_preview.tscn):
## one buzzing in front of the seat, one resting on the console.


func _ready() -> void:
	_fly(Vector3(-0.12, 1.2, 0.42), Vector3(0, 30, 0), "buzz", 0.01)
	_fly(Vector3(0.14, 0.973, 0.16), Vector3(18, -40, 0), "rest", 0.0)


func _fly(pos: Vector3, deg: Vector3, clip: String, t: float) -> void:
	var fly: Node3D = load("res://fly/art/fly.tscn").instantiate()
	add_child(fly)
	fly.position = pos
	fly.rotation_degrees = deg
	var anim: AnimationPlayer = fly.find_child("Anim", true, false)
	anim.play(clip)
	anim.seek(t, true)
	anim.pause()
