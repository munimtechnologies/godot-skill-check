# Tests for gdcheck (no Godot needed: Godot's output is replayed from real 4.7.2 runs).
# By MV2 of Munim, Inc. Made with AI agents (Anthropic Claude).
# SPDX-License-Identifier: Apache-2.0
import os
import tempfile
import textwrap
import unittest
from pathlib import Path

import gdcheck as g

HEAD = "Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengine.org\n\n\n"


def godot_out(*errs, kind="Parse error"):
    s = HEAD
    for msg, line in errs:
        s += f"SCRIPT ERROR: {msg}\n          at: GDScript::reload (res://s/x.gd:{line})\n"
    if errs:
        s += f'ERROR: Failed to load script "res://s/x.gd" with error "{kind}".\n'
        s += "   at: load (modules/gdscript/gdscript_resource_format.cpp:46)\n"
    return s


OUT_G3 = godot_out(('Parse Error: The "onready" keyword was removed in Godot 4. Use the "@onready" '
                    'annotation instead.', 3))
OUT_EXTERNAL = godot_out(('Parse Error: Could not find type "PlayerStatsResource" in the current scope.', 3),
                         ('Parse Error: Identifier "PlayerStatsResource" not declared in the current scope.', 6))
OUT_BIGNUMBER = godot_out(("Compile Error: Identifier not found: BigNumber", 35), kind="Compilation failed")
OUT_LOWER = godot_out(("Compile Error: Identifier not found: global_transform", 36), kind="Compilation failed")
OUT_VARIANT = godot_out(("Parse Error: The variable type is being inferred from a Variant value, so it will "
                         "be typed as Variant. (Warning treated as error.)", 22))
OUT_SAMELINE = godot_out(('Parse Error: Function "get_world_3d()" not found in base self.', 7),
                         ('Parse Error: Cannot infer the type of "space" variable because the value doesn\'t '
                          'have a set type.', 7))


def md(text):
    d = tempfile.mkdtemp()
    p = Path(d) / "skill.md"
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return p


class TestMarkdown(unittest.TestCase):
    def test_extract_backtick_and_tilde(self):
        text = "# T\n\n```gdscript\nextends Node\n```\n\nx\n\n~~~gd\nfunc f():\n\tpass\n~~~\n"
        b = g.extract_blocks(text)
        self.assertEqual([x["lang"] for x in b], ["gdscript", "gd"])
        self.assertEqual([x["fence_line"] for x in b], [3, 9])
        self.assertTrue(all(x["closed"] for x in b))

    def test_indented_fence_is_dedented(self):
        b = g.extract_blocks("1. step\n\n   ```gdscript\n   extends Node\n   ```\n")
        self.assertEqual(b[0]["code"], "extends Node")
        self.assertTrue(g.is_complete(b[0]["code"]))

    def test_marks(self):
        b = g.extract_blocks("<!-- gdcheck: skip -->\n```gdscript\nx\n```\n\n"
                             "<!--gdcheck:extends CharacterBody2D-->\n```gd\nfunc f():\n\tpass\n```\n")
        self.assertEqual(b[0]["mark"], "skip")
        self.assertEqual(b[1]["mark"], "extends CharacterBody2D")

    def test_complete_and_fragment(self):
        self.assertTrue(g.is_complete("# comment\nextends Node2D\n"))
        self.assertTrue(g.is_complete("@tool\nextends Node\n"))
        self.assertTrue(g.is_complete("class_name Foo\n"))
        self.assertFalse(g.is_complete("func f():\n\tpass\n"))
        self.assertTrue(g.is_declaration_fragment("@export var s := 1.0\n\nfunc f() -> void:\n\tpass\n"))
        self.assertTrue(g.is_declaration_fragment("static func f() -> int:\n\treturn 1\n"))
        self.assertFalse(g.is_declaration_fragment("velocity.x = 5\n"))
        self.assertFalse(g.is_declaration_fragment("\tindented_first()\n"))
        self.assertFalse(g.is_declaration_fragment("# only a comment\n"))

    def test_multi_file(self):
        self.assertTrue(g.is_multi_file("extends Node\nvar a\n\nextends Node2D\n"))
        self.assertFalse(g.is_multi_file("extends Node\nvar a\n"))

    def test_contrast_markers(self):
        def blk(context, code="extends Node\n"):
            return {"context": context, "code": code}
        self.assertTrue(g.is_contrast(blk("❌ Bad:")))
        self.assertTrue(g.is_contrast(blk("In Godot 3.x this was:")))
        self.assertTrue(g.is_contrast(blk("Problem: the old API")))
        self.assertTrue(g.is_contrast(blk("", "# Before\nextends KinematicBody2D\n")))
        self.assertTrue(g.is_contrast(blk("", "# 3.x\nextends Spatial\n")))
        self.assertTrue(g.is_contrast(blk("", "extends Node  # deprecated\n")))
        self.assertFalse(g.is_contrast(blk("A complete Godot 4 player script:")))
        self.assertFalse(g.is_contrast(blk("Do this before calling start():")))
        # a '#' inside a string is not a comment
        self.assertFalse(g.is_contrast(blk("", 'extends Node\nvar s := "# Before"\n')))


class TestPlan(unittest.TestCase):
    def setUp(self):
        self.path = md("""\
            # Skill

            <!-- gdcheck: skip -->
            ```gdscript
            extends KinematicBody2D
            ```

            ❌ Wrong:

            ```gdscript
            extends Spatial
            ```

            ```gdscript
            extends Node
            func f() -> void:
            \tpass
            ```

            ```gdscript
            velocity.x = 5.0
            ```

            ```gdscript
            func heal(n: int) -> void:
            \tpass
            ```

            <!-- gdcheck: extends Node2D -->
            ```gdscript
            func _ready() -> void:
            \tposition.x = 1.0
            ```

            ```gdscript
            extends Node
            var a := 1

            extends Node2D
            ```

            ```python
            print(1)
            ```

            ```gdscript
            extends Node
            """)

    def test_statuses_default(self):
        e = g.plan_file(self.path)
        self.assertEqual(len(e), 8)  # python block not counted
        st = [x.get("status", "check") for x in e]
        self.assertEqual(st, ["skipped", "skipped", "check", "fragment", "fragment", "check", "skipped", "skipped"])
        self.assertEqual(e[5]["kind"], "fragment")
        self.assertEqual(e[5]["offset"], 1)
        self.assertEqual(e[5]["severity"], "error")
        self.assertTrue(e[5]["code"].startswith("extends Node2D\n"))
        self.assertIn("several scripts", e[6]["reason"])
        self.assertIn("unclosed", e[7]["reason"])

    def test_fragments_flag(self):
        e = g.plan_file(self.path, fragments=True)
        self.assertNotIn("status", e[4])
        self.assertEqual(e[4]["severity"], "warning")
        self.assertTrue(e[4]["code"].startswith("extends Node\n"))
        self.assertEqual(e[3]["status"], "fragment")  # bare statement: never wrapped

    def test_no_auto_skip(self):
        e = g.plan_file(self.path, auto_skip=False)
        self.assertEqual(e[0]["status"], "skipped")  # explicit marker still wins
        self.assertNotIn("status", e[1])

    def test_find_files(self):
        d = Path(tempfile.mkdtemp())
        (d / "a.md").write_text("x", encoding="utf-8")
        (d / "b.gd").write_text("extends Node\n", encoding="utf-8")
        (d / "node_modules").mkdir()
        (d / "node_modules" / "c.md").write_text("x", encoding="utf-8")
        names = [f.name for f in g.find_files([d])]
        self.assertEqual(names, ["a.md"])
        names = [f.name for f in g.find_files([d], gd_files=True)]
        self.assertEqual(names, ["a.md", "b.gd"])
        with self.assertRaises(FileNotFoundError):
            g.find_files([d / "missing"])


class TestClassify(unittest.TestCase):
    def status(self, out, code="", rc=1):
        errs, failed = g.parse_output(out)
        g.classify_errors(errs, code)
        return g.status_of(errs, rc, failed, False), errs

    def test_clean(self):
        self.assertEqual(self.status(HEAD, rc=0)[0], "ok")

    def test_unknown_failure(self):
        self.assertEqual(self.status(HEAD + 'ERROR: Failed to load script "res://s/x.gd"\n')[0], "fail-unknown")

    def test_godot3(self):
        st, errs = self.status(OUT_G3)
        self.assertEqual((st, errs[0]["category"], errs[0]["script_line"]), ("error", "godot3", 3))

    def test_external(self):
        st, errs = self.status(OUT_EXTERNAL)
        self.assertEqual(st, "external")
        self.assertEqual([e["category"] for e in errs], ["external", "external"])

    def test_compile_error_pascal_case_is_external(self):
        st, errs = self.status(OUT_BIGNUMBER)
        self.assertEqual(errs[0]["msg"], "Identifier not found: BigNumber")
        self.assertEqual(st, "external")

    def test_compile_error_lower_case_is_own(self):
        self.assertEqual(self.status(OUT_LOWER)[0], "error")

    def test_variant_inference(self):
        st, errs = self.status(OUT_VARIANT)
        self.assertEqual((st, errs[0]["category"]), ("error", "inference"))

    def test_same_line_cascade_follows_root(self):
        st, errs = self.status(OUT_SAMELINE)
        self.assertEqual([e["category"] for e in errs], ["other", "cascade"])
        self.assertEqual(errs[1]["follows"], "other")
        self.assertEqual(st, "error")

    def test_cascade_from_external_declaration(self):
        code = ('extends Node\n\nconst Bullet := preload("res://bullet.tscn")\n\nfunc fire() -> void:\n'
                '\tvar b := Bullet.instantiate()\n\tadd_child(b)\n')
        out = godot_out(('Parse Error: Preload file "res://bullet.tscn" does not exist.', 3),
                        ('Parse Error: Cannot infer the type of "b" variable because the value doesn\'t '
                         'have a set type.', 6))
        st, errs = self.status(out, code)
        self.assertEqual([e["category"] for e in errs], ["external", "cascade"])
        self.assertEqual(st, "external")

    def test_inference_unrelated_to_external_stays_own(self):
        code = 'extends Node\n\nvar s: Foo\n\nfunc f() -> void:\n\tvar d := JSON.parse_string("1")\n'
        out = godot_out(('Parse Error: Could not find type "Foo" in the current scope.', 3),
                        ("Parse Error: The variable type is being inferred from a Variant value, so it will "
                         "be typed as Variant. (Warning treated as error.)", 6))
        self.assertEqual(self.status(out, code)[0], "error")

    def test_elision(self):
        out = godot_out(('Parse Error: Expected statement, found "..." instead.', 4))
        self.assertEqual(self.status(out)[0], "elision")


class FakeRunner:
    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = 0

    def __call__(self, code):
        self.calls += 1
        for needle, out in self.outputs.items():
            if needle in code:
                return 1, out, False
        return 0, HEAD, False


class TestCheck(unittest.TestCase):
    def test_line_mapping_and_dedupe(self):
        p = md("""\
            # S

            ```gdscript
            extends KinematicBody2D

            onready var t = $T
            ```

            ```gdscript
            extends KinematicBody2D

            onready var t = $T
            ```

            <!-- gdcheck: extends Node2D -->
            ```gdscript
            func _ready() -> void:
            \tvelocity.x = 1.0
            ```

            ```gdscript
            extends Node
            ```
            """)
        runner = FakeRunner({
            "onready var": OUT_G3,
            "velocity.x": godot_out(('Parse Error: Identifier "velocity" not declared in the current scope.', 3)),
        })
        e = g.check_entries(g.plan_file(p), runner)
        self.assertEqual(runner.calls, 3)  # the two identical blocks are checked once
        self.assertEqual([x["status"] for x in e], ["error", "error", "error", "ok"])
        self.assertEqual(e[0]["errors"][0]["line"], 3 + 3)    # fence at 3, script line 3
        self.assertEqual(e[1]["errors"][0]["line"], 9 + 3)
        self.assertEqual(e[2]["errors"][0]["line"], 16 + 3 - 1)  # wrapped: one line added
        self.assertTrue(all("code" not in x for x in e))
        self.assertEqual(g.exit_code_of(e), 1)
        self.assertEqual(g.counts_of(e), {"error": 3, "ok": 1})

    def test_warning_fragment_does_not_fail(self):
        p = md("```gdscript\nfunc heal(n: int) -> void:\n\thealth += n\n```\n")
        runner = FakeRunner({"health": godot_out(('Parse Error: Identifier "health" not declared in the '
                                                  'current scope.', 3))})
        e = g.check_entries(g.plan_file(p, fragments=True), runner)
        self.assertEqual((e[0]["status"], e[0]["severity"]), ("error", "warning"))
        self.assertEqual(g.exit_code_of(e), 0)
        self.assertTrue(g.format_github(e, "4.7.2")[0].startswith("::warning "))

    def test_external_and_fail_on_external(self):
        p = md("```gdscript\nextends Node\nvar s: PlayerStatsResource\n```\n")
        runner = FakeRunner({"PlayerStats": OUT_EXTERNAL})
        e = g.check_entries(g.plan_file(p), runner)
        self.assertEqual(e[0]["status"], "external")
        self.assertEqual(g.exit_code_of(e), 0)
        self.assertEqual(g.exit_code_of(e, fail_on_external=True), 1)
        self.assertTrue(g.format_github(e, "4.7.2")[0].startswith("::warning "))
        self.assertTrue(g.format_github(e, "4.7.2", True)[0].startswith("::error "))

    def test_timeout(self):
        p = md("```gdscript\nextends Node\n```\n")
        e = g.check_entries(g.plan_file(p), lambda code: (None, "", True))
        self.assertEqual(e[0]["status"], "timeout")
        self.assertEqual(g.exit_code_of(e), 1)


class TestOutput(unittest.TestCase):
    def test_github_escaping(self):
        self.assertEqual(g.gh_escape("a%b\nc"), "a%25b%0Ac")
        self.assertEqual(g.gh_escape("x:y,z", prop=True), "x%3Ay%2Cz")
        e = [{"file": "docs/a,b.md", "line": 5, "kind": "script", "severity": "error", "status": "error",
              "errors": [{"line": 7, "msg": "50% wrong\nhere", "category": "other"}]}]
        line = g.format_github(e, "4.7.2")[0]
        self.assertTrue(line.startswith("::error file=docs/a%2Cb.md,line=7,title=gdcheck (Godot 4.7.2)::"))
        self.assertIn("50%25 wrong%0Ahere", line)

    def test_text_and_summary(self):
        e = [{"file": "a.md", "line": 5, "kind": "script", "severity": "error", "status": "error",
              "errors": [{"line": 7, "msg": "bad | thing", "category": "other"}]},
             {"file": "a.md", "line": 9, "kind": "script", "severity": "error", "status": "ok", "errors": []}]
        self.assertEqual(g.format_text(e), ["a.md:7: error: bad | thing [other]"])
        s = g.summary_markdown(e, "4.7.2")
        self.assertIn("| error | 1 |", s)
        self.assertIn("bad \\| thing", s)

    def test_main_without_godot(self):
        p = md("```gdscript\nextends Node\n```\n")
        self.assertEqual(g.main(["--godot", os.path.join(tempfile.mkdtemp(), "no-godot"), str(p)]), 2)


if __name__ == "__main__":
    unittest.main()
