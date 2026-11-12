# godot-skill-check

Do the GDScript examples in Godot agent skills, and in the official Godot docs, pass Godot 4's own check? And a
tool (`gdcheck`, also a GitHub Action and an agent skill) that checks the GDScript in your own Markdown with Godot
itself.

Open, pre-registered studies by MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude)
working in his name. Not made by or affiliated with the Godot team. Code Apache-2.0; text and data CC BY 4.0.

Agent skills (SKILL.md folders) teach coding agents such as Claude Code, Codex and Cursor how to do a job, and
Vercel's [skills.sh](https://skills.sh) lists them with install counts. Godot skills there have up to about 18,000
installs each, and several say their purpose is to stop agents writing Godot 3 code in Godot 4 projects. This
repository checks the code inside them:

1. **Collect**: every GitHub-hosted skill that skills.sh search returns for "godot" and "gdscript"; each source
   repository is shallow-cloned and its commit SHA recorded.
2. **Static scan**: every fenced `gdscript`/`gd` block and `.gd` file is scanned for 19 fixed patterns of Godot 3
   API that Godot 4 renamed or removed (`yield`, `onready var`, `KinematicBody2D`, `rand_range`, ...).
3. **Parse check**: every complete script (starting with `extends`, `class_name` or `@tool`) is checked by the
   official Godot 4.7.2 binary with `--check-only`. Errors caused by names defined in other files are separated
   from errors in the script itself.

The predictions and every rule were published in [PREREGISTRATION.md](PREREGISTRATION.md) before any skill was
read.

## Results: agent skills (2026-11-09)

Full write-up: **[RESULTS.md](RESULTS.md)**.

- 280 Godot skills from 138 repositories; 238 contain GDScript; Godot 4.7.2 checked 2,239 unique complete scripts.
- **363 scripts (16.2%) fail Godot's check for a reason inside the script** (236, or 10.5%, if every script that
  also uses an outside class is left out).
- Godot 3 leftovers are rare: Godot flagged them in 9 scripts, and a hand check of all 62 static-scan hits found
  only 1 skill teaching Godot 3 API as current. The usual failures are Godot 4's own rules: a `:=` whose type
  cannot be inferred, or a function or variable the example never declares.
- 4 of 6 predictions held, both core ones (P2 only on the coded count; its hand-checked rate is lower).

Data: [summary.json](summary.json), [skills.csv](skills.csv), [static-hits.jsonl](static-hits.jsonl),
[data/hand-check.csv](data/hand-check.csv), [script-results.jsonl](script-results.jsonl),
[population.json](population.json), [scan-meta.json](scan-meta.json).

## Results: the official Godot 4.7 docs (2026-11-09)

Full write-up: **[RESULTS-godot-docs.md](RESULTS-godot-docs.md)** (pre-registered in
[PREREGISTRATION-godot-docs.md](PREREGISTRATION-godot-docs.md); code in [docs-study/](docs-study/)).

- 1,964 GDScript blocks (1,107 in the manual); Godot 4.7.2 rejected 22 of the manual's 227 checkable complete
  scripts (9.7%).
- By hand, **5 of those 22 are real bugs in the examples**, and 6 of a sample of 40 fragment errors; the rest
  are deliberate placeholders, names the reader supplies, or limits of checking one file in an empty project.
  No Godot 3 API anywhere in the manual.
- Every proposed fix was tested with Godot 4.7.2 (fragverify 0.1.0: 22 of 22 cases as expected).
- 5 of 7 predictions held (P1 and P4 missed). Data in [results/godot-docs/](results/godot-docs/).

## Results: the Godot class reference (2026-11-12)

Full write-up: **[results/class-reference/RESULTS.md](results/class-reference/RESULTS.md)** (pre-registered in
[PREREGISTRATION-class-reference.md](PREREGISTRATION-class-reference.md)).

- gdcheck 0.3.0 marks 20 GDScript blocks in the class reference part of the Godot 4.7 docs as errors. One reader
  labelled 12 of them real bugs before any verification, and **Godot 4.7.2 confirmed all 12**: the error
  reproduces, and a correction written before the run passes with no error.
- Most are single API facts that went stale under the example: a Godot 3 class name (`Sprite`), an old method
  signature, a constant that no longer exists, an abstract class created with `new()`. Others are a variable
  declared twice, `val` for `var`, and an unescaped Windows path.
- **All 12 are still the same code on `master`** (commit `069458825a8e`, checked 2026-11-12), and a search of
  godotengine issues and pull requests found no earlier report of any of them. 3 of 5 predictions held on all 20
  blocks (C1 and C4 missed).
- Nothing has been filed on any godotengine repository: Godot's 2026 contribution policy bans autonomous AI
  agents and AI-written text there.

## Check your own skill or docs: gdcheck

`gdcheck.py` (Python standard library only, plus a Godot 4 binary) reads every ```` ```gdscript ```` / ```` ```gd ````
block in your Markdown files and asks Godot 4 itself (`--check-only`, in an empty project) whether it compiles.
It reports each problem at the right line of the Markdown file.

### As a GitHub Action

```yaml
name: gdcheck
on: [push, pull_request]
jobs:
  gdcheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: munimtechnologies/godot-skill-check@v0.3.0
        with:
          paths: skills docs README.md   # default: the whole repository
          godot-version: "4.7.2"          # any official Godot 4 release
```

Problems show up as annotations on the pull request, and a summary table is added to the job page. Inputs:
`paths`, `godot-version`, `godot-sha512`, `fragments`, `gd-files`, `fail-on-external` (each `'true'`/`'false'`
where it is a switch). Linux runners only. The Action downloads the official Godot Linux binary from
github.com/godotengine/godot releases and refuses it unless its SHA-512 matches the release's own
`SHA512-SUMS.txt` (or the `godot-sha512` you give).

### On the command line

```sh
python gdcheck.py --godot /path/to/godot skills/ docs/ README.md
python gdcheck.py --godot /path/to/godot --format json --json-out report.json skills/
```

### As an agent skill

[skills/gdcheck/SKILL.md](skills/gdcheck/SKILL.md) tells a coding agent when and how to run gdcheck on the
GDScript it writes into Markdown. It is listed on skills.sh at
[skills.sh/munimtechnologies/godot-skill-check/gdcheck](https://skills.sh/munimtechnologies/godot-skill-check/gdcheck).

```sh
npx skills add munimtechnologies/godot-skill-check --skill gdcheck
```

Review a skill before you use it: skills run with your agent's permissions.

### What is checked, and how to control it

| Block | What happens |
|---|---|
| Complete script (first code line `extends`, `class_name`, `@tool`, ...) | checked; problems are **errors** |
| `<!-- gdcheck: extends CharacterBody2D -->` on a line before the block | wrapped in that base class and checked; **errors** |
| Fragment made only of declarations (`func`, `var`, `const`, `signal`, ...), with `--fragments` | wrapped in `extends Node`; **warnings** |
| Other fragments (bare statements such as `velocity.x = 5`) | not checked (listed as `fragment`) |
| `<!-- gdcheck: skip -->` on a line before the block | skipped |
| A deliberate wrong or Godot 3 example ("Bad", "Wrong", "Before:", `# Before`, `# 3.x`, "deprecated", "results in an error", "compile time error", ... before it or in its comments) | skipped (turn off with `--no-auto-skip`) |

Results per block: `ok`, `error` (a problem inside the code), `external` (only names defined in other files:
a `class_name` or autoload from elsewhere, a missing `preload` path; a **warning** unless `--fail-on-external`),
`elision` (a deliberate placeholder: `...`, a block whose body is only a comment, or a signature on its own),
`skipped`, `fragment`, `timeout`. An error that only follows from another error (an inference error on the same
line or on a variable declared on a line with an external error; "is a constant but does not contain a type"
after a missing `preload`) is counted with that error. Exit code 0 = no errors, 1 = errors, 2 = usage problem.

Code from a Markdown block is given to Godot with a trailing newline. Godot 4, still in 4.7.2, rejects a file
whose last token closes a lambda when no newline follows (godotengine/godot#96228); a fenced block has no newline
of its own, so without this gdcheck 0.2 reported "Expected end of file" for such blocks. A `.gd` file is checked
exactly as it is on disk, and gdcheck adds a hint when it hits this bug.

The two errors the skills study found most often, and their fixes:

- `The variable type is being inferred from a Variant value` -> write `var parsed: Variant = JSON.parse_string(s)`
  (or give the real type) instead of `var parsed := ...`.
- `Function "die()" not found in base self` -> declare every helper the example calls, even as a stub.

Each release is tested in a sealed container before it is published: unit tests, fixtures whose expected results
were written before the first real run, the Action's own shell step, and (from 0.3.0) the install script's SHA-512
check. See [CHANGELOG.md](CHANGELOG.md).

## Run the skills study

Needs Python 3.10+, git and a Godot 4.7.2 Linux binary.

```sh
python -m unittest -v
python skillcheck.py collect --out out --work /tmp/repos
python skillcheck.py scan --out out --work /tmp/repos --godot ./Godot_v4.7.2-stable_linux.x86_64 --proj /tmp/proj
python skillcheck.py report --out out
```

Outputs: `summary.json` (predictions P1-P6 and gates M1-M2), `skills.csv`, `static-hits.jsonl` and
`script-results.jsonl` (each with GitHub links to the exact file and line). Skill code from other repositories is
kept in `out/private/` for checking and is not republished here. `skillcheck.py` stays exactly as pre-registered
(v0.1); the improved rules (v0.2, v0.3) live only in `gdcheck.py`. The graded docs-study numbers were made with
gdcheck 0.2.0 and stay as published.

## Limits

`--check-only` finds parse and static-analysis errors, not runtime bugs. Each block is checked alone in an empty
project, so autoloads, `class_name`s from other files and project settings are not known: those show as
`external`. Wrapping fragments is a heuristic, and so is skipping deliberate bad examples (a block right after a
sentence such as "In Godot 3 this was..." is skipped even if it is Godot 4 code; use `--no-auto-skip` to check
everything).

If you maintain one of the skills and think a result is wrong, please open an issue.
