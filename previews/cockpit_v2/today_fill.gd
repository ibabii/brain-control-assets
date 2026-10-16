extends Node
## Preview only: fills the TODAY list with 6 rows, the first 2 ticked (game-ux readability check).
## Use with the cockpit preview: --extra res://previews/cockpit_v2/today_fill.tscn

const ROWS := ["Mop kitchen floor", "Be a functional human", "Mom's pills: HEMOZEN", "Return the parcel",
	"Pet the cat/kind of", "It's okay. :)"]

func _ready() -> void:
	await get_tree().process_frame
	var list := get_tree().current_scene.find_child("Today", true, false).get_node("Page/List")
	for i in ROWS.size():
		var item := list.get_node("Item%d" % i) as Control
		item.visible = true
		(item.get_node("Text") as RichTextLabel).text = ROWS[i]
		(item.get_node("Box/Tick") as Control).visible = i < 2
