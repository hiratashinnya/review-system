"""整数変換の fail-close（F-696-21）。非 ASCII 数字・巨大桁は、traceback（終了コード 1）ではなく 4。

``int()`` は ``"²"``（``str.isdigit()`` は真）で、また 4300 桁超で ``ValueError`` になる。
文書化された終了コード {0,2,3,4} の外へ漏れないよう、変換は :mod:`karte.int_args` を通す
（変換関数そのものの単体テストは ``test_karte_int_args.py``）。
"""

import argparse
import contextlib
import io
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from karte import cli, exit_codes, model, paths
from tests.unit.karte_support import finding, make_tmp_repo, required_finding

REPO = Path(__file__).resolve().parent.parent.parent
HUGE = "9" * 5000
_FINDING = finding("a/b.py::f", "f が入力検査をしていない")


class _RootedCase(unittest.TestCase):
    def setUp(self):
        self.root = make_tmp_repo(self, "karte-int-")

    def _call(self, func, **kwargs):
        args = argparse.Namespace(repo_root=str(self.root), **kwargs)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = func(args)
        return code, err.getvalue()

    def _write_report(self, text):
        path = self.root / "tmp" / "review.md"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def _ledger_text(self) -> str:
        karte = model.Karte(issue=5)
        karte.findings.append(
            model.Finding(
                id="F-5-01", harm=_FINDING["harm"], harm_detail=_FINDING["harm_detail"],
                severity=_FINDING["severity"], scope=_FINDING["scope"],
                locus=[_FINDING["locus"]], summary=_FINDING["summary"],
                evidence=_FINDING["evidence"], expected=_FINDING["expected"],
                recheck=_FINDING["recheck"], rounds=[1],
            )
        )
        return model.dumps(karte)

    def _write_ledger(self, mutate):
        text = mutate(self._ledger_text())
        paths.karte_path(5, self.root, create_dir=True).write_text(text, encoding="utf-8")


class TestHugeIssue(_RootedCase):
    def test_ingest_review_with_a_huge_issue_is_exit_error(self):
        code, err = self._call(cli.cmd_ingest_review, issue=HUGE, round="1", source="-")
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertNotIn("Traceback", err)

    def test_real_process_with_a_huge_issue_is_exit_error(self):
        sandbox = self.root / "pkg"
        shutil.copytree(
            REPO / "karte", sandbox / "karte", ignore=shutil.ignore_patterns("__pycache__")
        )
        done = subprocess.run(
            [sys.executable, "-m", "karte", "ingest-review", "--issue", HUGE, "--round", "1",
             "--from", "-"],
            input=b"", cwd=str(sandbox), capture_output=True,
        )
        self.assertEqual(exit_codes.EXIT_ERROR, done.returncode, done.stderr)
        self.assertNotIn(b"Traceback", done.stderr)


class TestNonAsciiDigitsInTheLedger(_RootedCase):
    def test_status_and_ingest_refuse_a_ledger_with_a_non_ascii_rounds_entry(self):
        self._write_ledger(lambda text: text.replace("rounds: [1]", "rounds: [²]"))
        self.assertIn("rounds: [²]", paths.karte_path(5, self.root).read_text(encoding="utf-8"))
        code, err = self._call(cli.cmd_status, issue="5", json=False)
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        report = self._write_report(
            "### new\n" + "\n".join(f"{k}: {v}" for k, v in _FINDING.items()) + "\n"
        )
        code, err = self._call(cli.cmd_ingest_review, issue="5", round="2", source=report)
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertNotIn("Traceback", err)

    def test_unmodified_ledger_parses(self):
        """前提：mutate 前の台帳は有効（以降の拒否が別の理由で空振りしていない）。"""
        self.assertEqual([1], required_finding(model.parse(self._ledger_text()), "F-5-01").rounds)

    def test_non_ascii_resolved_round_is_a_format_error(self):
        text = self._ledger_text().replace("resolved_round: \n", "resolved_round: ²\n")
        self.assertIn("resolved_round: ²", text)
        with self.assertRaisesRegex(model.KarteFormatError, "resolved_round は整数"):
            model.parse(text)

    def test_non_ascii_rounds_entry_is_a_format_error(self):
        text = self._ledger_text().replace("rounds: [1]", "rounds: [²]")
        with self.assertRaisesRegex(model.KarteFormatError, "'rounds' は整数のリスト"):
            model.parse(text)


class TestHugeNumbersInHeadings(_RootedCase):
    def test_report_heading_with_a_huge_sequence_is_exit_error(self):
        fields = "\n".join(f"{k}: {v}" for k, v in _FINDING.items())
        report = self._write_report(f"### F-6-{HUGE}\n{fields}\n")
        code, err = self._call(cli.cmd_ingest_review, issue="6", round="1", source=report)
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertNotIn("Traceback", err)
        self.assertFalse(paths.karte_path(6, self.root).exists())

    def test_ledger_headings_with_huge_numbers_are_format_errors(self):
        base = self._ledger_text()
        attempt = f"### Attempt {HUGE}\nround: 1\nfinding_ids: [F-5-01]\nroot_cause: rc\n"
        result = f"### Result {HUGE}\nattempt: 1\nfinding_ids: [F-5-01]\noutcome: fixed\n"
        for text in (
            base.replace("issue-5", f"issue-{HUGE}", 1),
            base + attempt,
            base + result,
            base.replace("F-5-01", f"F-5-{HUGE}"),
        ):
            with self.subTest(text=text[-30:]), self.assertRaisesRegex(
                model.KarteFormatError, "桁数が多すぎる"
            ):
                model.parse(text)


if __name__ == "__main__":
    unittest.main()
