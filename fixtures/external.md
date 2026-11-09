# Examples that use names from other files

Uses a class defined in another file:

```gdscript
extends Node

var stats: PlayerStatsResource

func _ready() -> void:
	stats = PlayerStatsResource.new()
```

Preloads a scene that is not in this project:

```gdscript
extends Node

const Bullet := preload("res://bullet.tscn")

func fire() -> void:
	var b := Bullet.instantiate()
	add_child(b)
```
