# Examples that compile

A complete Godot 4 player script:

```gdscript
extends CharacterBody2D

const SPEED := 200.0
@export var jump_velocity: float = -400.0
@onready var timer: Timer = $Timer

signal landed

func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity += get_gravity() * delta
	var dir := Input.get_axis("ui_left", "ui_right")
	velocity.x = dir * SPEED
	move_and_slide()

func wait_a_bit() -> void:
	await get_tree().create_timer(0.5).timeout
	landed.emit()
```

A tilde fence works too:

~~~gd
extends Node

func _ready() -> void:
	print("hello")
~~~
