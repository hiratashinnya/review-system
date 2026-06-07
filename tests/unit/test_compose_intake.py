"""TC-compose-001 / TC-intake-001: P2 合成（org最小）と P1 受付の純粋ロジック。"""
import unittest
from pathlib import Path

from review_system.domain.enums import (
    Determinism, Severity, OverrideRule, DocumentType, InheritanceLayer,
)
from review_system.domain.ids import RuleId, Provenance, Scope
from review_system.domain.criteria import RuleMeta, RuleGuidance, ComposedRule
from review_system.domain.review import SourceFile
from review_system.core import compose, intake


def _rule(rid, enabled=True):
    return ComposedRule(
        RuleId(rid), rid,
        RuleGuidance("s", (), (), ()),
        RuleMeta(Determinism.DETERMINISTIC, Severity.ERROR, OverrideRule.TIGHTEN_ONLY, enabled),
        Provenance(Path("criteria/org/code.md"), InheritanceLayer.ORG),
    )


class TestCompose(unittest.TestCase):
    def test_pack_strips_meta_and_maps(self):            # 基本
        pack, meta = compose.build_pack_and_meta((_rule("naming"),))
        self.assertTrue(pack.contains(RuleId("naming")))
        self.assertIsNotNone(meta.get(RuleId("naming")))

    def test_disabled_excluded_from_pack(self):          # エッジ：enabled=False
        pack, meta = compose.build_pack_and_meta((_rule("off", enabled=False),))
        self.assertFalse(pack.contains(RuleId("off")))

    def test_duplicate_id_unioned_keep_first(self):      # エッジ：兄弟 union の同 id
        pack, meta = compose.build_pack_and_meta((_rule("dup"), _rule("dup")))
        self.assertEqual(len(pack.rules), 1)

    def test_empty(self):                                # 境界：空
        pack, meta = compose.build_pack_and_meta(())
        self.assertEqual(len(pack.rules), 0)


class TestIntake(unittest.TestCase):
    def test_target_reference_separation(self):
        t = (SourceFile(Path("a.py"), "x"),)
        r = (SourceFile(Path("ref.py"), "y"),)
        nz = intake.build_intake(t, r, DocumentType.CODE, Scope.org())
        self.assertEqual(nz.target_files, t)
        self.assertEqual(nz.reference_files, r)
        self.assertEqual(nz.document_type, DocumentType.CODE)


if __name__ == "__main__":
    unittest.main()
