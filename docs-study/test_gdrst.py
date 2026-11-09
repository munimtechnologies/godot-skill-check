# Tests for gdrst (no Godot needed; Godot's messages are copied from real 4.7.2 output).
# By MV2 of Munim, Inc. Made with AI agents (Anthropic Claude).
# SPDX-License-Identifier: Apache-2.0
import unittest

import gdcheck as g
import gdrst as r

TABS = """\
Some intro.

Write this code below.

.. tabs::
 .. code-tab:: gdscript GDScript

    extends Area2D

    @export var speed = 400

 .. code-tab:: csharp C#

    using Godot;

    public partial class Player : Area2D
    {
    }

More prose.
"""

LITERAL = """\
Typed variables
---------------

With types, you can enforce this::

    var damage: float = 10.5

.. note::

    Inside a note, an example:

    ::

        func hit(damage: float) -> bool:
            return true

.. highlight:: none

Console output::

    scons platform=linuxbsd
"""

COMMENT = """\
.. UPDATE: this comment has a body that ends with a colon pair::

    var not_code = 1

.. _doc_target:

Real paragraph::

    var real = 2
"""


class TestExtract(unittest.TestCase):
    def test_code_tabs(self):
        b = r.extract_rst_blocks(TABS)
        self.assertEqual([x["lang"] for x in b], ["gdscript", "csharp"])
        self.assertEqual(b[0]["source"], "code-tab")
        self.assertEqual(b[0]["line"], 6)
        self.assertEqual(b[0]["first_line"], 8)
        self.assertEqual(b[0]["code"], "extends Area2D\n\n@export var speed = 400")
        self.assertEqual(b[0]["context"], "Some intro.\nWrite this code below.")
        self.assertTrue(b[1]["code"].startswith("using Godot;"))

    def test_spaced_directive_and_options(self):
        text = ("Note:\n\n.. tabs::\n\n           .. code-tab :: gdscript GDScript\n"
                "              :emphasize-lines: 2\n\n             if x:\n                 y()\n")
        b = r.extract_rst_blocks(text)
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]["code"], "if x:\n    y()")
        self.assertEqual(b[0]["first_line"], 8)

    def test_literal_blocks_and_highlight(self):
        b = r.extract_rst_blocks(LITERAL)
        self.assertEqual([x["source"] for x in b], ["literal-default", "literal-default", "literal-highlight"])
        self.assertEqual(b[0]["code"], "var damage: float = 10.5")
        self.assertEqual(b[0]["first_line"], 6)
        self.assertEqual(b[0]["context"], "Typed variables\nWith types, you can enforce this::")
        self.assertEqual(b[1]["code"], "func hit(damage: float) -> bool:\n    return true")
        self.assertEqual(b[1]["context"], "Inside a note, an example:\n::")
        self.assertEqual(b[2]["lang"], "none")

    def test_comment_bodies_are_ignored(self):
        b = r.extract_rst_blocks(COMMENT)
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]["code"], "var real = 2")

    def test_code_block_without_language_takes_default(self):
        b = r.extract_rst_blocks(".. code-block::\n\n    extends Node\n\n.. code-block:: glsl\n\n    void f() {}\n")
        self.assertEqual([x["lang"] for x in b], ["gdscript", "glsl"])
        self.assertEqual([x["source"] for x in b], ["code-block", "code-block"])

    def test_paragraph_without_indented_body_is_not_a_block(self):
        self.assertEqual(r.extract_rst_blocks("Ends with colons::\nnot indented\n"), [])


class TestPlan(unittest.TestCase):
    def test_complete_then_fragments_use_page_base(self):
        text = TABS + """
.. tabs::
 .. code-tab:: gdscript GDScript

    func _ready():
        screen_size = get_viewport_rect().size

.. tabs::
 .. code-tab:: gdscript GDScript

    position += velocity * delta
    hide()
"""
        es = r.plan_rst_text(text, "p.rst")
        self.assertEqual([e["kind"] for e in es], ["script", "decl-fragment", "stmt-fragment"])
        self.assertEqual(es[1]["base"], "Area2D")
        self.assertTrue(es[1]["code"].startswith("extends Area2D\nfunc _ready():"))
        self.assertEqual(es[1]["offset"], 1)
        self.assertEqual(es[2]["code"], "extends Area2D\nfunc __gdcheck_fragment():\n"
                                        "    position += velocity * delta\n    hide()\n")
        self.assertEqual(es[2]["offset"], 2)

    def test_literal_default_statements_are_not_wrapped(self):
        es = r.plan_rst_text("Run::\n\n    scons platform=linuxbsd\n\nCode::\n\n    var a = 1\n", "p.rst")
        self.assertEqual(es[0]["status"], "fragment")
        self.assertIn("literal block", es[0]["reason"])
        self.assertEqual(es[1]["kind"], "decl-fragment")

    def test_contrast_markers(self):
        text = ("This will trigger a **syntax error**.\n\n"
                "1. You can't specify the type of individual elements::\n\n"
                "    var enemies: Array = [$Goblin: Enemy]\n\n"
                "Fine::\n\n    var ok = 1\n\n"
                "Nested::\n\n    var a: Array[int] = []\n    # The following would be errors:\n    var b = 1\n\n"
                "**Bad**:\n\n.. code-block:: gdscript\n\n    extends Node\n")
        es = r.plan_rst_text(text, "p.rst")
        self.assertEqual([e.get("status") for e in es], ["skipped", None, "skipped", "skipped"])

    def test_mixed_and_indented_fragments(self):
        mixed = ".. code-block:: gdscript\n\n    func f():\n        pass\n    f()\n"
        es = r.plan_rst_text(mixed, "p.rst")
        self.assertEqual(es[0]["reason"], "mixes declarations and statements")
        ind = ".. code-block:: gdscript\n\n    # c\n        x = 1\n    y = 2\n"
        es = r.plan_rst_text(ind, "p.rst")
        self.assertEqual(es[0]["reason"], "first code line is indented")

    def test_script_base(self):
        self.assertEqual(r.script_base("@tool\nextends EditorPlugin\n"), "EditorPlugin")
        self.assertEqual(r.script_base("class_name Child extends Parent\n"), "Parent")
        self.assertIsNone(r.script_base('extends "res://a.gd"\n'))


def errs(*pairs):
    out = [{"msg": m, "script_line": ln} for m, ln in pairs]
    return out


class TestClassify(unittest.TestCase):
    def classify(self, e, code, fragment):
        g.classify_errors(e, code)
        r.reclassify(e, code, fragment)
        return r.status_of(e, 1, True, False)

    def test_fragment_context(self):
        code = "extends Area2D\nfunc _ready():\n    screen_size = get_viewport_rect().size\n"
        e = errs(('Identifier "screen_size" not declared in the current scope.', 3))
        self.assertEqual(self.classify(e, code, True), "context")
        self.assertEqual(e[0]["category"], "context")

    def test_same_message_in_complete_script_is_error(self):
        code = "extends Area2D\nfunc _ready():\n    screen_size = 1\n"
        e = errs(('Identifier "screen_size" not declared in the current scope.', 3))
        self.assertEqual(self.classify(e, code, False), "error")

    def test_inference_after_context_is_cascade(self):
        code = "extends Node\nfunc __gdcheck_fragment():\n    var space := get_world_3d().direct_space_state\n"
        e = errs(('Function "get_world_3d()" not found in base self.', 3),
                 ("Cannot infer the type of \"space\" variable because the value doesn't have a set type.", 3))
        self.assertEqual(self.classify(e, code, True), "context")
        self.assertEqual(e[1]["category"], "cascade")
        self.assertEqual(e[1]["follows"], "context")

    def test_inference_using_context_name_later(self):
        code = ("extends Node\nfunc __gdcheck_fragment():\n    var v = speed\n    var w := v\n")
        e = errs(('Identifier "speed" not declared in the current scope.', 3),
                 ("Cannot infer the type of \"w\" variable because the value doesn't have a set type.", 4))
        self.assertEqual(self.classify(e, code, True), "context")
        self.assertEqual(e[1]["follows"], "context")

    def test_real_fragment_error_survives(self):
        code = "extends CharacterBody2D\nfunc __gdcheck_fragment():\n    move_and_slide(velocity)\n"
        e = errs(('Too many arguments for "move_and_slide()" call. Expected at most 0 but received 1.', 3))
        self.assertEqual(self.classify(e, code, True), "error")

    def test_godot3_in_fragment(self):
        code = "extends Node\nfunc __gdcheck_fragment():\n    yield(get_tree(), \"idle_frame\")\n"
        e = errs(('The "yield" keyword was removed in Godot 4. Use "await" instead.', 3))
        self.assertEqual(self.classify(e, code, True), "error")
        self.assertEqual(e[0]["category"], "godot3")

    def test_elided_body(self):
        code = "class_name Parent\n\nfunc get_property() -> Node:\n    # ...\n"
        e = errs(("Expected indented block after function declaration.", 4))
        self.assertEqual(self.classify(e, code, False), "elision")

    def test_empty_body_without_elision_is_error(self):
        code = "extends Node\n\nfunc f():\n"
        e = errs(("Expected indented block after function declaration.", 4))
        self.assertEqual(self.classify(e, code, False), "error")

    def test_ok_and_unknown(self):
        self.assertEqual(r.status_of([], 0, False, False), "ok")
        self.assertEqual(r.status_of([], 1, True, False), "fail-unknown")
        self.assertEqual(r.status_of([], None, False, True), "timeout")


class FakeRunner:
    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = []

    def __call__(self, code):
        self.calls.append(code)
        first = code.split("\n", 1)[0]
        return self.outputs.get(first, (0, "Godot Engine v4.7.2.stable\n", False))


def out_err(msg, line):
    return (1, f"SCRIPT ERROR: Parse Error: {msg}\n          at: GDScript::reload (res://s/x.gd:{line})\n"
               f'ERROR: Failed to load script "res://s/x.gd" with error "Parse error".\n', False)


class TestCheckEntry(unittest.TestCase):
    def test_base_retry_and_line_mapping(self):
        e = {"file": "p.rst", "line": 20, "index": 2, "kind": "stmt-fragment", "offset": 2,
             "severity": "warning", "base": "Parent",
             "code": "extends Parent\nfunc __gdcheck_fragment():\n    a()\n    b(\n"}
        runner = FakeRunner({"extends Parent": out_err('Could not find base class "Parent".', 1),
                             "extends Node": out_err('Expected closing ")" after call arguments.', 4)})
        r.check_entry(e, runner, {})
        self.assertEqual(len(runner.calls), 2)
        self.assertEqual(e["base"], "Node")
        self.assertEqual(e["base_retry"], "Parent")
        self.assertEqual(e["status"], "error")
        self.assertEqual(e["errors"][0]["line"], 21)

    def test_script_line_mapping_and_cache(self):
        cache = {}
        e1 = {"file": "p.rst", "line": 8, "index": 1, "kind": "script", "offset": 0, "severity": "error",
              "code": "extends Node\nfunc f():\n    x(\n"}
        e2 = dict(e1, index=2, line=30)
        runner = FakeRunner({"extends Node": out_err('Expected closing ")" after call arguments.', 3)})
        r.check_entry(e1, runner, cache)
        r.check_entry(e2, runner, cache)
        self.assertEqual(len(runner.calls), 1)
        self.assertEqual(e1["errors"][0]["line"], 10)
        self.assertEqual(e2["errors"][0]["line"], 32)

    def test_docs_url(self):
        self.assertEqual(r.docs_url("tutorials/scripting/gdscript/static_typing.rst"),
                         "https://docs.godotengine.org/en/4.7/tutorials/scripting/gdscript/static_typing.html")


if __name__ == "__main__":
    unittest.main()
