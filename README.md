# godot-skill-check

Do the GDScript examples in Godot agent skills pass Godot 4's own check?

An open, pre-registered study by MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude)
working in his name. Code Apache-2.0; text and data CC BY 4.0.

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
read. Results will be added here whatever they show.

## Run it

Needs Python 3.10+, git and a Godot 4.7.2 Linux binary.

```sh
python -m unittest -v
python skillcheck.py collect --out out --work /tmp/repos
python skillcheck.py scan --out out --work /tmp/repos --godot ./Godot_v4.7.2-stable_linux.x86_64 --proj /tmp/proj
python skillcheck.py report --out out
```

Outputs: `summary.json` (predictions P1-P6 and gates M1-M2), `skills.csv`, `static-hits.jsonl` and
`script-results.jsonl` (each with GitHub links to the exact file and line). Skill code from other repositories is
kept in `out/private/` for checking and is not republished here.

## Limits

`--check-only` finds parse and static-analysis errors, not runtime bugs. Code fragments are only covered by the
static scan. A script that leans on a class defined elsewhere can hide further errors. Contrast markers
("wrong", "Godot 3", ...) are used to leave out deliberate bad examples, which is a heuristic.

If you maintain one of the skills and think a result is wrong, please open an issue.
