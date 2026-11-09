# Fragments

A helper function on its own:

```gdscript
func heal(amount: int) -> void:
	health = min(health + amount, 100)
```

A fragment with its base class given:

<!-- gdcheck: extends CharacterBody2D -->
```gdscript
func _physics_process(delta: float) -> void:
	velocity.y += 980.0 * delta
	move_and_slide()
```

A fragment whose base class has no velocity:

<!-- gdcheck: extends Node2D -->
```gdscript
func _ready() -> void:
	velocity.x = 1.0
```
