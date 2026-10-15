@tool
extends EditorScenePostImport
## Post-import for fly/art/fly.glb: AnimationPlayer -> Anim, "buzz" loops.


func _post_import(scene: Node) -> Object:
	var anim: AnimationPlayer = scene.get_node("AnimationPlayer")
	anim.name = "Anim"
	anim.get_animation("buzz").loop_mode = Animation.LOOP_LINEAR
	return scene
