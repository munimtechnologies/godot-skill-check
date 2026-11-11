# SPDX-License-Identifier: Apache-2.0
# By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents (Anthropic Claude).
import unittest

import c5_upstream as c5


class NormTests(unittest.TestCase):
    def test_tabs_and_common_indent(self):
        xml = "\n\t\t\t\tfunc f():\n\t\t\t\t\tpass\n\t\t\t"
        self.assertEqual(c5.norm_lines(xml), ["func f():", "    pass"])

    def test_rst_style_matches_xml_style(self):
        rst = "func f():\n    pass\n"
        xml = "\n\t\t\t\tfunc f():\n\t\t\t\t\tpass\n\t\t\t"
        self.assertEqual(c5.norm_lines(rst), c5.norm_lines(xml))

    def test_inner_blank_lines_kept(self):
        self.assertEqual(c5.norm_lines("a\n\n   \nb\n"), ["a", "", "", "b"])

    def test_indentation_difference_is_seen(self):
        good = "f(func():\n        x()\n    )\n"
        bad = "f(func():\n        x()\n            )\n"
        self.assertNotEqual(c5.norm_lines(good), c5.norm_lines(bad))
        self.assertEqual(c5.stripped(c5.norm_lines(good)), c5.stripped(c5.norm_lines(bad)))


class ContainsTests(unittest.TestCase):
    def test_contiguous_only(self):
        self.assertTrue(c5.contains(["a", "b", "c"], ["b", "c"]))
        self.assertFalse(c5.contains(["a", "b", "c"], ["a", "c"]))
        self.assertFalse(c5.contains(["a"], []))


class XmlTests(unittest.TestCase):
    XMLTEXT = (
        "<description>\n[codeblocks]\n[gdscript]\nvar a = [lb]1, 2[rb]\nif a &lt; b &amp;&amp; c:\n[/gdscript]\n"
        "[csharp]\nint a;\n[/csharp]\n[/codeblocks]\n"
        "[codeblock lang=text]\nplain &quot;x&quot;\n[/codeblock]\n[codeblock]\ny()\n[/codeblock]</description>")

    def test_blocks_found_and_unescaped(self):
        b = c5.xml_blocks(self.XMLTEXT)
        self.assertEqual(len(b), 3)
        self.assertIn("var a = [1, 2]", b[0])
        self.assertIn("if a < b && c:", b[0])
        self.assertNotIn("int a;", "".join(b))
        self.assertIn('plain "x"', b[1])
        self.assertIn("y()", b[2])

    def test_compare(self):
        blocks = c5.xml_blocks(self.XMLTEXT)
        res = c5.compare("var a = [1, 2]\nif a < b && c:\n", blocks, fixed_code="y()\n")
        self.assertTrue(res["same"])
        self.assertTrue(res["same_ignoring_ws"])
        self.assertTrue(res["fixed_present"])
        self.assertEqual(res["best_index"], 0)
        res = c5.compare("var a = [1, 3]\n", blocks)
        self.assertFalse(res["same"])
        self.assertFalse(res["fixed_present"])


class SetupTests(unittest.TestCase):
    def test_every_case_has_a_query_and_xml(self):
        ids = {"R01", "R02", "R03", "R04", "R06", "R07", "R10", "R13", "R14", "R15", "R16", "R18"}
        self.assertEqual(set(c5.QUERIES), ids)
        self.assertEqual(len(c5.XML), 9)
        self.assertTrue(c5.GLANCED <= ids)


if __name__ == "__main__":
    unittest.main()
