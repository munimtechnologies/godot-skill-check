# Results: do the GDScript examples in the Godot class reference that Godot rejects have real bugs?

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude). Text: CC BY 4.0.
Code quoted from the Godot class reference stays under the docs' licence, CC BY 3.0 (Godot community).

Status (2026-11-11): C1 to C4 graded; **C5 (is the same code still on `master`?) is not graded yet**. It
waits for the read-only job `classref-c5-v1`. Its method and code were published before it runs:
[c5/EXPECTATIONS.md](c5/EXPECTATIONS.md), [c5/c5_upstream.py](c5/c5_upstream.py).

- Pre-registration: [PREREGISTRATION-class-reference.md](../../PREREGISTRATION-class-reference.md)
  (commit `899351a`, 2026-11-10 16:19 UTC).
- Labels, written and published before verification: [LABELS.md](LABELS.md), [handcheck.csv](handcheck.csv)
  (commit `933fada`, 2026-11-10 19:02 UTC).
- Verification: [job/verify_classref.py](job/verify_classref.py) 0.1.0, run unchanged once in a sealed
  container on 2026-11-11 01:35 to 01:38 UTC with Godot `4.7.2.stable.official.ed1daf0bf`, on this
  repository at `3ef6cad`. Output: [classref-verify.json](classref-verify.json),
  [verify-stdout.txt](verify-stdout.txt), unit tests 14 of 14 passed ([verify-unittest.txt](verify-unittest.txt)).

Results are kept in three groups: what the checker found automatically, what one reader labelled by hand,
and what Godot confirmed. Exploratory findings are listed apart and were not used for any label or grade.

## 1. Automatic (gdcheck 0.3.0)

The class reference is the `classes/` part of the official Godot 4.7 docs (godot-docs `9adca4c`). gdcheck
0.3.0 marks 23 of its GDScript blocks `error`. 3 of those 23 moved out of `error` in 0.3.0 before the study
started, so the population is **N = 20** (3 complete scripts, 8 declaration fragments, 9 statement
fragments). 5 of the 20 had been glanced at in an earlier run, so every prediction is graded on all 20 and
on the 15 not glanced at. A rebuild of the population in a separate job gave the same 20 blocks with the
same code as the reader labelled (no mismatch).

## 2. Hand labels (one reader, before any verification)

| label | all 20 | the 15 |
|---|---|---|
| real | 12 | 7 |
| intended | 8 | 8 |
| context, tool, unsure | 0 | 0 |

Three judgment calls are reported in [LABELS.md](LABELS.md): three blocks are not GDScript at all and were
labelled `intended` because the label set has no "not code" label; three blocks that declare the same
variable name more than once were labelled `real` under the pre-registered rule; and a comment inside one
block was read as the page calling two functions alternatives.

## 3. Verification with Godot 4.7.2

A `real` label stands only if (a) the block as gdcheck checked it still gives its recorded error and (b) the
correction written before the run passes `--check-only` with no error at all. **All 12 held both.** The two
reported checks also held for all 12: the unchanged block inside the smallest script that supplies the
names its page assumes gives the same error, and the correction applied to gdcheck's own wrapping removes it.

| id | page:line (4.7 docs) | what Godot 4.7.2 says | correction that passes |
|---|---|---|---|
| R01 | class_@gdscript.rst:642 | `@export_multiline` needs a String-like type, got Variant | add `: String` |
| R02 | class_@gdscript.rst:706 | variable `number` declared three times | distinct names (types added too; see X1) |
| R03 | class_@globalscope.rst:6415 | could not find base class `Sprite` (Godot 3 name) | `extends Sprite2D` |
| R04 | class_@globalscope.rst:7737 | variable `a` declared three times | `a`, `b`, `c` |
| R06 | class_displayserver.rst:4499 | `val` instead of `var` (two lines) | `var` |
| R07 | class_dtlsserver.rst:115 | `connect_to_peer(udp, false)`: argument 2 must be a String (hostname); the bool is the Godot 3 signature | `connect_to_peer(udp, "127.0.0.1", TLSOptions.client_unsafe())` |
| R10 | class_linkbutton.rst:294 | invalid escape `\S` in a Windows path | escaped backslashes |
| R13 | class_node.rst:2033 | variable `b` declared twice | `c` and `d` |
| R14 | class_popupmenu.rst:913 | closing `)` of a multi-line lambda at an indentation that matches no level | `)` at the level of the `connect(` line |
| R15 | class_renderingdevice.rst:3263 | no constant `STORAGE_BUFFER_USAGE_SHADER_DEVICE_ADDRESS` | `0, RenderingDevice.BUFFER_CREATION_DEVICE_ADDRESS_BIT` as the creation flag |
| R16 | class_renderingdevice.rst:6854 | `RenderingDevice.new()`: the class is abstract | `RenderingServer.create_local_rendering_device()` |
| R18 | class_spinbox.rst:36 | no constant `LineEdit.HORIZONTAL_ALIGNMENT_RIGHT` | `spin_box.alignment = HORIZONTAL_ALIGNMENT_RIGHT` |

Nine facts from Godot's own ClassDB that the labels rely on came out as written before the run (9 of 9),
for example: `Sprite` does not exist and `Sprite2D` does; `RenderingDevice` cannot be instantiated; `SpinBox`
has a property `alignment` and none called `horizontal_alignment`; argument 2 of
`PacketPeerDTLS.connect_to_peer` is a String.

## 4. Predictions, graded as written

| | prediction | all 20 | the 15 |
|---|---|---|---|
| C1 | 3 to 10 blocks verified real | **not held** (12, above the range) | **held** (7) |
| C2 | at least one complete-script error verified real | **held** (2 of 3: R03, R07) | **held** (R03) |
| C3 | at most 5 labelled `tool` | **held** (0) | **held** (0) |
| C4 | at most 5 labelled `intended` | **not held** (8) | **not held** (8) |
| C5 | at least half of the verified blocks unchanged on `master` | pending (needs 6 of 12) | pending (needs 4 of 7) |

C1 was set from the rates in the earlier manual studies (5 of 17 script errors and 6 of 40 sampled fragment
errors were real). The class reference turned out much higher: 12 of 20 (60%). A likely reason, not tested:
the manual's fragment errors are mostly sketches with parts left out on purpose, while the class reference's
errors are mostly single API facts (an old class name, a missing constant, an old signature) that a
reference page gets wrong when the API changes under it.

## 5. Exploratory (written before the run, not used for any label)

- **X1 not held.** We expected R02's block with distinct names but **no** types to fail on untyped
  `@export_range`. It passes `--check-only` in Godot 4.7.2. So R02's only error is the repeated name, and
  the types in our correction are more than needed (the correction is still valid).
- **X2 held.** Dropping only `LineEdit.` from R18 passes `--check-only`, although `SpinBox` has no
  property `horizontal_alignment`. `var spin_box = SpinBox.new()` declares the variable without a static
  type, so the parser does not check the property name. The SpinBox example has a second bug that a
  parser check cannot see; ClassDB confirms it.
- **X3 held.** R07 with a hostname and default TLS options also passes.
- **Open question about the checker.** R04's check D listed one extra message, `Could not find base class
  "Sprite"`, which is R03's error, not R04's. It changes no verdict (R04's checks A and B show no such
  message, and R04's own error was gone in D). gdcheck 0.3.0 keeps every script it checks in one project
  folder and does not compare the file named in Godot's `at:` line with the file being checked, so a message
  about an earlier script may be counted for a later one. The `classref-c5-v1` job re-runs those checks and
  saves Godot's raw output so the cause can be read, not guessed. If it is a gdcheck bug, the fix and the
  numbers it changes will be published in a gdcheck release.

## Limits

- One reader labelled every block; no second reader. The labels were published before verification so
  they could not be adjusted to the results.
- `--check-only` sees parse and type errors only. A block that passes can still be wrong when it runs
  (X2 shows one such case).
- The population is the class reference's blocks that gdcheck 0.3.0 marks `error`. Blocks Godot accepts
  were not read, so this is not a count of all bugs in the class reference.
- Nothing here has been filed, commented or proposed on any godotengine repository. Godot's 2026
  contribution policy bans autonomous AI agents and AI-written text in its issues and pull requests.
