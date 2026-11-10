# Changelog

## v0.3.0 (2026-11-10)

- Markdown blocks are now checked with a trailing newline. Godot 4.7.2 rejects any file whose last token closes
  a lambda when no newline follows (known Godot bug godotengine/godot#96228); gdcheck 0.2.0 wrote blocks without
  one and so reported false "Expected end of file" errors. `.gd` files are still checked exactly as they are, with
  a hint that names the bug when it applies. `GodotRunner(..., keep_eof=True)` keeps the old behaviour.
- "Expected indented block" is now `elision` when a block header has a comment-only body or is a bare signature at
  the end of the code. A header followed directly by code at the same indentation is still an error.
- `"X" is a constant but does not contain a type` after a missing `preload` is now a `cascade` of the external
  error.
- Two more contrast markers: "results in an error" and "compile time error" (both were found unmarked in the
  Godot docs).
- `install_godot.sh` verifies the SHA-512 of the Godot download (from the release's `SHA512-SUMS.txt`, or from
  `GODOT_SHA512` if set) and exits 3 on a mismatch.
- `skills/gdcheck/SKILL.md` clones the tagged release (`--branch v0.3.0`) instead of the moving main branch.
- New fixtures `fixtures/v03.md`, with their expected results in `fixtures/expected.json` (run "v03"), written
  before gdcheck 0.3 first ran against Godot.
- Tested before release in a sealed container (job gdcheck-v03-v1, 2026-11-10, Godot 4.7.2.stable.official.ed1daf0bf):
  59 of 59 unit tests passed; 0 fixture mismatches; the install script exited 3 on a wrong hash and verified the
  real one; the Action step exited 1 on the bad fixtures and 0 on the good ones; gdcheck checked its own
  SKILL.md (3 blocks ok); demo runs on wshobson/agents (9c61ab2) and a 16-skill Godot collection (4cce500)
  finished in under 5 s each.
- The same job ran the godot-docs study once more with gdcheck 0.3.0 (exploratory): all five expectations written
  before the run held. See "gdcheck 0.3 on the docs" in `RESULTS-godot-docs.md` and
  `results/godot-docs/docs-v03.json`.
- `docs-study/test_gdrst.py`: in that job, 25 of 26 docs-study tests passed. The one failure was a test that
  expected gdcheck 0.2's handling of a bare signature at the end of the code. The test now uses a real missing
  indent, and a new test records the 0.3 behaviour. This test-only change was traced by hand before release and
  is re-run against the published tag in job gdcheck-v03-verify-v1. The graded docs-study results were made with
  gdcheck 0.2.0 and are unchanged.
- `skillcheck.py` is unchanged (v0.1, as pre-registered for the skills study).

## v0.2.0 (2026-11-09)

- New: `gdcheck.py`, a checker for the GDScript in Markdown (agent skills, READMEs, docs). It runs every
  complete script, and on request declaration-only fragments, through Godot 4's own `--check-only` and reports
  problems at the Markdown line. Categories: `godot3`, `external`, `cascade`, `elision`, `inference`, `other`.
- New: `action.yml` + `install_godot.sh`, a GitHub Action that downloads the official Godot Linux binary and runs
  gdcheck, with pull-request annotations and a job summary.
- New: `skills/gdcheck/SKILL.md`, an agent skill that tells coding agents how to run gdcheck.
- Tested before release in a sealed container (job gdcheck-action-v1, 2026-11-09): 28 of 28 unit tests passed;
  every fixture block got the status written in `fixtures/expected.json` before the first real run (0
  mismatches); the Action step exited 1 on the bad fixtures and 0 on the good ones; demo runs on the Godot
  skills of wshobson/agents (9c61ab2) and a 16-skill Godot collection (4cce500) finished in under 4 s each.
- New: the godot-docs study (`PREREGISTRATION-godot-docs.md`, `docs-study/`, `RESULTS-godot-docs.md`).
- `skillcheck.py` is unchanged (v0.1, as pre-registered for the skills study).

## First publication (2026-11-09)

- The pre-registered study of GDScript in Godot agent skills (`PREREGISTRATION.md`, `skillcheck.py`,
  `RESULTS.md` and data).
