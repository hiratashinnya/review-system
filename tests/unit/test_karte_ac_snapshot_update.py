"""Issue #801: dispatch AC snapshot / ownerチェック更新の衝突とfail-close。"""

import unittest
from types import SimpleNamespace

from karte.ac_snapshot import digest, from_issue_body
from karte.ac_check_update import plan, verify_written
from karte.errors import KarteUsageError
from karte.format_error import KarteFormatError

BODY = """# Issue

## Acceptance criteria
- [ ] AC1 動作する
- [ ] AC2 未検証
- [x] AC3 充足済み

## Other
- [ ] unrelated
"""


def judge(*results):
    return [SimpleNamespace(number=i, result=r) for i, r in enumerate(results, 1)]


class ACSnapshotUpdateTest(unittest.TestCase):
    def test_snapshot_digest_changes_on_ac_text_and_checked_state(self):
        before = from_issue_body(BODY)
        self.assertEqual(len(before), 3)
        self.assertNotEqual(digest(before), digest(from_issue_body(BODY.replace("AC1 動作する", "AC1 改訂"))))
        self.assertNotEqual(digest(before), digest(from_issue_body(BODY.replace("[ ] AC1", "[x] AC1"))))

    def test_only_satisfied_ac_is_checked_and_unrelated_edit_survives(self):
        live = BODY.replace("# Issue", "# Owner edited issue")
        updated, changed = plan(BODY, live, judge("satisfied", "unverified", "satisfied"))
        self.assertEqual(changed, [1])
        self.assertIn("- [x] AC1 動作する", updated)
        self.assertIn("- [ ] AC2 未検証", updated)
        self.assertIn("- [ ] unrelated", updated)
        self.assertIn("# Owner edited issue", updated)
        verify_written(updated, updated)

    def test_stale_text_or_check_state_fail_closed(self):
        for live in (BODY.replace("AC1 動作する", "AC1 仕様変更"), BODY.replace("[ ] AC1", "[x] AC1")):
            with self.subTest(live=live), self.assertRaises(KarteUsageError):
                plan(BODY, live, judge("satisfied", "unverified", "satisfied"))

    def test_checked_ac_regression_requires_owner(self):
        with self.assertRaisesRegex(KarteUsageError, "オーナー判断"):
            plan(BODY, BODY, judge("satisfied", "unverified", "not_met"))

    def test_malformed_judgment_or_readback_rejected(self):
        for judgments in (judge("satisfied", "unverified"), judge("satisfied", "invalid", "satisfied")):
            with self.subTest(judgments=judgments), self.assertRaises(KarteUsageError):
                plan(BODY, BODY, judgments)
        with self.assertRaises(KarteUsageError):
            verify_written("before", "after")

    def test_no_ac_and_noncheckbox_remain_unchanged(self):
        original = "# t\n## Acceptance criteria\n- Plain prose AC\n"
        items = from_issue_body(original)
        self.assertEqual([i.checked for i in items], [None])
        self.assertEqual((original, []), plan(original, original, judge("satisfied")))
        self.assertEqual((), from_issue_body("# no AC\n"))

    def test_duplicate_ac_rejected(self):
        with self.assertRaises(KarteFormatError):
            from_issue_body(BODY.replace("- [ ] AC2 未検証", "- [ ] AC1 動作する"))


if __name__ == "__main__":
    unittest.main()
