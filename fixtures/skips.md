# Blocks that are not checked

Skipped on purpose:

<!-- gdcheck: skip -->
```gdscript
extends KinematicBody2D
onready var sprite = $Sprite
```

❌ Bad:

```gdscript
extends KinematicBody2D
onready var sprite = $Sprite
```

Migration example:

```gdscript
# Before
extends KinematicBody2D
onready var sprite = $Sprite
```

Some Python, which is ignored:

```python
print("not GDScript")
```

A fragment:

```gdscript
velocity.x = 5.0
```
