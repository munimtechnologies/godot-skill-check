# Tests for docs_study's grading (no Godot needed).
# By MV2 of Munim, Inc. Made with AI agents (Anthropic Claude).
# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path

import docs_study as d


def ent(kind, status, complete=False, stratum="manual", cats=()):
    return {"kind": kind, "status": status, "complete": complete, "stratum": stratum,
            "errors": [{"category": c, "msg": "m", "line": 1} for c in cats]}


class TestGrade(unittest.TestCase):
    def test_grade(self):
        es = ([ent("script", "ok", True)] * 18 + [ent("script", "error", True, cats=("other",))] * 2
              + [ent("decl-fragment", "context", cats=("context",))] * 30
              + [ent("stmt-fragment", "error", cats=("godot3",))] * 1
              + [ent("stmt-fragment", "ok")] * 9
              + [ent("fragment", "fragment")] * 40
              + [ent("script", "error", True, stratum="classes", cats=("other",))] * 50)
        res = d.grade(es)
        self.assertEqual(res["P1"]["value"], 100)
        self.assertFalse(res["P1"]["held"])
        self.assertEqual(res["P2"]["value_pct"], 20.0)
        self.assertTrue(res["P2"]["held"])
        self.assertEqual(res["P3"]["value_pct"], 10.0)
        self.assertTrue(res["P3"]["held"])
        self.assertEqual(res["P5"]["godot3_blocks"], 1)
        self.assertEqual(res["P5"]["of"], 60)
        self.assertFalse(res["P5"]["held"])
        self.assertTrue(res["P6"]["held"])
        self.assertEqual(res["P7"]["of"], 40)
        self.assertEqual(res["P7"]["value_pct"], 2.5)
        self.assertFalse(res["P7"]["held"])
        self.assertIsNone(res["P4"]["held"])

    def test_cascade_roots(self):
        e = {"errors": [{"category": "cascade", "follows": "context"}, {"category": "context"}]}
        self.assertEqual(d.root_categories(e), ["context"])

    def test_rst_files_skips_underscore_dirs(self):
        root = Path(tempfile.mkdtemp())
        for p in ["index.rst", "classes/class_node.rst", "_tools/x.rst", "tutorials/a/b.rst", ".git/c.rst"]:
            (root / p).parent.mkdir(parents=True, exist_ok=True)
            (root / p).write_text("x\n", encoding="utf-8")
        got = [p.relative_to(root).as_posix() for p in d.rst_files(root)]
        self.assertEqual(got, ["classes/class_node.rst", "index.rst", "tutorials/a/b.rst"])
        self.assertEqual(d.stratum("classes/class_node.rst"), "classes")
        self.assertEqual(d.stratum("tutorials/a/b.rst"), "manual")


if __name__ == "__main__":
    unittest.main()
