---
name: gdcheck
description: Check that the GDScript code blocks in Markdown (Godot agent skills, docs, READMEs, tutorials) compile in Godot 4, using Godot's own --check-only. Use when writing or editing GDScript examples in Markdown, before publishing a Godot skill, or when asked whether example code is valid Godot 4.
license: Apache-2.0
---

# gdcheck: make sure GDScript examples in Markdown compile in Godot 4

From godot-skill-check by MV2 of Munim, Inc. (mv2@munimtech.com), made with AI agents (Anthropic Claude).
In a 2026 check of 280 Godot skills listed on skills.sh, 16% of the complete example scripts failed Godot 4.7.2's
own check. An agent that copies such an example gets a script that does not load. Run gdcheck on any Markdown
with GDScript before you publish it.

## 1. Get gdcheck and Godot

gdcheck is one Python file (standard library only). It needs a Godot 4 binary. Use a fixed release of
godot-skill-check, and read `install_godot.sh` (about 50 lines) before you run it: it downloads the official
Godot Linux build from github.com/godotengine/godot releases and refuses it unless its SHA-512 matches the
`SHA512-SUMS.txt` that the Godot team publishes with that release.

```sh
git clone --depth 1 --branch v0.3.0 https://github.com/munimtechnologies/godot-skill-check /tmp/godot-skill-check
GODOT_VERSION=4.7.2 RUNNER_TEMP=/tmp bash /tmp/godot-skill-check/install_godot.sh   # Linux x86_64
```

The last line printed is `GDCHECK_GODOT=<path>`. If Godot 4 is already installed (macOS, Windows, or a
distribution package), skip the script and pass that binary with `--godot`. Python 3.10+ is needed; nothing
else.

## 2. Check

```sh
python /tmp/godot-skill-check/gdcheck.py --godot "$GDCHECK_GODOT" path/to/skill-or-docs/
```

Each problem is printed as `file.md:LINE: error: <Godot's message> [category]`, with LINE pointing into the
Markdown file. Exit code 0 means no errors.

- `error`: a real problem in the example. Fix it.
- `external`: the example uses a name defined in another file (a `class_name`, an autoload, a missing `preload`).
  That is a warning. If the reader is not expected to have that file, show it or declare a stub.
- `elision`: a deliberate placeholder (`...`, a body that is only a comment, a signature on its own). A notice.
- `fragment`: a partial snippet that was not checked. To check it, put
  `<!-- gdcheck: extends CharacterBody2D -->` (the right base class) on the line before the block.
- `skipped`: the block is marked as a deliberate wrong or Godot 3 example ("Bad", "results in an error", ...),
  or has `<!-- gdcheck: skip -->`.

## 3. Fix the common errors

**Type inferred from a Variant.** `JSON.parse_string`, untyped dictionary lookups and `Array` elements return
`Variant`; `:=` on them is an error with Godot 4's default settings. Give the type explicitly:

```gdscript
extends Node

func load_settings(text: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(text)
	if parsed is Dictionary:
		return parsed
	return {}
```

**Helper never declared.** If an example calls `die()`, `take_damage()` or similar, declare it, even as a stub:

```gdscript
extends CharacterBody2D

var health := 3

func take_hit() -> void:
	health -= 1
	if health <= 0:
		die()

func die() -> void:
	queue_free()
```

**Members of the wrong base class.** `velocity`, `move_and_slide()` and `is_on_floor()` exist only on
`CharacterBody2D`/`CharacterBody3D`; `position` needs a `Node2D` or `Node3D`. Make the `extends` line match.

**A lambda at the very end of a .gd file.** Godot 4 (still in 4.7.2) rejects a file whose last token closes a
lambda when no newline follows it, with "Expected end of file" (godotengine/godot#96228). When you write a .gd
file, end it with a newline. gdcheck adds the newline for Markdown blocks and gives this hint for .gd files.

```gdscript
extends Node

func _ready() -> void:
	var timer := Timer.new()
	add_child(timer)
	timer.timeout.connect(func():
		print("tick")
	)
```

## 4. In CI

Add the GitHub Action so every pull request is checked:

```yaml
- uses: actions/checkout@v4
- uses: munimtechnologies/godot-skill-check@v0.3.0
  with:
    paths: skills docs
```

## Limits

Godot's `--check-only` finds parse and static errors, not runtime bugs. Each block is checked alone in an empty
project, so project settings and autoloads are unknown.
