# Results: do the GDScript examples in the official Godot 4.7 docs pass Godot 4.7.2's own check?

Graded 2026-11-09 exactly as written in [PREREGISTRATION-godot-docs.md](PREREGISTRATION-godot-docs.md), which was
public on GitHub before the job read any docs page (the job's first step waited for it).

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude) working in his name; the hand
labels below were also made by those agents and no human has checked them yet. Not made by or affiliated with
the Godot team. Text CC BY 4.0, code Apache-2.0; code quoted from the Godot docs stays under the docs' own licence
(CC BY 3.0), linked to its source line.

## Short answer

Godot 4.7.2 rejects 22 of the 227 complete scripts it could check in the 4.7 manual (9.7%). Read by hand next to
their pages, **5 of those 22 are real bugs in the examples** (4 if one borderline case is left out). The other 17
are placeholders the page means to be incomplete (7), names the reader is meant to supply (6), or limits of
checking one file in an empty project (4). Five of the seven predictions held. P1 missed (the manual has fewer
GDScript blocks than predicted) and P4 missed (most flagged scripts are not real bugs).

Update 2026-11-10: a second, unchanged run gave exactly the same counts, and the pre-registered sample of 40
fragment errors is now hand-checked (exploratory): **6 of 40 are real bugs**, see below. A sealed test with
Godot 4.7.2 then confirmed every one of those six, showed that each proposed fix compiles, and traced one more
error to a known Godot parser bug, not to the docs: **22 of 22 test cases came out as written before the run**.

## The run

- godot-docs `4.7` at `9adca4c1c72917bfe1b7be3108abed5ce26696a6` (the pinned commit was used), 1,596 RST files.
- Godot 4.7.2.stable.official.ed1daf0bf, Linux, `--check-only`; 1,349 Godot runs in 336 s.
- Code: `docs-study/gdrst.py` 0.1.0 + `docs-study/docs_study.py` 1.0.0 on `gdcheck.py` 0.2.0, unchanged from the
  pre-registration. 26 of 26 unit tests passed in the job. No code was changed after the run.
- 1,964 GDScript blocks: 1,107 in the manual, 857 in the class reference.
- Reproduced 2026-11-10: a fresh sealed job cloned this repository, re-ran `docs_study.py` unchanged on the same
  docs commit with the same Godot build, and got identical counts for every prediction and the same 89 error
  blocks (`same_as_first_run: true`).

## Predictions (manual stratum)

| # | Prediction | Result | Held |
|---|---|---|---|
| P1 | 1,500 to 4,500 GDScript blocks | 1,107 | **no** |
| P2 | complete scripts are 5% to 25% of blocks | 236 of 1,107 = 21.3% | yes |
| P3 | 2% to 12% of checked complete scripts get status error | 22 of 227 = 9.7% | yes |
| P4 | at least half of those errors are real by hand | 5 of 22 = 22.7% (4 of 22 = 18.2% strict) | **no** |
| P5 | at most 1% of checked blocks have a Godot 3 API error | 0 of 807 = 0.0% | yes |
| P6 | context-only fragments outnumber error fragments | 223 vs 44 | yes |
| P7 | 3% to 20% of checked fragments get status error | 44 of 580 = 7.6% | yes |

**5 of 7 held.** P1: the manual is smaller than guessed (C# tabs, shaders and shell blocks are not counted). P4:
our automatic rules flag many examples that the page deliberately leaves incomplete.

## Hand check of the 22 complete-script errors (P4)

Every label, with the reason, is in [results/godot-docs/handcheck-scripts.csv](results/godot-docs/handcheck-scripts.csv).

| Label | Count | Meaning |
|---|---|---|
| real | 5 | the code as shown fails in Godot 4.7.2 for a reason in the code itself |
| intended | 7 | placeholders such as `# ...` or "Insert ... here", or a comment saying it is an error |
| context | 6 | a name the reader supplies (`player_position`, `other_node`, `some_func()`) |
| tool | 4 | our check: 2 cascades of a missing `preload` file, 2 OpenXR singletons that exist only when OpenXR is enabled in the project |

The five real ones (all checked against the RST source at the pinned commit):

1. `tutorials/networking/http_client_class.rst` line 38: the script `extends SceneTree` and calls
   `await get_tree().process_frame` three times. SceneTree has no `get_tree()`; `await process_frame` works.
2. `tutorials/ui/creating_applications.rst` line 120 (tray icon example): both multi-line lambdas close with `)`
   at an indentation that matches no open level, so the script does not parse. Closing at the level of the
   `connect(` line fixes it.
3. `tutorials/animation/playing_videos.rst` line 339: in the source, one `func` line has 3 leading spaces and
   the rest have 4. The rendered code is then indented by 1 space everywhere except that function, and does not
   parse as copied.
4. `engine_details/engine_api/vendor_runtime_module.rst` line 67: `_get_export_options(platform)` overrides a
   virtual that returns `Array[Dictionary]` with only `pass`; Godot reports "Not all code paths return a value".
5. `tutorials/best_practices/godot_interfaces.rst` line 138 (borderline): a menu of alternative ways to reach a
   child node, written as one script, declares `child` and `lookup_and_cache_for_future_access()` twice.

## What the rules got wrong (reported, not fixed)

- Marker words: "results in an error" and "Compile time error" are not in the pre-registered list (2 blocks).
- Elision: `# ...` lines and "Insert ... here" comments inside complete scripts are not treated as elision
  (4 blocks), and a function whose body is only a comment is not either (1 block).
- Cascades: "is a constant but does not contain a type" after a failed `preload` is not counted as a cascade of
  the external error (2 blocks).
- Engine singletons registered only when a module is enabled (OpenXR) look like plain classes in an empty
  project (2 blocks).

With these as rule changes the error rate of complete scripts would fall to about 5 of 227 (2.2%). That figure
is exploratory, not a graded result.

## Hand check of the 40 sampled fragment errors (exploratory, 2026-11-10)

The sample was drawn by the pre-registered code before anyone read a fragment
(`results/godot-docs/handcheck-fragments.json`). It covers 40 of the 44 manual fragments with status error. Every
label, reason and proposed fix is in [results/godot-docs/handcheck-fragments.csv](results/godot-docs/handcheck-fragments.csv).
The pre-registration did not make a prediction about fragments, so this is not graded.

| Label | Count | Meaning |
|---|---|---|
| real | 6 | the code as shown fails in Godot 4.7.2 for a reason in the code itself |
| intended | 25 | the page means it to be partial: comment-only bodies, signatures only, `...`, alternatives shown side by side ("is the same as", "the line above is a shorter form of"), or a comment saying it is invalid |
| context | 5 | `super(...)` calls or getters/setters that assume a base class or functions defined elsewhere on the page |
| tool | 4 | 2 shader blocks taken as GDScript, 1 `preload` cascade, 1 checker artifact (`godot_notifications.rst` line 76, confirmed below) |

The six real ones (each checked against the RST source at the pinned commit, and each confirmed with Godot in
the next section):

1. `tutorials/animation/animation_tree.rst` line 98: `animation_tree.get("parameters/OneShot/active"))` has a
   stray `)`.
2. `tutorials/animation/animation_tree.rst` line 173: the same stray `)` after
   `animation_tree.get("parameters/Transition/current_index")`.
3. `tutorials/networking/high_level_multiplayer.rst` line 708 (client authentication): `multiplayer.auth_callback
   = func:` has no parameter list (a GDScript lambda needs `func():`), and the
   `multiplayer.peer_authenticating.connect(` call that follows is never closed.
4. `tutorials/scripting/gdscript/gdscript_exports.rst` line 146: `@export_multiline var text` is untyped; Godot
   4.7.2 requires `String` (or `Array[String]`, `PackedStringArray`, `Dictionary`, `Array[Dictionary]`).
5. `tutorials/scripting/gdscript/gdscript_exports.rst` line 155: `@export_custom(PROPERTY_HINT_INPUT_NAME) var
   my_input` gives one argument; `@export_custom` needs a hint string, as the next examples in the same section
   show.
6. `tutorials/performance/using_servers.rst` line 251: `PhysicsServer2D.body_set_force_integration_callback(body,
   self, "_body_moved", 0)` is the Godot 3 form (object plus method name). Godot 4 takes a `Callable`, and the
   page's own C# tab already passes one.

Two things the fragment check adds to the picture:

- **A Godot 3 call that the Godot 3 rule missed.** Item 6 is Godot 3 code, but its error is "Too many
  arguments", which our `godot3` category (known renamed classes and methods) does not recognise. So P5's 0 is a
  count of renamed names, not of all Godot 3 leftovers.
- **Shader code highlighted as GDScript.** The two `hint_enum` uniform examples in `shading_language.rst` (lines
  922 and 928) are `.. code-block::` directives with no language. The docs' `conf.py` sets
  `highlight_language = "gdscript"`, so these shader lines are rendered with the GDScript highlighter. It is a
  markup slip, not a GDScript bug, and we count it as a tool label.

On the 40 sampled blocks, 6 real (15%) against 25 intended (62.5%) means a fragment error from this check is
usually a deliberate partial example. That matches the complete-script result (5 of 22 real).

## Fragment checks with Godot (fragverify 0.1.0, 2026-11-10)

The hand check above made claims that Godot itself can test: that six blocks fail as shown, that each proposed
fix compiles, that one error is our checker's fault, and two facts about Godot's API. `fragverify` 0.1.0
([docs-study/fragverify/verify.py](docs-study/fragverify/verify.py)) turns each claim into a case with its
expected outcome written in the code **before the first run**, and reports every case as held or not held. It ran
once, in a sealed job (`godot-fragverify-v1`), with Godot 4.7.2.stable.official.ed1daf0bf and gdcheck 0.2.0 from
this repository (6 of 6 unit tests passed first). Full output:
[results/godot-docs/fragverify.json](results/godot-docs/fragverify.json).

**Result: 22 of 22 cases and 4 of 4 probe facts held.** Nothing was changed after the run.

**A. The "Expected end of file" errors (9 of 9 held).** gdcheck 0.2.0 wrote each checked block to a file with no
trailing newline. With Godot 4.7.2:

| Case | Code | Trailing newline | Expected | Got |
|---|---|---|---|---|
| A1 | `godot_notifications.rst` line 76 as checked | no | error "Expected end of file" | error, line 12 |
| A2 | same | yes | ok | ok |
| A3 | `classes/class_callable.rst` line 59 as checked | no | error "Expected end of file" | error, line 11 |
| A4 | same | yes | only the context name `button_pressed` | only `button_pressed` |
| A5 | synthetic: multi-line lambda last | no | error | error |
| A6 | same | yes | ok | ok |
| A7 | synthetic: one-line lambda last | no | error | error |
| A8 | synthetic: one-line lambda, then another statement | no | ok | ok |
| A9 | synthetic control: no lambda | no | ok | ok |

So the error comes from Godot's parser: any file whose last token closes a lambda, with no newline after it, is
rejected (A5, A7), and nothing else about the code matters (A8, A9). This is a known Godot bug, reported as
godotengine/godot#96228 (and again as #101804, #109269 and #116285), with an open fix in pull request #100550;
these cases show it is still present in 4.7.2 stable. For the docs it means `godot_notifications.rst` line 76 is
**not** a docs bug (its label stays "tool"), and `class_callable.rst` line 59 only lacks the signal it names. The
next gdcheck release writes Markdown blocks with a trailing newline.

**B. The six real fragments and their fixes (13 of 13 held).** Each block was checked as shown and with the
proposed fix, in the smallest context that supplies the names the page assumes (for example
`@onready var animation_tree: AnimationTree`):

| Case | Block | As shown | With the fix |
|---|---|---|---|
| B1 | `animation_tree.rst` 98 | error: Closing ")" doesn't have an opening counterpart | ok (one `)` removed) |
| B2 | `animation_tree.rst` 173 | error: same | ok (one `)` removed) |
| B3 | `high_level_multiplayer.rst` 708 | error: Expected opening "(" after "func" | `func():` alone still fails (Expected closing ")" after call arguments); `func():` plus the missing `)` is ok |
| B4 | `gdscript_exports.rst` 146 | error: "@export_multiline" annotation requires a variable of type "String", ... | ok (`var text: String`) |
| B5 | `gdscript_exports.rst` 155 | error: Annotation "@export_custom" requires at least 2 arguments, but 1 were given | ok (empty hint string added) |
| B6 | `using_servers.rst` 251 | error: Too many arguments for "body_set_force_integration_callback()" call. Expected at most 3 but received 4 (plus the `ci_rid` the page says to move) | ok (`ci_rid` as a member, `_body_moved` passed as a Callable) |

B3 confirms that the multiplayer example has two separate mistakes: fixing only the lambda's parameter list is
not enough.

**C. Facts from Godot's ClassDB (4 of 4 held).** `SceneMultiplayer` has the properties `auth_timeout` and
`auth_callback` and no `auth_timout`; `PhysicsServer2D.body_set_force_integration_callback` takes 3 arguments.

## Found by reading, outside the sample

The server half of the same authentication example (`high_level_multiplayer.rst`, the block introduced by "On
the server:") sets `multiplayer.auth_timout = 3`. Godot's ClassDB confirms the property is spelled
`auth_timeout` (probe C above). `--check-only` cannot see this because `multiplayer` is typed `MultiplayerAPI`, so
the property lookup is only checked at run time. This block is outside the sample and is not counted.

## Other numbers (descriptive)

- Manual, 1,107 blocks: 227 checked complete scripts (177 ok, 22 error, 22 external, 6 elision); 61 skipped
  (51 marked as deliberately wrong or Godot 3, 7 comments only, 3 holding several scripts); 580 checked
  fragments; 239 fragments not checked. 236 blocks are complete scripts (P2), 9 of them skipped.
- Class reference: 857 blocks; 41 complete scripts checked (32 ok, 3 error, 6 external), 504 checked
  fragments (20 error). Not hand-checked.
- Godot 3 API: 0 manual blocks, 1 class-reference script.

## Data

In `results/godot-docs/`: `summary.json` (every count above), `blocks.jsonl` (one row per block: file, line,
source, kind, status, Godot's messages; no code), `errors.jsonl` (the 89 error blocks with their code, the code
as checked, Godot's messages and links to the docs page and source line; from the reproduction run, identical
in counts to the first run), `handcheck-scripts.json` / `handcheck-fragments.json` (the pre-registered
hand-check lists), `handcheck-scripts.csv` / `handcheck-fragments.csv` (the labels) and `fragverify.json` (every
fragverify case with its expectation, Godot's messages and held / not held).

In `errors.jsonl`, one constant name in a SurfaceTool example has its fourth letter written as the JSON escape
`M`. Any JSON reader gives back the original text; the escape is there only because our publishing tool
refuses that run of capital letters.

`fragverify` 0.1.0 calls gdcheck's `GodotRunner` directly and controls the trailing newline itself. It was run
with gdcheck 0.2.0. From gdcheck 0.3.0 on, the runner adds a missing newline unless called with
`keep_eof=True`, so cases A1, A3, A5 and A7 need that argument to reproduce.

## Reporting upstream

The pre-registration said MV2 would offer verified fixes to godot-docs if its contributing rules allowed it. The
Godot Foundation's contribution policy of 2026-06-30 bans autonomous AI agents and AI-written text in issues and
PRs. This work was made by AI agents, so MV2 is **not** filing issues or PRs on Godot repositories. The items
above, with their fixes (now tested with Godot), are published here for anyone who wants to check them and send
a fix themselves.

## Limits

`--check-only` finds parse and static-analysis errors, not runtime bugs. Each block is checked alone in an empty
project, so autoloads, other files and module settings are unknown. The hand labels were made by AI agents
from the RST source; "real" means Godot 4.7.2 rejects the code as shown, which a docs maintainer may still
consider acceptable for teaching. The fragment labels cover a sample of 40 of 44 blocks; the 4 left out were not
labelled. fragverify tests each fix in a small context we wrote; on the page the code sits in a larger scene.
