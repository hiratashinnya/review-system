"""TC-triage-001: P4 検証・参照除外・仕分け（S1 取りこぼしゼロ・S2 安全側）。"""
import unittest
from pathlib import Path

from review_system.domain.enums import (
    Determinism, Severity, OverrideRule, ApplicationMode, TriageBucket,
)
from review_system.domain.ids import RuleId, Location, LineRange, Provenance
from review_system.domain.enums import InheritanceLayer
from review_system.domain.review import Finding
from review_system.domain.criteria import RuleMeta, MetaIndex, PackedRule, CriteriaPack, RuleGuidance
from review_system.domain.policy import PolicyMatrix
from review_system.core import triage as T


def _pack(*ids):
    g = RuleGuidance("s", (), (), ())
    return CriteriaPack(tuple(PackedRule(RuleId(i), i, g) for i in ids))


def _finding(rule_id, file="a.py"):
    return Finding(RuleId(rule_id), Location(Path(file), LineRange(1, 1)), rationale="r")


def _meta(determinism, severity=Severity.ERROR):
    return RuleMeta(determinism, severity, OverrideRule.TIGHTEN_ONLY, True)


class TestValidate(unittest.TestCase):
    def test_known_rule_id_valid(self):                  # 1
        valid, unc = T.validate((_finding("naming"),), _pack("naming"))
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(unc), 0)

    def test_unknown_rule_id_to_unclassified(self):      # 2（S1）
        valid, unc = T.validate((_finding("ghost"),), _pack("naming"))
        self.assertEqual(len(valid), 0)
        self.assertEqual(len(unc), 1)

    def test_conservation(self):                         # 3（保存則）
        findings = (_finding("naming"), _finding("ghost"), _finding("naming"))
        valid, unc = T.validate(findings, _pack("naming"))
        self.assertEqual(len(valid) + len(unc), len(findings))


class TestExcludeReference(unittest.TestCase):
    def test_reference_dropped(self):                    # 4
        kept = T.exclude_reference((_finding("naming", "ref.py"),), {Path("ref.py")})
        self.assertEqual(len(kept), 0)

    def test_same_name_other_dir_kept(self):             # 5（エッジ）
        kept = T.exclude_reference((_finding("naming", "src/a.py"),), {Path("ref/a.py")})
        self.assertEqual(len(kept), 1)


class TestTriage(unittest.TestCase):
    def _policy(self, mapping=None, overrides=None):
        wrapped = {det: {"*": mode} for det, mode in (mapping or {}).items()}
        return PolicyMatrix(wrapped, overrides or {})

    def test_deterministic_auto(self):                   # 6
        idx = MetaIndex({RuleId("naming"): _meta(Determinism.DETERMINISTIC)})
        pol = self._policy({Determinism.DETERMINISTIC: ApplicationMode.AUTO_FIX_LOG_ONLY})
        res = T.triage((_finding("naming"),), idx, pol)
        self.assertEqual(len(res.auto), 1)
        self.assertEqual(res.auto[0].bucket, TriageBucket.AUTO)

    def test_tradeoff_suggest(self):                     # 7
        idx = MetaIndex({RuleId("x"): _meta(Determinism.TRADEOFF)})
        pol = self._policy({Determinism.TRADEOFF: ApplicationMode.AUTO_FIX_SUGGEST})
        res = T.triage((_finding("x"),), idx, pol)
        self.assertEqual(len(res.approve), 1)

    def test_judgment_human(self):                       # 8
        idx = MetaIndex({RuleId("x"): _meta(Determinism.JUDGMENT)})
        pol = self._policy({Determinism.JUDGMENT: ApplicationMode.HUMAN_ONLY})
        res = T.triage((_finding("x"),), idx, pol)
        self.assertEqual(len(res.judge), 1)

    def test_missing_meta_defaults_human(self):          # 9（S2）
        idx = MetaIndex({})                              # メタ無し
        pol = self._policy({Determinism.DETERMINISTIC: ApplicationMode.AUTO_FIX_LOG_ONLY})
        res = T.triage((_finding("x"),), idx, pol)
        self.assertEqual(len(res.auto), 0)               # 🤖 にしない
        self.assertEqual(len(res.judge), 1)

    def test_missing_matrix_entry_defaults_human(self):  # 10（S2）
        idx = MetaIndex({RuleId("x"): _meta(Determinism.DETERMINISTIC)})
        pol = self._policy({})                           # matrix 欠落
        res = T.triage((_finding("x"),), idx, pol)
        self.assertEqual(len(res.auto), 0)
        self.assertEqual(len(res.judge), 1)

    def test_override_wins(self):                        # 11
        idx = MetaIndex({RuleId("x"): _meta(Determinism.DETERMINISTIC)})
        pol = self._policy(
            {Determinism.DETERMINISTIC: ApplicationMode.AUTO_FIX_LOG_ONLY},
            {RuleId("x"): ApplicationMode.HUMAN_ONLY},
        )
        res = T.triage((_finding("x"),), idx, pol)
        self.assertEqual(len(res.judge), 1)


if __name__ == "__main__":
    unittest.main()
