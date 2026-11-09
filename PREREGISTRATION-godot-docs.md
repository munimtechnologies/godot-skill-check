# Pre-registration: do the GDScript examples in the official Godot 4.7 docs pass Godot 4.7.2's own check?

Written 2026-11-09, before any job has read the docs' code blocks. This file is committed on its own; the sandbox
job that runs the study waits until this file is public on GitHub. The results will be published whatever they show,
graded exactly as written here.

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude) working in his name. Not made by
or affiliated with the Godot team. Apache-2.0 for this text and the code; code quoted from the Godot docs stays
under the docs' own licence (CC BY 3.0, godot-docs LICENSE.txt), with a link to its source line.

## Question

The Godot manual (https://docs.godotengine.org) teaches GDScript through thousands of short examples. godot-docs'
CI checks the RST syntax and builds the site, but nothing compiles the GDScript in it (searched 2026-11-09: the
godot-docs workflows and issues, Godot proposals and the web; individual broken examples are reported and fixed by
hand, e.g. godot-docs issue #10440, a threads example that fails with "Too many arguments"). This study runs every
GDScript block in the 4.7 docs through Godot 4.7.2's own `--check-only` and counts what fails and why. As far as
we found, nobody has published such a check of the Godot docs before.

## Population (fixed now)

- godot-docs, branch `4.7`, commit `9adca4c1c72917bfe1b7be3108abed5ce26696a6` (the branch head on 2026-11-09).
  If that commit cannot be fetched, the `4.7` branch head is used and its commit is reported.
- Godot 4.7.2-stable, the official Linux binary (the latest stable release on 2026-11-09).
- Every `.rst` file, except those in folders whose names start with `_` or `.`.
- Two strata, reported separately: **manual** (everything outside `classes/`) and **class reference**
  (`classes/`, generated from the engine's XML). All predictions are about the manual; the class reference
  is reported descriptively.

## Rules (fixed now; the code is `gdrst.py` 0.1.0 + `docs_study.py` 1.0.0 on top of gdcheck 0.2.0)

A **GDScript block** is any of these whose language is GDScript (`gdscript` or `gd`):

1. `.. code-tab:: gdscript ...` (inside `.. tabs::`; C# tabs are not counted);
2. `.. code-block:: <lang>`, `.. code:: <lang>` or `.. sourcecode:: <lang>`; with no language, the language
   in force;
3. a `::` literal block. godot-docs sets `highlight_language = "gdscript"`, so a literal block is GDScript unless
   a `.. highlight::` directive earlier in the file set another language. Bodies of RST comments are ignored.

Each block is then, in this order:

- **skipped** if it has no code (comments only); or if it is marked as a deliberate wrong, error or Godot 3
  example: one of gdcheck 0.2's markers (Bad, Wrong, Godot 3, deprecated, Before:, 3.x, ...) or one of these
  docs markers (syntax error, parse error, will/would/can cause/trigger/produce ... error, not supported,
  unsupported, disallowed, would be errors, won't/doesn't/does not work, is invalid, not valid, `error:`) in the
  three prose lines before it (never reaching back past the previous block) or in its own `#` comments; or if it
  holds several scripts;
- a **complete script** if its first code line is `extends`, `class_name`, `@tool` (gdcheck's rule): checked as
  it is;
- a **declaration fragment** (only `func`, `var`, `const`, `signal`, `enum`, `class` and annotations at the top
  level): wrapped in `extends <base>`;
- a **statement fragment** (top-level statements, no top-level `func`/`class`/`signal`/`enum`/annotation), only
  from code-tab, code-block and `.. highlight:: gdscript` literal blocks: wrapped in
  `extends <base>` + `func __gdcheck_fragment():`. Literal blocks that are GDScript only by default are never
  statement-wrapped, because many hold shell commands or console output;
- otherwise **not checked** (status `fragment`, with the reason).

`<base>` is the class extended by the latest checked complete script earlier on the same page (a plain class name),
otherwise `Node`. If Godot cannot find that base class, the fragment is re-checked with `Node`.

Each checked block gets a **status** from Godot's errors:

- error categories from gdcheck 0.2: `godot3` (Godot 3 API), `external` (a class or file defined elsewhere),
  `elision` (`...` placeholders), `inference`, `other`;
- added for this study: in a fragment, `Identifier "x" not declared`, `Identifier not found: x` and
  `Function "f()" not found in base self` are **context** (a name defined elsewhere on the page); an "Expected
  indented block" / "Expected statement" error in a block with an elided body (`# ...`) is **elision**;
- an inference error on the same line as another error, or on a line using a variable declared on a line with a
  context or external error, is a **cascade** of that root and takes its category;
- status **error** if any root error is `godot3`, `inference` or `other`; else `elision`, `context`, `external`
  in that order; `ok` if Godot reports nothing; `timeout` / `fail-unknown` as in gdcheck. A **checked** block is
  one Godot ran on (any status except skipped and fragment).

## Predictions (graded on the manual stratum)

| # | Prediction | Holds if |
|---|---|---|
| P1 | The manual holds between 1,500 and 4,500 GDScript blocks. | 1,500 <= blocks <= 4,500 |
| P2 | Complete scripts are 5% to 25% of the manual's GDScript blocks. | 5 <= % <= 25 |
| P3 | 2% to 12% of the manual's checked complete scripts get status error. | 2 <= % <= 12 |
| P4 | At least half of the manual's complete-script errors are confirmed real by hand. | confirmed / errors >= 0.5 (not gradable if P3 finds none) |
| P5 | At most 1% of the manual's checked blocks have a Godot 3 API (`godot3`) error. | % <= 1 |
| P6 | Among the manual's checked fragments, context-only blocks outnumber error blocks. | context > error |
| P7 | 3% to 20% of the manual's checked fragments get status error. | 3 <= % <= 20 |

P1-P3 and P5-P7 are graded automatically from the job's `summary.json`. P4 is graded by hand in a later run.

## Hand check (P4, and before any claim about a specific page)

Every manual complete script with status error, and a fixed random sample of up to 40 manual fragment errors
(Python `random.Random(20261109).sample` over the error list sorted by file and line), is read next to its page.
Each is labelled **real** (the code as shown fails in Godot 4.7.2 for a reason in the code itself),
**intended** (the page means it to fail or to be incomplete, and our markers missed it), **context** (it needs
code from elsewhere that our rules did not see) or **tool** (a gdrst/gdcheck mistake). Automatic results, hand
labels and exploratory findings are reported separately. A wrong label rule is reported as such, never fixed
silently.

## What will be published

`RESULTS-godot-docs.md` with the graded predictions and every number above; `summary.json`, `blocks.jsonl` (one
row per block: file, line, source, kind, status, error messages; no code) and `errors.jsonl` (each error block with
its code, Godot's messages and links to the docs page and source line); the study code. If real errors are
confirmed, MV2 will offer a few verified fixes to godot-docs, following its contributing guide and AI policy and
saying the work was made with AI agents.

## Changes after this pre-registration

Only bug fixes to the code that make it do what this file says. Each fix is listed in the results with what it
changed. If the job finds a bug that changes results, the job is re-run and both runs are reported.
gdcheck 0.2.0 is used unchanged; its own sandbox test (fixtures written before any Godot run) runs separately. If
that test shows a gdcheck bug that affects this study, the study is re-run with the fix and both runs are reported.

## Limits known now

`--check-only` checks one script at a time with no autoloads, no scenes and no other project files, so it cannot
see code a page defines elsewhere; that is what the external and context categories are for, and why only complete
scripts are the main measure. Warnings are not reported (only errors). Fragments are checked inside an assumed
class, so their results are less certain than complete scripts'. Markers for deliberate errors are word lists and
will miss some and over-skip others; skipped counts are reported by reason.
