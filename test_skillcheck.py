# Tests for godot-skill-check. By MV2 of Munim, Inc. Made with AI agents (Anthropic Claude).
# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path

import skillcheck as sc


class TestText(unittest.TestCase):
    def test_split_code(self):
        code, nostr = sc.split_code('var a = "x # y" # comment')
        self.assertEqual(code, 'var a = "x # y" ')
        self.assertEqual(nostr, 'var a = "_____" ')
        self.assertEqual(sc.comment_of('var a = 1 # hi'), '# hi')

    def test_extract_blocks(self):
        text = ("Intro\n\n```gdscript\nextends Node\n```\n\n- item\n\n"
                "  ```gd title=x.gd\n  func f():\n  \tpass\n  ```\n~~~python\nprint(1)\n~~~\n")
        b = sc.extract_blocks(text)
        self.assertEqual([x["lang"] for x in b], ["gdscript", "gd", "python"])
        self.assertEqual(b[0]["start_line"], 3)
        self.assertEqual(b[0]["code"], "extends Node")
        self.assertEqual(b[0]["context"], "Intro")
        self.assertEqual(b[1]["start_line"], 9)
        self.assertEqual(b[1]["code"], "func f():\n\tpass")
        self.assertTrue(all(x["closed"] for x in b))

    def test_complete_and_multi_file(self):
        self.assertTrue(sc.is_complete("# comment\nextends Node2D"))
        self.assertTrue(sc.is_complete("@tool\nextends EditorPlugin"))
        self.assertTrue(sc.is_complete("tool\nextends Node"))
        self.assertTrue(sc.is_complete("class_name Foo\nextends Node"))
        self.assertFalse(sc.is_complete("func _ready():\n\tpass"))
        self.assertTrue(sc.is_multi_file("extends Node\n\nfunc a():\n\tpass\n\nextends Node2D"))
        self.assertFalse(sc.is_multi_file("extends Node\n\nfunc a():\n\tpass"))


class TestStatic(unittest.TestCase):
    CODE = "\n".join([
        "extends KinematicBody2D",
        "onready var s = $Sprite",
        'var t = "Sprite"',
        "func _ready():",
        '\tyield(get_tree(), "idle_frame")',
        '\tconnect("hit", self, "_on_hit")',
        "\tvelocity = move_and_slide(velocity)",
        "\tmove_and_slide()",
        '\tget_tree().change_scene_to_file("res://a.tscn")',
        "\tvar x = rand_range(0, 1) # Godot 3 only, wrong",
        "\tvar y = CharacterBody2D.new()",
    ])

    def test_hits(self):
        hits = {(h["line"], h["pattern"]) for h in sc.scan_static(self.CODE)}
        self.assertEqual(hits, {(1, "renamed-class"), (2, "onready-keyword"), (5, "yield"),
                                (6, "string-connect-with-self"), (7, "move-and-slide-args")})

    def test_godot4_code_is_clean(self):
        self.assertEqual(sc.scan_static(sc.CONTROL_GOOD), [])
        self.assertTrue(len(sc.scan_static(sc.CONTROL_G3)) >= 4)

    def test_more_patterns(self):
        cases = {
            "export var speed = 10": "export-keyword",
            "export(int) var hp = 3": "export-keyword",
            "var hp = 3 setget set_hp": "setget",
            "var e = scene.instance()": "instance-call",
            "var a = PoolStringArray()": "pool-array",
            "get_tree().change_scene(\"res://b.tscn\")": "change-scene",
            "var f = File.new()": "file-directory-new",
            "remote func sync_pos(p):": "rpc-keyword",
            "if Engine.editor_hint:": "editor-hint-property",
            "var t = OS.get_ticks_msec()": "os-moved-method",
            "if event.button_index == BUTTON_LEFT:": "mouse-button-constant",
            "var r = deg2rad(90)": "renamed-global-function",
        }
        for line, pattern in cases.items():
            got = [h["pattern"] for h in sc.scan_static(line)]
            self.assertIn(pattern, got, line)
        for line in ["@export var speed = 10", "@onready var s = $Sprite", "var a = PackedStringArray()",
                     "var e = scene.instantiate()", "var r = deg_to_rad(90)", "var s: Sprite2D",
                     "var f = FileAccess.open(p, FileAccess.READ)", "if event.button_index == MOUSE_BUTTON_LEFT:",
                     "var p = $Navigation/Agent", "await get_tree().process_frame"]:
            self.assertEqual(sc.scan_static(line), [], line)

    def test_block_contrast(self):
        self.assertTrue(sc.block_contrast({"code": "extends Node", "context": "Common mistake: don't do this"}))
        self.assertTrue(sc.block_contrast({"code": "# ❌ Bad\nyield(x)", "context": ""}))
        self.assertFalse(sc.block_contrast({"code": "# avoid allocating here\nvar a = 1", "context": "Example:"}))
        self.assertTrue(sc.block_contrast({"code": "extends Node", "context": "", "path_hint": "examples/bad_example.gd"}))
        self.assertFalse(sc.block_contrast({"code": "extends Node", "context": "", "path_hint": "scripts/player.gd"}))


class TestGodotOutput(unittest.TestCase):
    OUT = ("Godot Engine v4.7.2.stable.official - https://godotengine.org\n\n"
           'SCRIPT ERROR: Parse Error: Could not find type "PlayerStats" in the current scope.\n'
           "          at: GDScript::reload (res://s/abc.gd:3)\n"
           'SCRIPT ERROR: Parse Error: Function "rand_range()" not found in base self.\n'
           "          at: GDScript::reload (res://s/abc.gd:7)\n"
           'ERROR: Failed to load script "res://s/abc.gd" with error "Parse error".\n'
           "   at: load (modules/gdscript/gdscript.cpp:2936)\n")

    def test_parse_output(self):
        errs, failed = sc.parse_output(self.OUT)
        self.assertTrue(failed)
        self.assertEqual([(e["msg"], e["line"]) for e in errs], [
            ('Could not find type "PlayerStats" in the current scope.', 3),
            ('Function "rand_range()" not found in base self.', 7)])

    def test_classify(self):
        st, errs = sc.classify_script(1, self.OUT, False)
        self.assertEqual(st, "real-error")
        self.assertEqual([e["category"] for e in errs], ["external", "godot3"])

        def one(msg):
            return f"SCRIPT ERROR: Parse Error: {msg}\n          at: GDScript::reload (res://s/x.gd:2)\n"
        self.assertEqual(sc.classify_script(1, one('Could not find base class "Player".'), False)[0], "external-only")
        self.assertEqual(sc.classify_script(1, one('Identifier "GameManager" not declared in the current scope.'),
                                            False)[0], "external-only")
        self.assertEqual(sc.classify_script(1, one('Identifier "SPEED" not declared in the current scope.'),
                                            False)[0], "real-error")
        self.assertEqual(sc.classify_script(1, one('Expected statement, found "..." instead.'), False)[0],
                         "elision-only")
        st, errs = sc.classify_script(1, one("The variable type is being inferred from a Variant value, so it "
                                             "will be typed as Variant. (Warning treated as error.)"), False)
        self.assertEqual((st, errs[0]["category"]), ("real-error", "inference"))
        self.assertEqual(sc.classify_script(1, one('Could not find base class "KinematicBody2D".'), False)[0],
                         "real-error")
        self.assertEqual(sc.classify_script(0, "Godot Engine v4.7.2.stable\n", False)[0], "clean")
        self.assertEqual(sc.classify_script(1, "Godot Engine v4.7.2.stable\n", False)[0], "unclassified-fail")
        self.assertEqual(sc.classify_script(None, "", True)[0], "timeout")
        self.assertEqual(sc.classify_error('Unexpected "Identifier" in class body.', [3], 3), "godot3")


class TestRepo(unittest.TestCase):
    def test_index_locate_files(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            a = root / "skills" / "a"
            (a / "references").mkdir(parents=True)
            (a / "nested").mkdir()
            (root / "b").mkdir()
            (a / "SKILL.md").write_text("---\nname: alpha\ndescription: x\n---\n# A\n")
            (a / "references" / "x.md").write_text("ref")
            (a / "nested" / "SKILL.md").write_text("---\nname: inner\n---\n")
            (a / "nested" / "y.md").write_text("y")
            (root / "b" / "SKILL.md").write_text("# no frontmatter\n")
            idx_name, idx_dir = sc.index_repo(root)
            self.assertEqual(sorted(idx_name), ["alpha", "inner"])
            d, how, n = sc.locate("alpha", idx_name, idx_dir)
            self.assertEqual((d, how, n), (a, "frontmatter-name", 1))
            d, how, _ = sc.locate("b", idx_name, idx_dir)
            self.assertEqual((d, how), (root / "b", "folder-name"))
            self.assertEqual(sc.locate("zzz", idx_name, idx_dir)[1], "not-found")
            files = [p.relative_to(a).as_posix() for p in sc.skill_files(a)]
            self.assertEqual(files, ["SKILL.md", "references/x.md"])

    def test_search_results(self):
        self.assertEqual(sc.search_results({"query": "x", "skills": [{"id": "a"}]}), [{"id": "a"}])
        self.assertEqual(sc.search_results([{"id": "a"}]), [{"id": "a"}])
        self.assertEqual(sc.search_results({"foo": [{"id": "z"}]}), [{"id": "z"}])
        self.assertEqual(sc.search_results({"count": 0}), [])


class TestPredictions(unittest.TestCase):
    def setUp(self):
        def row(i, inst, lab, comp, hits, hashes):
            return {"id": f"o/r/{i}", "source": "o/r", "installs": inst, "labeled_blocks": lab, "gd_files": 0,
                    "complete_blocks": comp, "excluded_blocks": 0, "static_hits": hits, "script_hashes": hashes}
        self.skills = [row("a", 100, 4, 1, 1, ["h1"]), row("b", 50, 2, 1, 0, ["h2"]), row("c", 10, 0, 0, 0, [])]
        self.scripts = {"h1": {"status": "real-error", "errors": [{"category": "inference"}]},
                        "h2": {"status": "clean", "errors": []}}
        self.meta = {"godot_version": "4.7.2.stable.official.abc",
                     "controls": {"control-good": {"expected": "clean", "got": "clean"}}}

    def test_values(self):
        r = sc.compute_predictions(self.skills, self.scripts, self.meta)
        self.assertTrue(r["M1_controls_ok"] and r["M2_godot_version_ok"])
        self.assertEqual(r["P1"]["skills_with_code"], 2)
        self.assertEqual(r["P1"]["verdict"], "failed")
        self.assertEqual(r["P2_core"]["share"], 0.5)
        self.assertEqual(r["P2_core"]["verdict"], "failed")
        self.assertEqual(r["P3_core"]["share"], 0.5)
        self.assertEqual(r["P3_core"]["verdict"], "held")
        self.assertEqual(r["P4"]["verdict"], "not gradable")
        self.assertEqual(r["P5"]["verdict"], "held")
        self.assertAlmostEqual(r["P6"]["share"], 2 / 6)
        self.assertEqual(r["P6"]["verdict"], "held")

    def test_controls_gate(self):
        self.meta["controls"]["control-good"]["got"] = "unclassified-fail"
        r = sc.compute_predictions(self.skills, self.scripts, self.meta)
        self.assertEqual(r["P3_core"]["verdict"], "not gradable")
        self.assertEqual(r["P5"]["verdict"], "not gradable")
        self.assertEqual(r["P2_core"]["verdict"], "failed")


if __name__ == "__main__":
    unittest.main()
