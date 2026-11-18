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

    def test_four_space_indented_code_does_not_hide_real_ac(self):
        body = ("# Issue\n\n    ```\n    sample\n\n"
                "## Acceptance criteria\n- [ ] real condition\n")
        items = from_issue_body(body)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].text, "real condition")
        updated, changed = plan(body, body, judge("satisfied"))
        self.assertEqual(changed, [1])
        self.assertIn("    ```", updated)
        self.assertIn("- [x] real condition", updated)
        self.assertNotEqual(digest(items), digest(from_issue_body(
            body.replace("real condition", "changed condition"))))

    def test_indented_code_pseudo_heading_does_not_steal_ac(self):
        body = ("# Issue\n\n    ## Acceptance criteria\n"
                "    - [ ] fake example\n\n"
                "## Acceptance criteria\n- [ ] actual condition\n")
        items = from_issue_body(body)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].text, "actual condition")
        updated, changed = plan(body, body, judge("satisfied"))
        self.assertEqual(changed, [1])
        self.assertIn("    - [ ] fake example", updated)
        self.assertIn("- [x] actual condition", updated)

    def test_fenced_example_outside_ac_cannot_become_real_ac(self):
        body = ("# Issue\n"
                "Code sample:\n"
                "```markdown\n"
                "## Acceptance criteria\n- [ ] fake example\n"
                "```\n\n"
                "## Acceptance criteria\n- [ ] real condition\n"
                "## Other\n")
        items = from_issue_body(body)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].text, "real condition")
        updated, changed = plan(body, body, judge("satisfied"))
        self.assertEqual(changed, [1])
        self.assertIn("- [ ] fake example", updated)
        self.assertIn("- [x] real condition", updated)
        self.assertNotEqual(digest(items), digest(from_issue_body(
            body.replace("real condition", "new real condition"))))

    def test_setext_headings_are_real_ac_not_zero_in_english_and_japanese(self):
        for label in ("Acceptance criteria", "受け入れ基準"):
            for underline in ("-------------", "============="):
                with self.subTest(label=label, underline=underline):
                    body = label + "\n" + underline + "\n- [ ] real condition\n"
                    criteria = from_issue_body(body)
                    self.assertEqual(len(criteria), 1)
                    self.assertEqual(criteria[0].text, "real condition")
                    changed = body.replace("real condition", "changed condition")
                    self.assertNotEqual(digest(criteria), digest(from_issue_body(changed)))
                    with self.assertRaisesRegex(KarteUsageError, "live本文"):
                        plan(body, changed, judge("satisfied"))
                    updated, indexes = plan(body, body, judge("satisfied"))
                    self.assertEqual(indexes, [1])
                    self.assertIn("- [x] real condition", updated)

    def test_setext_end_heading_excludes_checkbox_outside_ac(self):
        cases = (
            ("## Acceptance criteria", "Notes\n-----"),
            ("## Acceptance criteria", "Notes\n====="),
            ("Acceptance criteria\n-----", "Notes\n-----"),
            ("Acceptance criteria\n=====", "Notes\n-----"),
            ("## 受け入れ基準", "メモ\n-----"),
            ("受け入れ基準\n=====", "メモ\n====="),
            ("## Acceptance criteria", "## Notes"),
        )
        for begin, end in cases:
            with self.subTest(begin=begin, end=end):
                body = begin + "\n- [ ] real AC\n\n" + end + "\n- [ ] example\n"
                criteria = from_issue_body(body)
                self.assertEqual(1, len(criteria))
                self.assertEqual("real AC", criteria[0].text)
                self.assertEqual(
                    digest(criteria),
                    digest(from_issue_body(body.replace("example", "edited example"))),
                )
                self.assertNotEqual(
                    digest(criteria),
                    digest(from_issue_body(body.replace("real AC", "updated AC"))),
                )
                updated, changed = plan(body, body, judge("satisfied"))
                self.assertEqual([1], changed)
                self.assertIn("- [x] real AC", updated)
                self.assertIn("- [ ] example", updated)

    def test_indented_code_checkbox_is_not_an_ac_or_checkbox_update(self):
        for code_prefix in ("    ", "\t"):
            with self.subTest(prefix=repr(code_prefix)):
                body = ("## Acceptance criteria\n\n" +
                        code_prefix + "- [ ] example\n\n- [ ] real AC\n")
                items = from_issue_body(body)
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0].text, "real AC")
                updated, changed = plan(body, body, judge("satisfied"))
                self.assertEqual(changed, [1])
                self.assertIn(code_prefix + "- [ ] example", updated)
                self.assertIn("- [x] real AC", updated)
                self.assertNotEqual(digest(items), digest(from_issue_body(
                    body.replace("real AC", "changed AC"))))

    def test_closed_hash_atx_ac_headings_in_both_languages(self):
        for heading in ("## Acceptance criteria ##", "## 受け入れ基準 ##"):
            with self.subTest(heading=heading):
                body = heading + "\n- [ ] real condition\n"
                items = from_issue_body(body)
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0].text, "real condition")
                self.assertNotEqual(digest(items), digest(from_issue_body(
                    body.replace("real condition", "changed condition"))))
                updated, changed = plan(body, body, judge("satisfied"))
                self.assertEqual(changed, [1])
                self.assertIn("- [x] real condition", updated)

    def test_nested_heading_does_not_end_ac_section_or_lose_following_checkbox(self):
        body = ("## Acceptance criteria\n- [ ] AC1\n"
                "  ## Details\n  details\n- [ ] AC2\n")
        items = from_issue_body(body)
        self.assertEqual(len(items), 2)
        self.assertIn("## Details", items[0].text)
        self.assertEqual(items[1].text, "AC2")
        modified = body.replace("- [ ] AC2", "- [ ] AC2 modified")
        self.assertNotEqual(digest(items), digest(from_issue_body(modified)))
        with self.assertRaisesRegex(KarteUsageError, "live本文"):
            plan(body, modified, judge("satisfied", "satisfied"))
        updated, changed = plan(body, body, judge("satisfied", "satisfied"))
        self.assertEqual(changed, [1, 2])
        self.assertIn("- [x] AC1", updated)
        self.assertIn("- [x] AC2", updated)

    def test_four_space_closer_does_not_close_outer_fence(self):
        body = ("# Issue\n ```text\n"
                "    ```\n## Acceptance criteria\n- [ ] fake AC\n"
                "```\n## Acceptance criteria\n- [ ] real AC\n")
        items = from_issue_body(body)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].text, "real AC")
        updated, changed = plan(body, body, judge("satisfied"))
        self.assertEqual(changed, [1])
        self.assertIn("- [ ] fake AC", updated)
        self.assertIn("- [x] real AC", updated)

    def test_six_space_indented_code_is_not_list_fence(self):
        body = ("## Acceptance criteria\n- [ ] AC1\n"
                "      ```\n      sample\n- [ ] AC2\n")
        items = from_issue_body(body)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[1].text, "AC2")
        self.assertNotEqual(digest(items), digest(from_issue_body(
            body.replace("- [ ] AC2", "- [ ] AC2 changed"))))
        updated, changed = plan(body, body, judge("satisfied", "satisfied"))
        self.assertEqual(changed, [1, 2])
        self.assertIn("- [x] AC2", updated)

    def test_fence_info_string_does_not_close_and_hide_next_ac(self):
        body = ("## Acceptance criteria\n"
                "- [ ] AC1\n"
                "    ```markdown\n"
                "    ```not-a-closing-fence\n"
                "    ## Other\n"
                "    - [ ] fake checkbox in code\n"
                "    ```\n"
                "- [ ] AC2\n"
                "## Other\n")
        items = from_issue_body(body)
        self.assertEqual(len(items), 2)
        self.assertIn("## Other", items[0].text)
        self.assertIn("fake checkbox", items[0].text)
        self.assertEqual(items[1].text, "AC2")
        self.assertNotEqual(digest(items), digest(from_issue_body(
            body.replace("- [ ] AC2", "- [ ] AC2 changed"))))
        with self.assertRaisesRegex(KarteUsageError, "live本文"):
            plan(body, body.replace("AC2\n", "AC2 changed\n"),
                 judge("satisfied", "satisfied"))
        updated, changed = plan(body, body, judge("satisfied", "satisfied"))
        self.assertEqual(changed, [1, 2])
        self.assertIn("- [ ] fake checkbox in code", updated)
        self.assertIn("- [x] AC2", updated)

    def test_paragraph_form_ac_is_preserved_and_bound_to_digest(self):
        prose = ("# Example\n## Acceptance criteria\n"
                 "実環境での動作確認に成功すること。\n"
                 "操作条件: 電源投入後に確認する。\n\n"
                 "異常時には安全側へ移行すること。\n\n## Notes\n"
                 "一般情報はACではない。\n")
        criteria = from_issue_body(prose)
        self.assertEqual(len(criteria), 2)
        self.assertEqual([item.checked for item in criteria], [None, None])
        self.assertIn("操作条件", criteria[0].text)
        self.assertIn("安全側", criteria[1].text)
        self.assertNotIn("一般情報", "".join(item.text for item in criteria))
        changed = prose.replace("電源投入後", "再起動後")
        self.assertNotEqual(digest(criteria), digest(from_issue_body(changed)))
        with self.assertRaisesRegex(KarteUsageError, "live本文"):
            plan(prose, changed, judge("satisfied", "satisfied"))
        self.assertEqual(plan(prose, prose, judge("satisfied", "satisfied")), (prose, []))

    def test_prose_before_bullets_is_not_silently_dropped(self):
        body = ("## Acceptance criteria\n実環境で確認すること。\n"
                "- [ ] テストが成功する\n")
        items = from_issue_body(body)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].checked, None)
        self.assertEqual(items[1].checked, False)
        self.assertNotEqual(digest(items), digest(from_issue_body(
            body.replace("実環境", "シミュレータ"))))

    def test_multiline_ac_continuation_is_bound_to_snapshot_and_live(self):
        multiline = """# Test

## Acceptance criteria
- [ ] AC1 通常動作
    続き: 実環境での検証も必要
    - [ ] 子条件A
    - [ ] 子条件B

    ```text
    - [ ] コード中の擬似条件
    ```
- [ ] AC2 単独条件

## Notes
- [ ] ACと無関係
"""
        ac = from_issue_body(multiline)
        self.assertEqual(len(ac), 2)
        self.assertIn("続き: 実環境での検証も必要", ac[0].text)
        self.assertIn("子条件B", ac[0].text)
        self.assertIn("コード中の擬似条件", ac[0].text)
        changed = multiline.replace("子条件B", "子条件C")
        self.assertNotEqual(digest(ac), digest(from_issue_body(changed)))
        with self.assertRaisesRegex(KarteUsageError, "live本文"):
            plan(multiline, changed, judge("satisfied", "satisfied"))
        updated, changed_numbers = plan(multiline, multiline, judge("satisfied", "satisfied"))
        self.assertEqual(changed_numbers, [1, 2])
        self.assertIn("子条件B", updated)
        self.assertIn("コード中の擬似条件", updated)
        self.assertEqual(
            updated.replace("- [x] AC1", "- [ ] AC1").replace("- [x] AC2", "- [ ] AC2"),
            multiline,
        )

    def test_multiline_snapshot_changes_when_continuation_only_changed(self):
        body = "## Acceptance criteria\n- [ ] A\n  - nested evidence\n"
        self.assertNotEqual(
            digest(from_issue_body(body)),
            digest(from_issue_body(body.replace("nested evidence", "nested missing"))),
        )

    def test_duplicate_ac_rejected(self):
        with self.assertRaises(KarteFormatError):
            from_issue_body(BODY.replace("- [ ] AC2 未検証", "- [ ] AC1 動作する"))


if __name__ == "__main__":
    unittest.main()
