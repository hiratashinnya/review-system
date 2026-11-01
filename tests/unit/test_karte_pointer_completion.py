"""``karte.pointer_completion``：``--issue`` / ``--round`` の補完と、``ingest-review`` の拒否の無副作用・優先順位。

拒否の優先順位は issue→round→本文（origin/main と同じ）で、引数・ポインタ・本文由来の拒否は
``tmp/_karte/.writer.lock`` を作らない。
"""

import argparse
import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from karte import cli, exit_codes, paths, pointer_completion
from karte.errors import KarteUsageError
from karte.round_resolution import MissingRoundHint, ResolvedRound

_HINT = MissingRoundHint.FIRST_INGEST


class _RootedCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="karte-pc-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        (self.root / "tmp").mkdir()

    def _args(self, **kwargs):
        return argparse.Namespace(repo_root=str(self.root), **kwargs)

    def _write_pointer(self, text):
        paths.active_path(self.root, create_dir=True).write_text(text, encoding="utf-8")


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
        self._write_pointer('{"issue": 7, "round": 3}\n')
        resolved = pointer_completion.resolve_round(self._args(round=None), self.root, 7, _HINT)
        self.assertEqual(ResolvedRound(3, explicit=False), resolved)

    def test_missing_pointer_round_is_refused_with_the_callers_hint(self):
        self._write_pointer('{"issue": 7}\n')
        for hint in MissingRoundHint:
            with self.subTest(hint=hint.name), self.assertRaises(KarteUsageError) as caught:
                pointer_completion.resolve_round(self._args(round=None), self.root, 7, hint)
            self.assertIn(hint.value, str(caught.exception))

    def test_ingest_target_adds_one_to_the_pointer_round_only_when_it_completes_it(self):
        self._write_pointer('{"issue": 7, "round": 3}\n')
        self.assertEqual(
            (7, 4), pointer_completion.ingest_target(self._args(issue=None, round=None), self.root)
        )
        self.assertEqual(
            (7, 3),
            pointer_completion.ingest_target(self._args(issue="7", round="3"), self.root),
        )

    def test_pointer_round_zero_is_rejected_by_ingest_target_as_before(self):
        self._write_pointer('{"issue": 7, "round": 0}\n')
        with self.assertRaises(KarteUsageError):
            pointer_completion.ingest_target(self._args(issue="7", round=None), self.root)


class TestIngestRefusalsHaveNoSideEffect(_RootedCase):
    """引数・ポインタ・本文由来の拒否は、ロック用ファイルもディレクトリも作らない（挙動不変）。"""

    def _ingest(self, **kwargs):
        with contextlib.redirect_stderr(io.StringIO()) as err, mock.patch(
            "sys.stdin", io.StringIO("### new\n")
        ):
            code = cli.cmd_ingest_review(self._args(**kwargs))
        return code, err.getvalue()

    def _assert_refused_without_side_effect(self, **kwargs):
        code, err = self._ingest(**kwargs)
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertFalse((self.root / "tmp" / "_karte" / ".writer.lock").exists())
        self.assertFalse((self.root / "tmp" / "_karte" / "issue-7.md").exists())
        return err

    def test_missing_pointer_creates_nothing(self):
        self._assert_refused_without_side_effect(issue=None, round=None, source="-")
        self.assertFalse((self.root / "tmp" / "_karte").exists())

    def test_pointer_failures_create_no_lock_file(self):
        cases = {
            "broken": "{ not json",
            "not-an-object": "[]",
            "no-issue": '{"round": 2}',
            "no-round": '{"issue": 7}',
            "zero-round": '{"issue": 7, "round": 0}',
            "non-ascii-round": '{"issue": 7, "round": "²"}',
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                self._write_pointer(text)
                self._assert_refused_without_side_effect(issue=None, round=None, source="-")

    def test_pointer_pointing_at_another_issue_creates_no_lock_file(self):
        self._write_pointer('{"issue": 999, "round": 4}')
        err = self._assert_refused_without_side_effect(issue="7", round=None, source="-")
        self.assertIn("食い違う", err)

    def test_bad_explicit_arguments_create_nothing(self):
        for kwargs in (
            {"issue": "abc", "round": "1"},
            {"issue": "7", "round": "²"},
            {"issue": "7", "round": "9" * 6000},
            {"issue": "7", "round": "0"},
        ):
            with self.subTest(**{k: v[:10] for k, v in kwargs.items()}):
                self._assert_refused_without_side_effect(source="-", **kwargs)
                self.assertFalse((self.root / "tmp" / "_karte").exists())


class TestIngestRefusalOrder(_RootedCase):
    """拒否の優先順位は issue→round→本文。先に拒否される場合は標準入力を読まない。"""

    class _Unreadable:
        def read(self):
            raise AssertionError("標準入力を読んではならない")

    def _err_of(self, stdin=None, **kwargs):
        with contextlib.redirect_stderr(io.StringIO()) as err, mock.patch(
            "sys.stdin", stdin or self._Unreadable()
        ):
            code = cli.cmd_ingest_review(self._args(source="-", **kwargs))
        self.assertEqual(exit_codes.EXIT_ERROR, code)
        return err.getvalue()

    def test_issue_is_refused_before_round(self):
        self.assertIn("issue", self._err_of(issue="abc", round="²"))

    def test_round_is_refused_before_the_body_is_read(self):
        self.assertIn("round", self._err_of(issue="7", round="²"))

    def test_broken_pointer_is_refused_before_stdin_is_read(self):
        self._write_pointer("{ not json")
        self.assertIn("壊れている", self._err_of(issue=None, round=None))

    def test_both_invalid_reports_the_pointer_not_the_empty_body(self):
        self._write_pointer("{ not json")
        err = self._err_of(stdin=io.StringIO(""), issue=None, round=None)
        self.assertIn("壊れている", err)
        self.assertNotIn("空", err)

    def test_valid_arguments_then_an_empty_body_is_the_body_refusal(self):
        err = self._err_of(stdin=io.StringIO(""), issue="7", round="1")
        self.assertIn("空", err)
        self.assertFalse((self.root / "tmp" / "_karte").exists())


class TestPointerIsReadAgainInsideTheLock(_RootedCase):
    """ロック前の検証値は捨て、ポインタ由来の値はロック内で読み直した値だけが正（L-6 を保つ）。"""

    def test_the_value_resolved_inside_the_lock_is_the_one_used(self):
        self._write_pointer('{"issue": 7, "round": 1}')
        real = pointer_completion.ingest_target
        resolved, ingested = [], []

        def advance_after_the_first(args, repo_root):
            result = real(args, repo_root)
            resolved.append(result)
            if len(resolved) == 1:  # ロック前の検証の直後に、並行 ingest がポインタを進める
                self._write_pointer('{"issue": 7, "round": 5}')
            return result

        with mock.patch.object(
            pointer_completion, "ingest_target", side_effect=advance_after_the_first
        ), mock.patch(
            "karte.ingest_review.ingest_locked",
            side_effect=lambda root, issue, round_no, text: ingested.append((issue, round_no)) or 0,
        ), mock.patch("sys.stdin", io.StringIO("### new\n")):
            code = cli.cmd_ingest_review(self._args(issue=None, round=None, source="-"))
        self.assertEqual(0, code)
        self.assertEqual([(7, 2), (7, 6)], resolved)
        self.assertEqual([(7, 6)], ingested)


if __name__ == "__main__":
    unittest.main()
