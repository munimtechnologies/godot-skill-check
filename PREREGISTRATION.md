# Pre-registration: do the GDScript examples in Godot agent skills pass Godot 4's own check?

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude) working in his name.
Written and committed on 2026-11-08, **before any skill's files were read**. The only things seen before writing
were the skills.sh search result list for "godot" (132 results from 16 repositories, names and install counts
only) and the Godot 4 upgrade guide. Text CC BY 4.0; code Apache-2.0.

## Why

Agent skills (SKILL.md folders) teach coding agents such as Claude Code, Codex and Cursor how to do a task.
Vercel's skills.sh lists them with install counts; the most-installed Godot skills there have about 6,000 to
18,000 installs each. Several Godot skill packs say their purpose is to stop agents writing Godot 3 code
(`yield`, `KinematicBody2D`, `onready var`) in Godot 4 projects. Searches on 2026-11-08 found guides, skill
packs and a survey of which packs exist, but no measurement of whether the code inside these skills is itself
valid Godot 4 code. This study measures that, with Godot itself as the judge.

## Population (fixed)

1. Query `https://skills.sh/api/search?q=<q>&limit=200` for q = `godot` and q = `gdscript` (the endpoint the
   `skills find` CLI command uses; no login). Union of results by `id`.
2. Keep GitHub-hosted results (`source` = `owner/repo`). Shallow-clone each repo (`git clone --depth 1`) and
   record its commit SHA.
3. Locate each skill's folder: the folder of a `SKILL.md` whose frontmatter `name` equals the result's
   `skillId`; failing that, a folder whose name equals `skillId` (shortest path wins). Not found = reported, dropped.
4. A skill's files are the `.md` and `.gd` files under its folder, excluding sub-folders that hold their own
   `SKILL.md`. Files over 2 MB are skipped.
5. **Population** = located skills whose name or Markdown text mentions "godot" or "gdscript".
6. **Skills with code** = population skills with at least one fenced code block labelled `gdscript`, `gd`,
   `gdscript2` or `gdscript4` (case-insensitive), or at least one `.gd` file.

## Measures (fixed)

**E1, deliberate wrong examples are excluded.** A block is excluded when any of the 3 non-empty lines before its
opening fence matches the contrast markers (❌, ✗, bad, wrong, incorrect, anti-pattern, Godot 3, GDScript 1,
deprecated, legacy, outdated, old, don't, do not, avoid, never, mistake, pitfall, "before:", common error), or
when a comment inside it matches the strong markers (❌, ✗, bad, wrong, incorrect, anti-pattern, Godot 3,
GDScript 1, deprecated, legacy, outdated, "old way", "before:"). A `.gd` file is excluded when its path matches
the strong markers. In the static scan, a single line whose own comment matches the contrast markers is skipped.

**Static scan (Godot 3 patterns).** On every non-excluded block, with comments removed (and string contents
blanked for all patterns except the string-connect one), a fixed list of 19 regular expressions for Godot 3 API
or syntax that Godot 4 renamed or removed: `yield(`, `onready var`, `export var` / `export(`, bare `tool`,
`setget`, `.instance()`, 17 renamed global functions (`rand_range`, `deg2rad`, `rad2deg`, `stepify`, `range_lerp`,
`linear2db`, `db2linear`, `str2var`, `var2str`, `bytes2var`, `var2bytes`, `dict2inst`, `inst2dict`, `funcref`,
`ColorN`, `polar2cartesian`, `cartesian2polar`), `Pool*Array`, `connect("signal", self, ...)`,
`change_scene(`, `File.new()` / `Directory.new()`, `remote/master/puppet(...sync) func`, `is_network_master(`,
`move_and_slide(` with arguments, `Engine.editor_hint`, moved `OS.` time/window methods, Tween-node API
(`interpolate_property(`, `Tween.new(`), `BUTTON_LEFT/RIGHT/MIDDLE/WHEEL_*`, and 35 renamed classes
(`KinematicBody2D`, `Spatial`, `Sprite`, `Position2D`, `Particles2D`, `VisibilityNotifier2D`, `YSort`, ...).
The exact expressions are `G3_PATTERNS` in `skillcheck.py` v0.1.0, committed with this file.

**Parse check (Godot 4.7.2).** A block is a **complete script** when its first non-blank, non-comment line starts
with `extends`, `class_name`, `@tool`, `tool`, `@icon(`, `@static_unload` or `@abstract`; every `.gd` file is a
complete script. Complete scripts with more than one top-level `extends` or `class_name` line are
**multi-file blocks**: reported, not checked. The rest are de-duplicated by content (SHA-256) and each is
checked once with the official Godot 4.7.2-stable Linux x86_64 binary:
`godot --headless --path <empty project> --check-only --script res://s/<hash>.gd` (60 s timeout; empty
`project.godot` with default settings). If there are more than 3,000 unique scripts, the first 3,000 in hash
order are checked.

Each `SCRIPT ERROR` line is classified:
- **external**: the script uses a name defined elsewhere: `Could not find type/base class "X"`, could not resolve
  class / super class / script / external class member, preload file missing, could not preload, could not load
  the base class, "couldn't be fully loaded", or `Identifier "X" not declared` where X is PascalCase (first
  letter upper case, second lower case or digit, e.g. an autoload). Not counted as an error of the skill.
- **godot3**: the message quotes a Godot 3 identifier from the static list, or its line has a static-scan hit.
  (Checked before "external", so `extends KinematicBody2D` is godot3.)
- **elision**: the message quotes `...` or contains `…` (a documentation "code omitted here" marker).
- **inference**: the message contains "infer".
- **other**: anything else.

A script is **clean** (no error lines, exit code 0), **real-error** (at least one godot3, inference or other
error, or a nonzero exit / "Failed to load" with no error lines, called unclassified-fail), **external-only**,
**elision-only**, or **timeout**. **Graded scripts** = clean + real-error + external-only + elision-only
(timeouts and multi-file blocks are not graded).

## Method gates

- **M1 (controls).** Three scripts built into `skillcheck.py` must classify as expected: a Godot 4
  CharacterBody2D script -> clean; a Godot 3 KinematicBody2D script -> real-error; a script using an undefined
  class `PlayerStatsResource` -> external-only. If any control fails, P3-P5 are **not gradable** (raw numbers
  still published).
- **M2.** `godot --version` must start with 4.7.2, else P3-P5 are not gradable.
- **M3.** Every static-scan hit is hand-checked after the run (true Godot 3 usage, or a false positive such as a
  user-defined name). P2 is graded on the coded count exactly as written; the hand-checked count is reported
  next to it, separately.

## Predictions

| # | Prediction | Core |
|---|---|---|
| P1 | At least 80 skills with code. | |
| P2 | Between 2% and 20% (inclusive) of skills with code have at least one static-scan hit. | core |
| P3 | Between 10% and 50% (inclusive) of graded unique complete scripts are real-error. | core |
| P4 | Of the 10 most-installed skills (skills.sh installs at collection) that have at least one graded script, at least 3 have at least one real-error script. (Fewer than 10 such skills = not gradable.) | |
| P5 | More real-error scripts have an inference error than a godot3 error. | |
| P6 | Fewer than 40% of labelled GDScript code blocks are complete scripts. | |

## Limits stated in advance

- Fragments (most code blocks) are not run through Godot; only the static scan covers them.
- `--check-only` finds parse and static-analysis errors only, not runtime errors or wrong behaviour.
- Errors behind an unresolved external name can be masked (Godot stops analysing), so real-error is a lower bound.
- Default warning settings apply (some warnings, such as inferring a type from a Variant, are errors by default).
- skills.sh search results and install counts are read once, at collection time; skills change.
- The contrast-marker exclusion is a heuristic; its count is reported.

## Publication

The job waits until this file is public on GitHub before it reads anything. Results (summary.json, skills.csv,
static-hits.jsonl, script-results.jsonl with GitHub links to each block, and the hand check) will be published in
this repository whatever they show. Other people's skill code is linked by commit SHA and line, not copied here.
