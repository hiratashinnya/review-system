"""TC-repo-001: 基準/ポリシーの filesystem ローダ（DS1）。tmp ファイルで検証。"""
import tempfile
import unittest
from pathlib import Path

from review_system.domain.enums import (
    DocumentType, Determinism, Severity, OverrideRule, ApplicationMode, InheritanceLayer,
)
from review_system.domain.ids import RuleId, Scope
from review_system.persistence import criteria_repo as R

CRITERIA = """\
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
  - id: dead-code
    title: 未使用コード
    severity: warning
    determinism: tradeoff
    enabled: true
    override: tighten-only
---

## naming-convention — 命名規則

変数・関数の命名が規約に沿っているか。

## dead-code — 未使用コード

到達しないコードを検出する。
"""

POLICY = """\
scope: org
extends: null
version: "1.0"
matrix:
  deterministic:
    "*": auto_fix_log_only
  tradeoff:
    "*": auto_fix_suggest
  judgment:
    "*": human_only
overrides:
  - rule: secret-in-code
    mode: human_only
"""


class TestCriteriaRepo(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "code.md").write_text(CRITERIA, encoding="utf-8")
        (self.dir / "policy.yaml").write_text(POLICY, encoding="utf-8")

    def test_load_criteria_builds_composed_rules(self):
        rules = R.load_criteria_file(self.dir / "code.md")
        self.assertEqual(len(rules), 2)
        naming = next(r for r in rules if r.rule_id == RuleId("naming-convention"))
        self.assertEqual(naming.meta.determinism, Determinism.DETERMINISTIC)
        self.assertEqual(naming.meta.severity, Severity.ERROR)
        self.assertEqual(naming.meta.override, OverrideRule.TIGHTEN_ONLY)
        self.assertEqual(naming.provenance.inheritance_layer, InheritanceLayer.ORG)

    def test_guidance_body_extracted(self):              # 本文セクション抽出
        rules = R.load_criteria_file(self.dir / "code.md")
        naming = next(r for r in rules if r.rule_id == RuleId("naming-convention"))
        self.assertIn("命名が規約", naming.guidance.summary)

    def test_load_policy_matrix(self):
        pol = R.load_policy_file(self.dir / "policy.yaml")
        self.assertEqual(
            pol.resolve(Determinism.DETERMINISTIC, Severity.ERROR, RuleId("x")),
            ApplicationMode.AUTO_FIX_LOG_ONLY)
        # override が最優先
        self.assertEqual(
            pol.resolve(Determinism.DETERMINISTIC, Severity.ERROR, RuleId("secret-in-code")),
            ApplicationMode.HUMAN_ONLY)

    def test_discover_filters_by_doc_type(self):
        rules = R.discover_criteria(self.dir, DocumentType.CODE, Scope.org())
        self.assertEqual(len(rules), 2)
        spec = R.discover_criteria(self.dir, DocumentType.SPEC, Scope.org())
        self.assertEqual(len(spec), 0)                   # doc_type 不一致は拾わない

    def test_discover_filters_by_scope(self):            # #8：同 doc_type でも別 scope は拾わない
        team = CRITERIA.replace("scope: org", "scope: team:x")
        (self.dir / "team.md").write_text(team, encoding="utf-8")
        rules = R.discover_criteria(self.dir, DocumentType.CODE, Scope.org())
        self.assertEqual(len(rules), 2)                  # org の 2 ルールのみ（team 分は混入しない）
        self.assertTrue(all(r.provenance.inheritance_layer == InheritanceLayer.ORG
                            for r in rules))


if __name__ == "__main__":
    unittest.main()
