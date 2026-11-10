# SPDX-License-Identifier: Apache-2.0
# By MV2 of Munim, Inc. Made with AI agents (Anthropic Claude).
import unittest

import verify


class EvaluateTest(unittest.TestCase):
    def c(self, **kw):
        base = {"expect": "error", "must": [], "allow": [], "forbid": []}
        base.update(kw)
        return base

    def test_ok_case(self):
        self.assertTrue(verify.evaluate(self.c(expect="ok"), "ok", [])[0])
        self.assertFalse(verify.evaluate(self.c(expect="ok"), "error", ["x"])[0])

    def test_must(self):
        c = self.c(must=["Expected end of file"])
        self.assertTrue(verify.evaluate(c, "error", ["Expected end of file."])[0])
        self.assertFalse(verify.evaluate(c, "error", ["Other."])[0])
        self.assertFalse(verify.evaluate(c, "ok", [])[0])

    def test_allow_and_forbid(self):
        c = self.c(must=["button_pressed"], allow=["button_pressed"], forbid=["end of file"])
        self.assertTrue(verify.evaluate(c, "error", ['Identifier "button_pressed" not declared.'])[0])
        self.assertFalse(verify.evaluate(c, "error", ['Identifier "button_pressed" not declared.',
                                                      "Expected end of file."])[0])
        self.assertFalse(verify.evaluate(c, "error", ['Identifier "button_pressed" not declared.', "Other."])[0])

    def test_cases_well_formed(self):
        ids = [c["id"] for c in verify.CASES]
        self.assertEqual(len(ids), len(set(ids)))
        for c in verify.CASES:
            self.assertIn(c["expect"], ("ok", "error"))
            self.assertEqual(c["code"].endswith("\n"), c["eof_newline"], c["id"])
            self.assertTrue(c["code"].startswith("extends "), c["id"])

    def test_fixes_differ_by_one_edit(self):
        self.assertEqual(verify.ANIM98_ASIS.replace('"))', '")'), verify.ANIM98_FIXED)
        self.assertEqual(verify.ANIM173_ASIS.replace('"))', '")'), verify.ANIM173_FIXED)

    def test_parse_probe(self):
        p = verify.parse_probe("noise\nPROBE auth_timeout=true\nPROBE pfi_args=3\n")
        self.assertEqual(p, {"auth_timeout": "true", "pfi_args": "3"})


if __name__ == "__main__":
    unittest.main()
