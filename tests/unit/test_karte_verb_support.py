"""``verb_support`` の共通部品（整数の検証・ポインタの round 0・repo-root の 1 箇所化）。"""

import argparse
import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from karte import cli, model, paths, verb_support
from karte.errors import KarteUsageError

NON_ASCII_DIGITS = ("²", "٣", "①")  # str.isdigit() は True だが int() できない


class TestParseInt(unittest.TestCase):
    def test_accepts_ascii_digits_at_or_above_the_minimum(self):
        self.assertEqual(3, verb_support.parse_int("3", "round"))
        self.assertEqual(0, verb_support.parse_int(0, "round", minimum=0))

    def test_rejects_below_minimum_and_non_numbers(self):
        for value in ("0", "-1", "abc", "", "1.5", None):
            with self.subTest(value=value):
                with self.assertRaises(KarteUsageError):
                    verb_support.parse_int(value, "round")

    def test_non_ascii_digits_raise_usage_error_not_value_error(self):
        for value in NON_ASCII_DIGITS:
            with self.subTest(value=value):
                with self.assertRaises(KarteUsageError):
                    verb_support.parse_int(value, "round", minimum=0)


class TestHugeDigitStrings(unittest.TestCase):
    """桁数が多すぎる数字列は int() の変換上限で ValueError になる。fail-close に収める（L3）。"""

    HUGE = "9" * 6000

    def test_parse_int_raises_usage_error_for_huge_digit_strings(self):
        with self.assertRaises(KarteUsageError):
            verb_support.parse_int(self.HUGE, "round")

    def test_error_message_is_truncated(self):
        with self.assertRaises(KarteUsageError) as caught:
            verb_support.parse_int(self.HUGE, "round")
        self.assertLess(len(str(caught.exception)), 200)


class TestRoundAndRootResolution(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="karte-vs-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        (self.root / "tmp").mkdir()

    def _args(self, **kwargs):
        return argparse.Namespace(repo_root=str(self.root), **kwargs)

    def test_ingest_review_with_non_ascii_round_is_exit_error_without_traceback(self):
        report = self.root / "tmp" / "r.md"
        report.write_text("### new\n", encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()):
            code = cli.cmd_ingest_review(self._args(issue="1", round="²", source=str(report)))
        self.assertEqual(cli.EXIT_ERROR, code)

    def test_check_with_non_ascii_round_is_exit_error_without_traceback(self):
        paths.karte_path(1, self.root, create_dir=True).write_text(
            model.dumps(model.new_karte(1)), encoding="utf-8"
        )
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = cli.cmd_check(self._args(issue="1", round="²"))
        self.assertEqual(cli.EXIT_ERROR, code)

    def test_pointer_round_raises_usage_error_for_non_ascii_round(self):
        with self.assertRaises(KarteUsageError):
            cli._pointer_round(self._args(issue="1", round="²"), self.root, 1, "")

    def test_pointer_round_zero_is_rejected_by_ingest_review_as_before(self):
        paths.active_path(self.root, create_dir=True).write_text('{"issue": 7, "round": 0}\n', encoding="utf-8")
        with self.assertRaises(KarteUsageError):
            cli._resolve_ingest_round(self._args(issue="7", round=None), self.root, 7)

    def test_repo_root_override_is_a_single_place(self):
        args = argparse.Namespace()
        with mock.patch.object(verb_support, "_REPO_ROOT", self.root):
            self.assertEqual(self.root, verb_support.repo_root_of(args))


if __name__ == "__main__":
    unittest.main()
