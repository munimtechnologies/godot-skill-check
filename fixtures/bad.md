# Examples that fail Godot's check

A save manager:

```gdscript
extends Node

const SAVE_PATH := "user://save.json"

func load_game() -> Dictionary:
	var file := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if file == null:
		return {}
	var parsed := JSON.parse_string(file.get_as_text())
	if parsed is Dictionary:
		return parsed
	return {}
```

A player script:

```gdscript
extends KinematicBody2D

onready var timer = $Timer
var velocity = Vector2()

func _physics_process(delta):
	velocity = move_and_slide(velocity, Vector2.UP)
	yield(get_tree().create_timer(rand_range(0.1, 0.5)), "timeout")
```

An enemy script:

```gdscript
extends Node2D

var health := 3

func take_hit() -> void:
	health -= 1
	if health <= 0:
		die()
```
