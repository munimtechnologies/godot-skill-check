# docs-study: the godot-docs sample check

Do the GDScript examples in the official Godot 4.7 docs pass Godot 4.7.2's own `--check-only`? The question,
rules and predictions are fixed in `../PREREGISTRATION-godot-docs.md`, which was committed before any job read
the docs. This folder holds the study code as it was when that file was written.

- `gdrst.py` (0.1.0): finds GDScript blocks in reStructuredText (code-tab, code-block and `::` literal blocks,
  with Sphinx's `highlight_language` and `.. highlight::`), skips blocks marked as deliberate errors, wraps
  fragments in the class the page's latest complete script extends, and adds the study's categories
  (context, elided bodies, cascades) on top of gdcheck 0.2.
- `docs_study.py` (1.0.0): runs every block through Godot, writes `summary.json`, `blocks.jsonl`,
  `errors.jsonl` and the hand-check lists, and grades the automatic predictions.
- `test_gdrst.py`, `test_docs_study.py`: unit tests (Godot's messages replayed from real 4.7.2 output). They import
  `gdcheck.py` 0.2.0 from the repository root (it is added to the repository once its own sandbox test passes);
  run them with that file next to these.

Apache-2.0. By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude) working in his
name. Not made by or affiliated with the Godot team.
