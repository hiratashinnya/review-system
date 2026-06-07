"""TC-pipeline-001: P1 通し（FakePlatformAdapter で決定化）。"""
import unittest
from pathlib import Path

from review_system.domain.enums import (
    DocumentType, Determinism, Severity, OverrideRule, ApplicationMode, InheritanceLayer,
)
from review_system.domain.ids import RuleId, Location, LineRange, Provenance, Scope
from review_system.domain.criteria import RuleMeta, RuleGuidance, ComposedRule
from review_system.domain.policy import PolicyMatrix
from review_system.domain.review import SourceFile, Finding, UnmatchedFinding
from review_system.domain.result import Success, Failure
from review_system.ports.platform import ReviewRequest, RawReviewResponse
from review_system.adapters.fake import FakePlatformAdapter
from review_system.core.pipeline import Deps, run_review


def _rule(rid, det):
    return ComposedRule(
        RuleId(rid), rid, RuleGuidance("s", (), (), ()),
        RuleMeta(det, Severity.ERROR, OverrideRule.TIGHTEN_ONLY, True),
        Provenance(Path("criteria/org/code.md"), InheritanceLayer.ORG),
    )


def _loc(f="a.py"):
    return Location(Path(f), LineRange(1, 1))


def _deps(findings, unmatched=(), rules=None, policy=None):
    platform = FakePlatformAdapter(RawReviewResponse(findings, unmatched))
    rules = rules if rules is not None else (
        _rule("naming", Determinism.DETERMINISTIC), _rule("design", Determinism.JUDGMENT),
    )
    policy = policy or PolicyMatrix(
        {Determinism.DETERMINISTIC: {"*": ApplicationMode.AUTO_FIX_LOG_ONLY},
         Determinism.JUDGMENT: {"*": ApplicationMode.HUMAN_ONLY}}, {})
    return Deps(
        platform=platform,
        load_criteria=lambda dt, sc: rules,
        load_policy=lambda sc: policy,
        now=lambda: "2026-06-07T00:00:00Z",
    )


def _request(type_override=DocumentType.CODE, references=()):
    return ReviewRequest(
        targets=(SourceFile(Path("a.py"), "x"),),
        references=references,
        type_override=type_override,
        scope=Scope.org(),
    )


class TestPipeline(unittest.TestCase):
    def test_happy_path_buckets(self):                   # 1
        findings = (
            Finding(RuleId("naming"), _loc(), "r"),       # → auto
            Finding(RuleId("design"), _loc(), "r"),       # → judge
            Finding(RuleId("ghost"), _loc(), "r"),        # → unclassified (S1)
        )
        out = run_review(_request(), _deps(findings))
        self.assertIsInstance(out, Success)
        rep = out.value
        self.assertEqual((len(rep.auto), len(rep.judge), len(rep.unclassified)), (1, 1, 1))

    def test_version_stamp(self):                        # 2
        out = run_review(_request(), _deps((Finding(RuleId("naming"), _loc(), "r"),)))
        self.assertTrue(out.value.stamp.execution_id.value)
        self.assertTrue(out.value.stamp.criteria_content_hash.value)

    def test_conservation(self):                         # 3
        findings = tuple(Finding(RuleId("naming"), _loc(), "r") for _ in range(3))
        rep = run_review(_request(), _deps(findings)).value
        total = len(rep.auto) + len(rep.approve) + len(rep.judge) + len(rep.unclassified)
        self.assertEqual(total, 3)

    def test_no_type_fail_close(self):                   # 4（境界）
        out = run_review(_request(type_override=None), _deps(()))
        self.assertIsInstance(out, Failure)

    def test_empty_criteria_fail_close(self):            # 5（境界）
        out = run_review(_request(), _deps((), rules=()))
        self.assertIsInstance(out, Failure)

    def test_reference_excluded(self):                   # 6
        findings = (Finding(RuleId("naming"), _loc("ref.py"), "r"),)
        req = _request(references=(SourceFile(Path("ref.py"), "y"),))
        rep = run_review(req, _deps(findings)).value
        self.assertEqual(len(rep.auto), 0)               # 参照のパスは除外


if __name__ == "__main__":
    unittest.main()
