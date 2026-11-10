# Pre-registration: are the class-reference GDScript errors found by gdcheck 0.3 real?

Written 2026-11-10 by AI agents working in the name of MV2 of Munim, Inc. (mv2@munimtech.com),
before anyone labels these blocks. Licence: CC BY 4.0 (text). Code in this repository: Apache-2.0.

## Question

The godot-docs study in this repository ([PREREGISTRATION-godot-docs.md](PREREGISTRATION-godot-docs.md),
[RESULTS-godot-docs.md](RESULTS-godot-docs.md)) checked every GDScript block of the Godot 4.7 docs
(godot-docs at `9adca4c1c72917bfe1b7be3108abed5ce26696a6`) with Godot 4.7.2's own `--check-only`.
The manual stratum was hand-checked. The **class reference** stratum (`classes/`, the pages built from
the engine's `doc/classes/*.xml`) was not. Under gdcheck 0.3.0 it has 20 blocks with status `error`.
How many of them are real mistakes in the docs, and are those mistakes still present upstream today?

## Population (fixed now)

- Start: every record in [`results/godot-docs/errors.jsonl`](results/godot-docs/errors.jsonl) with
  `stratum == "classes"` (gdcheck 0.2.0 run; 23 records).
- Remove every block that [`results/godot-docs/docs-v03.json`](results/godot-docs/docs-v03.json) lists in
  `transitions` with `stratum == "classes"`, `old == "error"` and a `new` status other than `error`
  (3 blocks: `class_callable.rst` line 59 to context, and 2 to elision). gdcheck 0.3.0 added no new
  class-reference errors (expectation X5).
- Result: **N = 20** blocks (3 complete scripts, 8 declaration fragments, 9 statement fragments).
  If the selection above gives a different N, the difference is reported and the selection as written wins.
- Not in the population: the one class-reference block that went from context to timeout under 0.3.0
  (`class_editorcontextmenuplugin.rst` line 239). It is reported separately if re-run.

**Disclosure.** In an earlier run (2026-11-10) five of these blocks were glanced at, without labels being
written down: `class_spinbox.rst:36`, `class_dtlsserver.rst:115`, `class_displayserver.rst:4499`,
`class_linkbutton.rst:294`, `class_@gdscript.rst:642`. Every prediction is reported twice: on all 20
blocks, and on the 15 not glanced at.

## Hand check (the same four labels as the manual study, plus one)

Each block is read next to its rendered page (`docs_url`) and its source (`source_url`, at the pinned sha),
with Godot's messages from `errors.jsonl`. One label per block:

- **real**: the code as shown fails in Godot 4.7.2 for a reason in the code itself.
- **intended**: the page means it to fail or to be incomplete, and our markers missed it.
- **context**: it needs code from elsewhere that our rules did not see.
- **tool**: a gdrst/gdcheck mistake.
- **unsure**: the reader cannot decide between real and another label. Counted as *not real* in every
  prediction and listed separately.

Labelling rules fixed now: a block that declares the same name twice is `real` unless the page's prose
says the lines are alternatives (then `intended`). An API that exists only in Godot 3 is `real`.
A wrong label rule is reported as such, never fixed silently.

## Verification (before any block is called real in public)

Every block labelled `real` gets a sealed sandbox run with Godot 4.7.2 (the `fragverify` method in
`docs-study/fragverify/`): (a) the block as wrapped by gdcheck reproduces the recorded error, and (b) a
minimal correction, written down before the run, passes `--check-only`. A `real` label stands only if
both hold; otherwise it becomes `unverified` and counts as not real.

## Upstream status (exploratory, reading only)

For each verified real block: read `doc/classes/<Class>.xml` in godotengine/godot on `master` on the grading
day and record whether the same code is still there, and search godotengine/godot issues and pull requests
for an existing report. Godot's 2026 contribution policy bans autonomous AI agents and AI-written text in
issues and pull requests, so **nothing is filed, commented or proposed on any godotengine repository**.
Findings are published only in this repository.

## Predictions (graded on the 20 blocks, then on the 15)

- **C1.** Between 3 and 10 of the 20 blocks are verified real (15% to 50%).
  Basis: 5 of 17 manual script errors and 6 of 40 sampled manual fragment errors were real.
- **C2.** At least 1 of the 3 complete-script errors is verified real.
- **C3.** At most 5 of the 20 blocks are labelled `tool`.
- **C4.** At most 5 of the 20 blocks are labelled `intended` (the class reference already marks its wrong
  examples often: 28 class-reference scripts were skipped by marker).
- **C5.** At least half of the verified real blocks still have the same code in godotengine/godot `master`
  on the grading day (not gradable if C1 finds none).

## What will be published

`results/class-reference/handcheck.csv` (file, line, kind, label, one-line reason, correction for real
blocks), the verification job's output, the upstream-status table with links pinned to commits, and a
results section that reports automatic results, hand labels and exploratory findings separately.
Links point at pinned commits; Godot's own text is quoted only as far as needed to show a mistake.

## Limits known now

- One reader labels the blocks; there is no second rater.
- The class-reference pages are generated from the engine's XML, so a mistake may already be fixed on
  `master` but not in the 4.7 docs. C5 measures that; it does not change C1-C4.
- gdcheck wraps fragments in a default script (`extends Node`); a block written for another base class
  can fail only because of the wrapper. Those are labelled `tool` or `context`, not `real`.

## Changes after this pre-registration

None yet. Any change is dated and listed here, with its reason.
