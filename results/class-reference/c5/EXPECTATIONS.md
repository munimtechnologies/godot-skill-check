# classref-c5: how C5 is measured (written 2026-11-11 ~03:40 UTC, before the job's first run)

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude). Text: CC BY 4.0.

C5 of PREREGISTRATION-class-reference.md (commit 899351a): "At least half of the verified-real blocks
still show identical code in godotengine/godot master on the grading day." The verification job
(classref-verify 0.1.0, 2026-11-11 01:35 UTC) verified all 12 `real` labels, so C5 needs at least 6
of 12 (and, on the 15 blocks not glanced at earlier, at least 4 of 7).

## Method (fixed before the first run)

1. Resolve `master` and the `4.7` branch of godotengine/godot to commit SHAs (GitHub API) and fetch
   each class's XML (`doc/classes/<Class>.xml`, `modules/gdscript/doc_classes/@GDScript.xml`) at those
   SHAs from raw.githubusercontent.com.
2. Take every `[codeblock ...]` and `[gdscript]` section, unescape XML entities and `[lb]`/`[rb]`.
3. Normalise both the XML block and the block gdcheck read from the 4.7 docs (`block_code` in
   `results/godot-docs/errors.jsonl`): strip trailing spaces, turn each leading tab into 4 spaces, remove
   the common indentation, drop blank lines at the start and end.
4. **Same code** = the docs block's normalised lines appear as one contiguous run in one XML block
   (indentation kept, so the PopupMenu indentation error still counts).
5. **Control:** the same test on the `4.7` branch, from which the 4.7 docs were built. Expected: 12 of
   12 match. A case that fails the control is graded by reading the dumped best-matching XML block by
   eye, and that is reported.
6. Also reported for every case, not used for the grade: whether the block matches once leading
   whitespace and blank lines are ignored, whether our correction (from verify_classref.py) appears in
   master, and the best similarity ratio.
7. Read-only prior-report search: one GitHub search query per case over issues and PRs in
   godotengine/godot and godotengine/godot-docs. Hits are candidates, read by hand afterwards. Nothing is
   filed, commented or proposed on any godotengine repository.

## Expectations (my guesses, not pre-registered predictions)

- E1: unit tests pass.
- E2: control matches 12 of 12.
- E3: master still shows 10 to 12 of the 12 blocks unchanged (the class reference changes slowly and
  none of these errors is something a parser-based CI check in the Godot repo would catch).
- E4: the search finds no earlier report for at least 8 of the 12.
