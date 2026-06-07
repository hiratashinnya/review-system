"""TC-domain-001: ドメイン基盤の単体テスト（境界値・エッジ含む）。

TDD: 実装(review_system.domain)より先に書いた契約。各 public 値オブジェクト/関数を
壊れた値を作らせないか・境界でどう振る舞うかで検証する。
"""
import unittest
from pathlib import Path

from review_system.domain.enums import DocumentType, Severity, InheritanceLayer
from review_system.domain.ids import (
    RuleId, ContentHash, LineRange, Location, ExecutionId, FindingId, Scope,
)
from review_system.domain.review import TypeEstimation, SuggestedFix, Finding
from review_system.domain.intake import resolve_document_type
from review_system.domain.result import Success, Failure, ok, fail, FailureStage


class TestRuleId(unittest.TestCase):
    def test_valid_and_value_equality(self):            # case 1
        self.assertEqual(RuleId("naming"), RuleId("naming"))
        self.assertEqual(len({RuleId("a"), RuleId("a")}), 1)  # hashable・縮退

    def test_empty_rejected(self):                       # case 2（境界：空）
        with self.assertRaises(ValueError):
            RuleId("")


class TestLineRange(unittest.TestCase):
    def test_lower_bound_single_line(self):              # case 3（境界 start=end=1）
        lr = LineRange(1, 1)
        self.assertEqual((lr.start_line, lr.end_line), (1, 1))

    def test_start_below_one_rejected(self):             # case 4（境界 start=0）
        with self.assertRaises(ValueError):
            LineRange(0, 5)

    def test_end_before_start_rejected(self):            # case 5（エッジ end<start）
        with self.assertRaises(ValueError):
            LineRange(5, 4)

    def test_normal_range(self):                         # case 6
        self.assertEqual(LineRange(1, 100).end_line, 100)


class TestLocation(unittest.TestCase):
    def test_optional_line_range(self):                  # case 7
        loc = Location(Path("a.py"))
        self.assertIsNone(loc.line_range)

    def test_hashable_and_equal(self):                   # case 8（hashable・set 縮退）
        a = Location(Path("a.py"), LineRange(1, 2))
        b = Location(Path("a.py"), LineRange(1, 2))
        self.assertEqual(a, b)
        self.assertEqual(len({a, b}), 1)


class TestScope(unittest.TestCase):
    def test_org_without_name_ok(self):                  # case 9
        self.assertEqual(Scope(InheritanceLayer.ORG).layer, InheritanceLayer.ORG)

    def test_org_with_name_rejected(self):               # case 10（矛盾）
        with self.assertRaises(ValueError):
            Scope(InheritanceLayer.ORG, "x")

    def test_team_without_name_rejected(self):           # case 11（矛盾）
        with self.assertRaises(ValueError):
            Scope(InheritanceLayer.TEAM)

    def test_team_empty_name_rejected(self):             # case 12（エッジ：空名）
        with self.assertRaises(ValueError):
            Scope(InheritanceLayer.TEAM, "")

    def test_org_factory(self):                          # case 13
        s = Scope.org()
        self.assertEqual(s.layer, InheritanceLayer.ORG)
        self.assertIsNone(s.name)


class TestSeverityOrder(unittest.TestCase):
    def test_ordering(self):                             # case 14（IntEnum 比較）
        self.assertGreater(Severity.ERROR, Severity.WARNING)
        self.assertGreater(Severity.WARNING, Severity.INFO)


class TestExecutionId(unittest.TestCase):
    def test_truncates_hash_to_12(self):                 # case 15
        eid = ExecutionId.of("2026-06-07T00:00:00Z", ContentHash("abcdef0123456789"))
        self.assertTrue(eid.value.endswith("-abcdef012345"))

    def test_short_hash_not_truncated(self):             # case 16（エッジ <12）
        eid = ExecutionId.of("T", ContentHash("abc"))
        self.assertEqual(eid.value, "T-abc")


class TestFindingId(unittest.TestCase):
    def test_derived_and_stable(self):                   # case 17
        loc = Location(Path("a.py"), LineRange(1, 2))
        f = Finding(RuleId("naming"), loc, rationale="r")
        self.assertEqual(FindingId.of(f), FindingId.of(f))
        self.assertEqual(FindingId.of(f).rule_id, RuleId("naming"))


class TestResolveDocumentType(unittest.TestCase):
    def test_manual_override_wins(self):                 # case 18（優先）
        r = resolve_document_type(DocumentType.SPEC, TypeEstimation(DocumentType.CODE, 0.9))
        self.assertEqual(r, DocumentType.SPEC)

    def test_estimation_fallback(self):                  # case 19
        r = resolve_document_type(None, TypeEstimation(DocumentType.CODE, 0.9))
        self.assertEqual(r, DocumentType.CODE)

    def test_both_none_returns_none(self):               # case 20（境界：両欠→fail-close 用）
        self.assertIsNone(resolve_document_type(None, None))


class TestResult(unittest.TestCase):
    def test_ok(self):                                   # case 21
        self.assertEqual(ok(42), Success(42))

    def test_fail_and_match(self):                       # case 22
        outcome = fail(FailureStage.INTAKE, "boom", None, "retry")
        match outcome:
            case Failure(notice):
                self.assertEqual(notice.stage, FailureStage.INTAKE)
            case _:
                self.fail("Failure であるべき")


if __name__ == "__main__":
    unittest.main()
