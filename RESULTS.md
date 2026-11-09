# Results: do the GDScript examples in Godot agent skills pass Godot 4's own check?

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude) working in his name.
Graded on 2026-11-09 against [PREREGISTRATION.md](PREREGISTRATION.md), which was committed before any skill was
read. Text CC BY 4.0; code Apache-2.0.

## In one paragraph

Godot 4.7.2 itself checked 2,239 unique complete GDScript scripts taken from 280 Godot agent skills listed on
skills.sh. **363 (16.2%) failed for a reason inside the script**, not because they use a class defined in another
file. Old Godot 3 code was rare: Godot flagged a Godot 3 construct in only 9 scripts, and a hand check of every
static-scan hit found just **1 of 238 skills with code** that teaches Godot 3 API as if it were current. The
common failures are Godot 4's own rules: a type that cannot be inferred (`:=` on a value without a known type), a
function or variable that the example uses but never declares. **4 of 6 predictions held, including both core
predictions**, but core prediction P2 held only on the coded count; the hand check puts the true rate below the
predicted range (details below).

## What was run

One sealed job (`godot-skill-check-v1`, 2026-11-09 02:21-02:44 UTC, Python 3.12, 0.6 GB peak memory):

1. The job first waited until PREREGISTRATION.md was public on GitHub (it was, on the first try).
2. **Collect**: skills.sh search for `godot` (131 results) and `gdscript` (200, the limit; the search is fuzzy, so
   that list may be cut off) gave 321 unique results from 138 GitHub repositories; 281 skill folders were located in shallow clones; **280 skills** mention Godot or GDScript
   (the population). The pre-registration said that, before writing it, only the first search list was seen
   (132 results from 16 repositories); the larger union is what the fixed rule produced at collection time.
3. **Scan**: 3,646 labelled GDScript blocks plus every `.gd` file; 2,259 unique complete scripts, 20 of them
   multi-file blocks (not checked), **2,239 checked** with the official Godot 4.7.2-stable Linux binary
   (`--headless --check-only`, empty default project). No timeouts.
4. **Report**: `summary.json`, `skills.csv`, `static-hits.jsonl`, `script-results.jsonl`.

## Method gates

| Gate | Result |
|---|---|
| M1 controls: Godot 4 script -> clean; Godot 3 `onready` script -> real-error; undefined `PlayerStatsResource` -> external-only | **passed** (all three as expected) |
| M2 Godot version | **passed**: `4.7.2.stable.official.ed1daf0bf` |
| M3 hand check of every static-scan hit | **done**: 62 hits, see [data/hand-check.csv](data/hand-check.csv) |

## Predictions, graded exactly as written

| # | Prediction | Result | Verdict |
|---|---|---|---|
| P1 | At least 80 skills with code | 238 skills with code | **held** |
| P2 (core) | 2%-20% of skills with code have a static-scan hit | 31 of 238 = 13.0% (coded count) | **held** (see hand check) |
| P3 (core) | 10%-50% of graded unique complete scripts are real-error | 363 of 2,239 = 16.2% | **held** |
| P4 | At least 3 of the 10 most-installed skills with a graded script have a real-error script | 2 of 10 | **failed** |
| P5 | More real-error scripts have an inference error than a godot3 error | 142 inference vs 9 godot3 | **held** |
| P6 | Fewer than 40% of labelled blocks are complete scripts | 1,466 of 3,646 = 40.2% | **failed** (by 0.2 points) |

Script status counts: clean 1,505; real-error 363; external-only 365; elision-only 6; multi-file 20 (not graded).

## Hand check of the static scan (M3, reported separately from P2)

All 62 static-scan hits were read in their source files:

| What the hit really was | Hits | Skills |
|---|---|---|
| A user-defined method or autoload call named `change_scene` (not Godot 3's `SceneTree.change_scene`) | 37 | 28 |
| A deliberate Godot 3 "before" example in a migration guide (`# Before`, `Problem:`, `# 3.x`) that the contrast markers missed | 18 | 2 |
| **True Godot 3 code presented as current** (`tool`, `.instance()`, `Sprite.new()`, `Directory.new()`) | 7 | **1** |

So the hand-checked rate is **1 of 238 skills (0.4%)**, below P2's 2% floor. P2 stays "held" because the
pre-registration grades it on the coded count, but it held for the wrong reason: the `change-scene` pattern was too
broad, and the contrast markers did not include `# Before` (without a colon) or `# 3.x`. A future version should
match only `get_tree().change_scene(` and add those markers.

## Exploratory numbers (not pre-registered; for context only)

- **Errors that might be knock-on effects.** 127 of the 363 real-error scripts also contain an external error
  (a class or file defined elsewhere). When Godot cannot resolve a name, a later `:=` on that value can fail with
  "Cannot infer the type", which the fixed rules count as the script's own error. Example: the one real-error
  script among the top-10 `gamedev-skills` skills fails only because `preload("res://bullet.tscn")` does not exist
  in an empty project. Counting only scripts with no external error at all: **236 of 2,239 (10.5%)** still fail,
  which is still inside P3's range. 92 of the 142 inference scripts co-occur with an external error.
- **What the self-contained failures look like.** 45 real-error scripts fail only because they call a function
  they never define (`Function "die()" not found in base self`), 35 only because of undeclared lower-case names
  (`speed`, `player`, `global_position` in a script whose base class has no position), 19 only because of type
  inference. These are mostly abbreviated examples: fine for a human reader, but an agent that copies them
  verbatim gets a script that does not compile.
- **One collection dominates.** Scripts from one repository (`thedivergentai/game-dev-agentic-skills`, which ships
  1,200+ `.gd` files) make up 1,389 of the 2,239 graded scripts; 196 of them (14.1%) are real-error. All other
  repositories: 167 of 850 (19.6%).
- **Copies spread errors.** The most-installed Godot skill (`wshobson/agents/godot-gdscript-patterns`, 18,211
  installs at collection) has copies in 17 other repositories (19 more skills) that share some of its scripts. One of its scripts,
  a save manager, has `var parsed := JSON.parse_string(json)`; `JSON.parse_string` returns a Variant, and with
  Godot 4's default settings that line is an error ("The variable type is being inferred from a Variant value...
  (Warning treated as error.)"). The fix is `var parsed: Variant = JSON.parse_string(json)`.
- **Skill level.** 138 of the 210 skills with at least one checked script have at least one real-error script
  (a script shared by several skills counts for each).
- **Classifier gap.** 14 error lines use Godot's other wording, `Compile Error: Identifier not found: X`; at least
  one names a PascalCase class (`BigNumber`) that the pre-registered external rule did not cover, so up to 14
  scripts may be over-counted as real-error. P3 holds with or without them.

## Limits

- `--check-only` finds parse and static-analysis errors only, not runtime bugs or wrong behaviour; fragments
  (60% of labelled blocks) were covered only by the static scan.
- An empty default project: real projects may relax warning-as-error settings or define the missing names.
- skills.sh search results and install counts were read once (2026-11-09); skills change. Every link in the data
  is pinned to the commit SHA that was checked.
- One repository supplies most scripts, and many skills are copies of one another, so per-script and per-skill
  shares are not independent samples.

## Files

- [summary.json](summary.json): gates, P1-P6, counts, top error messages.
- [skills.csv](skills.csv): one row per skill (installs, blocks, complete scripts, exclusions, hits, errors).
- [static-hits.jsonl](static-hits.jsonl) and [data/hand-check.csv](data/hand-check.csv): every static hit and its
  hand-check verdict.
- [script-results.jsonl](script-results.jsonl): every checked script by hash, with GitHub links (commit SHA and
  line) to every place it appears and Godot's error messages. Other people's code is linked, not copied.
- [population.json](population.json), [scan-meta.json](scan-meta.json): the collected population and the scan run.

If you maintain one of these skills and think a result is wrong, please open an issue.
