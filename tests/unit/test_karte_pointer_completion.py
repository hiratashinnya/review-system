"""``karte.pointer_completion``：``--issue`` / ``--round`` の補完と、``ingest-review`` の拒否の無副作用・優先順位。

拒否の優先順位は issue→round→本文（origin/main と同じ）。何も作らずに拒否できるのは、ロックの前
（``prepare`` 段）で拒否できる引数・ポインタ・本文由来の範囲に限る。ロックを取ったあとの拒否
（内容検証・台帳との突き合わせ・ロック内での読み直し）は、新規 repo でも ``tmp/_karte/`` と
``.writer.lock`` を残す（台帳は書かない）。
"""

import io
import unittest
from unittest import mock

from karte import exit_codes, pointer_completion
from karte.errors import KarteUsageError
from karte.round_resolution import MissingRoundHint, ResolvedRound
from tests.unit.karte_support import (
    HUGE, RootedCase, finding, ingest_argv, report_text, rooted_args,
)

_HINT = MissingRoundHint.FIRST_INGEST


class _RootedCase(RootedCase):
    prefix = "karte-pc-"

    def _args(self, **kwargs):
        return rooted_args(self.root, **kwargs)


class TestRoundCompletion(_RootedCase):
    def test_non_ascii_round_is_a_usage_error(self):
        with self.assertRaises(KarteUsageError):
            pointer_completion.resolve_round(self._args(issue="1", round="²"), self.root, 1, _HINT)

    def test_explicit_round_does_not_read_the_pointer(self):
        resolved = pointer_completion.resolve_round(
            self._args(issue="1", round="5"), self.root, 1, _HINT
        )
        self.assertEqual(ResolvedRound(5, explicit=True), resolved)
        self.assertFalse((self.root / "tmp" / "_karte").exists())

    def test_pointer_round_is_used_as_is(self):
        self.write_pointer('{"issue": 7, "round": 3}\n')
        resolved = pointer_completion.resolve_round(self._args(round=None), self.root, 7, _HINT)
        self.assertEqual(ResolvedRound(3, explicit=False), resolved)

    def test_missing_pointer_round_is_refused_with_the_callers_hint(self):
        self.write_pointer('{"issue": 7}\n')
        for hint in MissingRoundHint:
            with self.subTest(hint=hint.name), self.assertRaises(KarteUsageError) as caught:
                pointer_completion.resolve_round(self._args(round=None), self.root, 7, hint)
            self.assertIn(hint.value, str(caught.exception))

    def test_ingest_target_adds_one_to_the_pointer_round_only_when_it_completes_it(self):
        self.write_pointer('{"issue": 7, "round": 3}\n')
        self.assertEqual(
            (7, 4), pointer_completion.ingest_target(self._args(issue=None, round=None), self.root)
        )
        self.assertEqual(
            (7, 3),
            pointer_completion.ingest_target(self._args(issue="7", round="3"), self.root),
        )

    def test_pointer_round_zero_completes_ingest_target_to_round_one(self):
        self.write_pointer('{"issue": 7, "round": 0}\n')
        self.assertEqual(
            (7, 1), pointer_completion.ingest_target(self._args(issue="7", round=None), self.root)
        )
        with self.assertRaises(KarteUsageError):
            pointer_completion.resolve_round(self._args(round=None), self.root, 7, _HINT)


class TestRecordedRound(unittest.TestCase):
    """``append`` の補完と ``render`` の見出しが共有する、ポインタの記録ラウンドの読み方（R5-02/R5-03）。"""

    def test_a_round_recorded_for_the_same_issue_is_returned(self):
        self.assertEqual(3, pointer_completion.recorded_round({"issue": 7, "round": 3}, 7))
        self.assertEqual(3, pointer_completion.recorded_round({"issue": 7, "round": "3"}, 7))

    def test_it_degrades_to_none_for_another_issue_or_a_falsy_round(self):
        cases = {
            "other issue": {"issue": 8, "round": 3},
            "issue as string": {"issue": "7", "round": 3},
            "no issue": {"round": 3},
            "no round": {"issue": 7},
            "zero": {"issue": 7, "round": 0},
            "null": {"issue": 7, "round": None},
            "empty string": {"issue": 7, "round": ""},
            "false": {"issue": 7, "round": False},
            "other issue with a garbage round": {"issue": 8, "round": "abc"},
        }
        for name, active in cases.items():
            with self.subTest(case=name):
                self.assertIsNone(pointer_completion.recorded_round(active, 7))
        self.assertIsNone(pointer_completion.recorded_round({}, 7))

    def test_a_truthy_round_that_is_not_a_positive_ascii_integer_is_refused(self):
        for value in ("²", "abc", "0", "-1", [1], {"a": 1}, True, float("nan"), 1.5, HUGE, "5\n"):
            with self.subTest(value=str(value)[:10]), self.assertRaises(KarteUsageError):
                pointer_completion.recorded_round({"issue": 7, "round": value}, 7)


class TestIngestRefusalsHaveNoSideEffect(_RootedCase):
    """引数・ポインタ・本文由来の拒否は、ロック用ファイルもディレクトリも作らない（挙動不変）。"""

    def _assert_refused_without_side_effect(self, issue=None, round_no=None):
        code, _out, err = self.run_verb(ingest_argv(issue, round_no), "### new\n")
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertFalse((self.root / "tmp" / "_karte" / ".writer.lock").exists())
        self.assertFalse((self.root / "tmp" / "_karte" / "issue-7.md").exists())
        return err

    def test_missing_pointer_creates_nothing(self):
        self._assert_refused_without_side_effect()
        self.assertFalse((self.root / "tmp" / "_karte").exists())

    def test_pointer_failures_create_no_lock_file(self):
        cases = {
            "broken": "{ not json",
            "not-an-object": "[]",
            "no-issue": '{"round": 2}',
            "no-round": '{"issue": 7}',
            "negative-round": '{"issue": 7, "round": -1}',
            "boolean-round": '{"issue": 7, "round": false}',
            "huge-round": '{"issue": 7, "round": "' + HUGE + '"}',
            "non-ascii-round": '{"issue": 7, "round": "²"}',
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                self.write_pointer(text)
                self._assert_refused_without_side_effect()

    def test_pointer_round_zero_allows_ingestion_as_round_one(self):
        self.write_pointer('{"issue": 7, "round": 0}')
        report = report_text(("new", finding("a.py::f", "検証が不足")))
        code, _out, err = self.run_verb(ingest_argv(), report)
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        self.assertEqual([1], self.ledger().findings[0].rounds)

    def test_pointer_pointing_at_another_issue_creates_no_lock_file(self):
        self.write_pointer('{"issue": 999, "round": 4}')
        err = self._assert_refused_without_side_effect(issue=7)
        self.assertIn("食い違う", err)

    def test_bad_explicit_arguments_create_nothing(self):
        for kwargs in (
            {"issue": "abc", "round_no": "1"},
            {"issue": "7", "round_no": "²"},
            {"issue": "7", "round_no": HUGE},
            {"issue": "7", "round_no": "0"},
        ):
            with self.subTest(**{k: v[:10] for k, v in kwargs.items()}):
                self._assert_refused_without_side_effect(**kwargs)
                self.assertFalse((self.root / "tmp" / "_karte").exists())


class TestRefusalInsideTheLockLeavesTheLockFile(_RootedCase):
    """``prepare`` 段を通ったあとの拒否は、ロック用ファイルとディレクトリを残す（台帳は書かない）。"""

    def test_report_content_refusal_in_a_fresh_repo_leaves_the_lock_file(self):
        invalid = report_text(("new", {**finding("a.py::f", "s"), "harm": ""}))
        code, _out, err = self.run_verb(ingest_argv(7, 1), invalid)
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertTrue((self.root / "tmp" / "_karte" / ".writer.lock").exists())
        self.assertFalse((self.root / "tmp" / "_karte" / "issue-7.md").exists())


class TestIngestRefusalOrder(_RootedCase):
    """拒否の優先順位は issue→round→本文。先に拒否される場合は標準入力を読まない。"""

    class _Unreadable(io.StringIO):
        def read(self, size: int | None = -1) -> str:
            raise AssertionError("標準入力を読んではならない")

    def _err_of(self, stdin=None, issue=None, round_no=None):
        code, _out, err = self.run_verb(ingest_argv(issue, round_no), stdin or self._Unreadable())
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        return err

    def test_issue_is_refused_before_round(self):
        self.assertIn("issue", self._err_of(issue="abc", round_no="²"))

    def test_round_is_refused_before_the_body_is_read(self):
        self.assertIn("round", self._err_of(issue="7", round_no="²"))

    def test_broken_pointer_is_refused_before_stdin_is_read(self):
        self.write_pointer("{ not json")
        self.assertIn("壊れている", self._err_of())

    def test_both_invalid_reports_the_pointer_not_the_empty_body(self):
        self.write_pointer("{ not json")
        err = self._err_of(stdin=io.StringIO(""))
        self.assertIn("壊れている", err)
        self.assertNotIn("空", err)

    def test_valid_arguments_then_an_empty_body_is_the_body_refusal(self):
        err = self._err_of(stdin=io.StringIO(""), issue="7", round_no="1")
        self.assertIn("空", err)
        self.assertFalse((self.root / "tmp" / "_karte").exists())


class TestPointerIsReadAgainInsideTheLock(_RootedCase):
    """ロック前の検証値は捨て、ポインタ由来の値はロック内で読み直した値だけが正（L-6 を保つ）。"""

    def test_the_value_resolved_inside_the_lock_is_the_one_used(self):
        self.write_pointer('{"issue": 7, "round": 1}')
        real = pointer_completion.ingest_target
        resolved, ingested = [], []

        def advance_after_the_first(args, repo_root):
            result = real(args, repo_root)
            resolved.append(result)
            if len(resolved) == 1:  # ロック前の検証の直後に、並行 ingest がポインタを進める
                self.write_pointer('{"issue": 7, "round": 5}')
            return result

        with mock.patch.object(
            pointer_completion, "ingest_target", side_effect=advance_after_the_first
        ), mock.patch(
            "karte.ingest_review.ingest_locked",
            side_effect=lambda root, issue, round_no, text: ingested.append((issue, round_no)) or 0,
        ):
            code, _out, err = self.run_verb(ingest_argv(), "### new\n")
        self.assertEqual(0, code, err)
        self.assertEqual([(7, 2), (7, 6)], resolved)
        self.assertEqual([(7, 6)], ingested)


if __name__ == "__main__":
    unittest.main()
