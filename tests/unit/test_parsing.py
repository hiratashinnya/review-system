"""TC-parsing-001: 自前フロントマター・パーサ＋lint（S5）。境界値・エッジ厚め。

TDD: 実装より先に契約を固定。対応サブセット外は黙って通さず MiniYamlError で弾く。
"""
import unittest

from review_system.parsing.frontmatter import parse_frontmatter, MiniYamlError
from review_system.parsing.lint import lint_criteria

VALID = """\
---
doc_type: code
scope: org
extends: null
version: "1.0"
rules:
  - id: naming-convention
    title: 命名規則
    severity: error
    determinism: deterministic
    enabled: true
    override: tighten-only
---
"""


def fm(text, is_markdown=True):
    return parse_frontmatter(text, is_markdown=is_markdown)


class TestParserSubset(unittest.TestCase):
    def test_normal(self):                               # P1
        d = fm(VALID)
        self.assertEqual(d["doc_type"], "code")
        self.assertIsInstance(d["rules"], list)
        self.assertEqual(d["rules"][0]["id"], "naming-convention")

    def test_scalar_types(self):                         # P2
        d = fm(VALID)
        self.assertEqual(d["version"], "1.0")            # 文字列のまま（整数化しない）
        self.assertIs(d["rules"][0]["enabled"], True)    # bool
        self.assertIsNone(d["extends"])                  # null → None
        self.assertEqual(d["rules"][0]["severity"], "error")

    def test_comments_ignored(self):                     # P3
        d = fm("---\n# 先頭コメント\ndoc_type: code   # 行末コメント\nscope: org\nrules:\n  - id: a\n---\n")
        self.assertEqual(d["doc_type"], "code")

    def test_hash_in_quotes_preserved(self):             # P4（エッジ）
        d = fm('---\ndoc_type: code\nscope: org\ntitle: "a # b"\nrules:\n  - id: a\n---\n')
        self.assertEqual(d["title"], "a # b")

    def test_tab_indent_rejected(self):                  # P5（境界）
        with self.assertRaises(MiniYamlError):
            fm("---\ndoc_type: code\nrules:\n\t- id: a\n---\n")

    def test_flow_style_rejected(self):                  # P6（境界）
        with self.assertRaises(MiniYamlError):
            fm("---\ndoc_type: code\ncats: [a, b]\n---\n")

    def test_multiline_scalar_rejected(self):            # P7（境界）
        with self.assertRaises(MiniYamlError):
            fm("---\ndoc_type: code\ndesc: |\n  long\n---\n")

    def test_anchor_rejected(self):                      # P8（境界）
        with self.assertRaises(MiniYamlError):
            fm("---\ndoc_type: &x code\n---\n")

    def test_missing_closing_fence(self):                # P9（境界）
        with self.assertRaises(MiniYamlError):
            fm("---\ndoc_type: code\nscope: org\n")

    def test_odd_indent_rejected(self):                  # P10（エッジ：3スペース）
        with self.assertRaises(MiniYamlError):
            fm("---\nrules:\n   - id: a\n---\n")


def lint(text, exists=lambda ref: True):
    return lint_criteria(parse_frontmatter(text, is_markdown=True), exists=exists)


class TestLint(unittest.TestCase):
    def test_valid_ok(self):                             # L1
        self.assertTrue(lint(VALID).ok)

    def test_bad_override(self):                         # L2
        bad = VALID.replace("override: tighten-only", "override: loose")
        self.assertFalse(lint(bad).ok)

    def test_bad_severity(self):                         # L3
        bad = VALID.replace("severity: error", "severity: fatal")
        self.assertFalse(lint(bad).ok)

    def test_bad_determinism(self):                      # L4
        bad = VALID.replace("determinism: deterministic", "determinism: maybe")
        self.assertFalse(lint(bad).ok)

    def test_missing_required_key(self):                 # L5
        bad = VALID.replace("doc_type: code\n", "")
        self.assertFalse(lint(bad).ok)

    def test_duplicate_rule_id(self):                    # L6（エッジ）
        dup = VALID[:-4] + "  - id: naming-convention\n    severity: warning\n---\n"
        res = lint(dup)
        self.assertFalse(res.ok)
        self.assertTrue(any("naming-convention" in e.reason for e in res.errors))

    def test_unsupported_major(self):                    # L7（境界）
        bad = VALID.replace('version: "1.0"', 'version: "2.0"')
        self.assertFalse(lint(bad).ok)

    def test_supported_major_newer_minor_ok(self):       # L8（境界：MINOR は情報のみ）
        good = VALID.replace('version: "1.0"', 'version: "1.9"')
        self.assertTrue(lint(good).ok)

    def test_extends_missing_target(self):               # L9
        bad = VALID.replace("extends: null", 'extends: "org"')
        self.assertFalse(lint(bad, exists=lambda ref: False).ok)


if __name__ == "__main__":
    unittest.main()
