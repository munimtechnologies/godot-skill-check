# SPDX-License-Identifier: Apache-2.0
# By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude).
"""Unit tests for verify_classref.py (no Godot needed)."""
import os
import unittest

import verify_classref as v

HERE = os.path.dirname(os.path.abspath(__file__))

# Blocks as transcribed from the class reference (godot-docs 4.7, CC BY 3.0, Godot community),
# used only to test that each correction applies once. The job uses the recorded block_code.
EXPORT_RANGE = (
    "@export_range(0, 20) var number\n"
    "@export_range(-10, 20) var number\n"
    "@export_range(-10, 20, 0.2) var number: float\n"
    "@export_range(0, 20) var numbers: Array[float]\n"
    "\n"
    '@export_range(0, 100, 1, "or_greater") var power_percent\n'
    '@export_range(0, 100, 1, "or_greater", "or_less") var health_delta\n'
    "\n"
    '@export_range(-180, 180, 0.001, "radians_as_degrees") var angle_radians\n'
    '@export_range(0, 360, 1, "degrees") var angle_degrees\n'
    '@export_range(-8, 8, 2, "suffix:px") var target_offset'
)
NODE = (
    "# Assuming the following are children of this node, in order:\n"
    "# First, Middle, Last.\n"
    "\n"
    'var a = get_child(0).name  # a is "First"\n'
    'var b = get_child(1).name  # b is "Middle"\n'
    'var b = get_child(2).name  # b is "Last"\n'
    'var c = get_child(-1).name # c is "Last"'
)
POPUP = (
    "func _ready():\n"
    '    add_multistate_item("Item", 3, 0)\n'
    "\n"
    "    index_pressed.connect(func(index: int):\n"
    "            toggle_item_multistate(index)\n"
    "            match get_item_multistate(index):\n"
    "                0:\n"
    '                    print("First state")\n'
    "        )"
)
LINK = (
    'uri = "https://godotengine.org"  # Opens the URL in the default web browser.\n'
    'uri = "C:\\SomeFolder"  # Opens the file explorer at the given path.\n'
    'uri = "C:\\SomeImage.png"  # Opens the given image in the default viewing app.'
)


def case(cid):
    return next(c for c in v.CASES if c["id"] == cid)


class TestFixes(unittest.TestCase):
    def test_single_replacement(self):
        self.assertEqual(v.apply_fixes("a b", [("b", "c")]), ("a c", None))

    def test_missing_or_double_is_refused(self):
        self.assertIsNone(v.apply_fixes("a b", [("x", "c")])[0])
        self.assertIsNone(v.apply_fixes("b b", [("b", "c")])[0])

    def test_regex_once(self):
        self.assertEqual(v.apply_fixes("x\n  )\n", [("re", r"(?m)^[ \t]+\)[ \t]*$", ")")])[0], "x\n)\n")

    def test_export_range_fix(self):
        fixed, err = v.apply_fixes(EXPORT_RANGE, case("R02")["fix"])
        self.assertIsNone(err)
        for name in ("number: int", "number2: int", "number3: float", "power_percent: int",
                     "health_delta: int", "angle_radians: float", "angle_degrees: float", "target_offset: float"):
            self.assertIn("var " + name, fixed)
        self.assertEqual(fixed.count("var number:"), 1)

    def test_node_fix_order(self):
        fixed, err = v.apply_fixes(NODE, case("R13")["fix"])
        self.assertIsNone(err)
        self.assertIn("var c = get_child(2)", fixed)
        self.assertIn("var d = get_child(-1)", fixed)
        self.assertEqual(fixed.count("var b ="), 1)

    def test_popup_fix(self):
        fixed, err = v.apply_fixes(POPUP, case("R14")["fix"])
        self.assertIsNone(err)
        self.assertTrue(fixed.endswith("\n    )"))

    def test_link_fix(self):
        fixed, err = v.apply_fixes(LINK, case("R10")["fix"])
        self.assertIsNone(err)
        self.assertIn('"C:\\\\SomeFolder"', fixed)
        self.assertIn('"C:\\\\SomeImage.png"', fixed)


class TestScripts(unittest.TestCase):
    def test_standalone_indents_statements(self):
        s = v.standalone(case("R10"), LINK)
        self.assertTrue(s.startswith("extends LinkButton\nfunc demo():\n    uri = "))
        self.assertTrue(s.endswith("\n"))

    def test_standalone_keeps_blank_lines_empty(self):
        s = v.standalone({"header": "func demo():\n", "indent": 4}, "a\n\nb\n")
        self.assertEqual(s, "func demo():\n    a\n\n    b\n")

    def test_cases_are_unique_and_complete(self):
        keys = [(c["file"], c["line"]) for c in v.CASES]
        self.assertEqual(len(keys), 12)
        self.assertEqual(len(set(keys)), 12)
        for c in v.CASES:
            self.assertTrue(c["key"] and c["fix"])
        bases = {c["id"] for c in v.CASES}
        for x in v.EXTRA:
            self.assertIn(x["base"], bases)

    def test_cases_match_the_real_labels(self):
        with open(os.path.join(HERE, "handcheck.csv"), encoding="utf-8") as f:
            labels = v.read_labels(f.read())
        self.assertEqual(len(labels), 20)
        real = {k for k, lab in labels.items() if lab == "real"}
        self.assertEqual(real, {(c["file"], c["line"]) for c in v.CASES})
        self.assertTrue(set(labels.values()) <= {"real", "intended", "context", "tool", "unsure"})


class TestEvaluate(unittest.TestCase):
    def test_ok(self):
        self.assertTrue(v.evaluate("ok", "ok", [])[0])
        self.assertFalse(v.evaluate("ok", "error", ["x"])[0])

    def test_error(self):
        self.assertTrue(v.evaluate("error", "error", ["has key here"], must=["key"])[0])
        self.assertFalse(v.evaluate("error", "error", ["other"], must=["key"])[0])
        self.assertFalse(v.evaluate("error", "error", ["key", "bad"], must=["key"], forbid=["bad"])[0])

    def test_norm_and_probe(self):
        self.assertEqual(v.norm("a \r\nb\n"), "a\nb")
        self.assertEqual(v.parse_probe("PROBE x= True\nnoise"), {"x": "true"})


if __name__ == "__main__":
    unittest.main()
