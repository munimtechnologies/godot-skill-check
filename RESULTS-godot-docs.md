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

## The run

- godot-docs `4.7` at `9adca4c1c72917bfe1b7be3108abed5ce26696a6` (the pinned commit was used), 1,596 RST files.
- Godot 4.7.2.stable.official.ed1daf0bf, Linux, `--check-only`; 1,349 Godot runs in 336 s.
- Code: `docs-study/gdrst.py` 0.1.0 + `docs-study/docs_study.py` 1.0.0 on `gdcheck.py` 0.2.0, unchanged from the
  pre-registration. 26 of 26 unit tests passed in the job. No code was changed after the run.
- 1,964 GDScript blocks: 1,107 in the manual, 857 in the class reference.

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

## Other numbers (descriptive)

- Manual, 1,107 blocks: 227 checked complete scripts (177 ok, 22 error, 22 external, 6 elision); 61 skipped
  (51 marked as deliberately wrong or Godot 3, 7 comments only, 3 holding several scripts); 580 checked
  fragments; 239 fragments not checked. 236 blocks are complete scripts (P2), 9 of them skipped.
- Class reference: 857 blocks; 41 complete scripts checked (32 ok, 3 error, 6 external), 504 checked
  fragments (20 error).
- Godot 3 API: 0 manual blocks, 1 class-reference script.
- Fragment errors (44 in the manual) are listed in `blocks.jsonl`; the pre-registered sample of 40 for hand
  checking is in `results/godot-docs/handcheck-fragments.json` and has **not** been hand-checked yet.

## Data

In `results/godot-docs/`: `summary.json` (every count above), `blocks.jsonl` (one row per block: file, line,
source, kind, status, Godot's messages; no code), `handcheck-scripts.json` / `handcheck-fragments.json` (the
pre-registered hand-check lists) and `handcheck-scripts.csv` (the labels). `errors.jsonl` (each error block with
its code and links) will be added in a later commit.

## Reporting upstream

The pre-registration said MV2 would offer verified fixes to godot-docs if its contributing rules allowed it. The
Godot Foundation's contribution policy of 2026-06-30 bans autonomous AI agents and AI-written text in issues and
PRs. This work was made by AI agents, so MV2 is **not** filing issues or PRs on Godot repositories. The five
items above, with their fixes, are published here for anyone who wants to check them and send a fix themselves.

## Limits

`--check-only` finds parse and static-analysis errors, not runtime bugs. Each block is checked alone in an empty
project, so autoloads, other files and module settings are unknown. The hand labels were made by AI agents
from the RST source; "real" means Godot 4.7.2 rejects the code as shown, which a docs maintainer may still
consider acceptable for teaching.
