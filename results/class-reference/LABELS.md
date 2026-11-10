# Class-reference hand check: labels (written before verification)

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude). Text: CC BY 4.0.
Code quoted from the Godot class reference stays under the docs' licence, CC BY 3.0 (Godot community).

This file goes with [PREREGISTRATION-class-reference.md](../../PREREGISTRATION-class-reference.md)
(commit `899351a`, 2026-11-10 16:19 UTC). The labels in [handcheck.csv](handcheck.csv) were written on
2026-11-10 (about 19:00 UTC) by one reader, before any sandbox run of the corrections. They are
published **before** the verification job runs, and that job refuses to start unless this exact file is
in the repository.

## Population

All 23 class-reference records in `results/godot-docs/errors.jsonl`, minus the 3 that gdcheck 0.3.0
moved out of `error` (`class_callable.rst:59`, `class_control.rst:502`, `class_fileaccess.rst:521`):
**N = 20** (3 complete scripts, 8 declaration fragments, 9 statement fragments), as pre-registered.
Each block was read together with its page text in the class reference (godot-docs 4.7 at `9adca4c`),
and API facts were checked against `doc/classes/*.xml` at `4.7-stable`.

## Labels

| label | all 20 | the 15 not glanced at earlier |
|---|---|---|
| real (before verification) | 12 | 7 |
| intended | 8 | 8 |
| context | 0 | 0 |
| tool | 0 | 0 |
| unsure | 0 | 0 |

All five blocks glanced at in the earlier run are labelled `real`.

The 12 `real` labels are not results yet. Each one stands only if the sealed job shows that (a) the block
as gdcheck checked it still gives the recorded error in Godot 4.7.2 and (b) the correction written in
`handcheck.csv` (and in the job's script, before its first run) passes `--check-only`. Until then
they are hypotheses. The script is published with this file, as filed and **not yet run**:
[job/verify_classref.py](job/verify_classref.py) (corrections, expectations and the ClassDB probe) and
[job/test_verify_classref.py](job/test_verify_classref.py).

## Judgment calls and rule problems (reported, not fixed)

1. **No label for "not code".** Three blocks are not GDScript at all: two lists of dictionary keys with
   their types (`class_navigationmeshsourcegeometrydata2d.rst:262`, `...3d.rst:268`) and a list of
   `goto_help()` descriptor strings (`class_scripteditor.rst:218`), each shown in a GDScript code block.
   The pre-registered labels have no place for them, so they are labelled `intended` (the page never
   means them to run). Without these three, `intended` would be 5.
2. **Duplicate names in a syntax list.** `class_@gdscript.rst:706` lists `@export_range` variants and
   declares `var number` three times. The pre-registered rule makes a repeated name `real` unless the
   prose says the lines are alternatives, and it does not, so the label is `real`. A reader could
   reasonably call it a list of alternatives. The same rule decides `class_@globalscope.rst:7737`
   (`var a` three times) and `class_node.rst:2033` (`var b` twice, where the comments show the names
   were meant to differ).
3. **Comment vs prose.** `class_array.rst:809` defines `func _ready()` twice, and a comment inside the
   block introduces the second as "Another example". The rule speaks of prose; this label reads the
   comment as the page saying the two are alternatives (`intended`). Read strictly, it would be `real`.

## Predictions that the labels alone decide (graded now)

- **C3** (at most 5 of 20 labelled `tool`): **held**. 0 of 20 (0 of 15).
- **C4** (at most 5 of 20 labelled `intended`): **not held**. 8 of 20 (8 of 15). The basis for C4, that
  the class reference marks its wrong examples, did not carry over to placeholders (`...`, `# Parsing
  logic.`) and non-code blocks. Under judgment call 1, it would be 5 and held; it is graded as written.

C1, C2 and C5 need the verification job and are graded when it finishes. If all 12 `real` labels
verify, C1 (3 to 10 verified real) is not held on the 20 (12) and held on the 15 (7), and C2 (at least
one complete script real) is held.

## What the job also reports (not used for any label)

- `X1`: the `@export_range` block with distinct names but no types (expected to fail on untyped
  `@export_range`).
- `X2`: the SpinBox block with only `LineEdit.` removed (expected to pass, so `--check-only` misses the
  wrong property name `horizontal_alignment`; the property is `alignment`).
- `X3`: the DTLS client with a hostname and default TLS options (expected to pass).
- Nine ClassDB facts the labels rely on (for example: `Sprite` does not exist, `RenderingDevice`
  cannot be instantiated, `SpinBox` has `alignment` and no `horizontal_alignment`).

Nothing here is filed, commented or proposed on any godotengine repository (Godot's 2026 contribution
policy bans autonomous AI agents and AI-written text in issues and pull requests).
