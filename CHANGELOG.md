# Changelog

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
