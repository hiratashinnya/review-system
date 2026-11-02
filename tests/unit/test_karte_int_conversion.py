"""整数変換の fail-close（F-696-21・第5回 R5-01）。非 ASCII 数字・巨大桁は、traceback（終了コード 1）ではなく 4。

``int()`` は ``"²"``（``str.isdigit()`` は真）で、また 4300 桁超で ``ValueError`` になる。
文書化された終了コード {0,2,3,4} の外へ漏れないよう、変換は :mod:`karte.int_args` を通す
（変換関数そのものの単体テストは ``test_karte_int_args.py``）。受理した値に ``+ 1`` して書く箇所
（自動補完の ``round``・``finding`` の連番・Attempt 番号）は、書いた値を読み戻せることも固定する。
"""

import subprocess
import sys
import unittest

from karte import exit_codes, model, paths
from karte.int_args import MAX_DIGITS
from tests.unit.karte_support import (
    AT_CONVERSION_LIMIT, HUGE, RootedCase, finding, ingest_argv, karte_sandbox, report_text, required_finding,
)

_FINDING = finding("a/b.py::f", "f が入力検査をしていない")
_OTHER = finding("c/d.py::g", "g が戻り値を握りつぶしている")
LONGEST = "9" * MAX_DIGITS  # 受理される最大の数


class _IntCase(RootedCase):
    prefix = "karte-int-"

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

    def _write_ledger(self, text):
        paths.karte_path(5, self.root, create_dir=True).write_text(text, encoding="utf-8")

    def _ledger_bytes(self) -> bytes:
        return paths.karte_path(5, self.root).read_bytes()


class TestHugeIssue(_IntCase):
    def test_ingest_review_with_a_huge_issue_is_exit_error(self):
        code, _out, err = self.run_verb(ingest_argv(HUGE, 1))
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertNotIn("Traceback", err)

    def test_real_process_with_a_huge_issue_is_exit_error(self):
        sandbox = karte_sandbox(self)
        done = subprocess.run(
            [sys.executable, "-m", "karte", *ingest_argv(HUGE, 1)],
            input=b"", cwd=str(sandbox), capture_output=True,
        )
        self.assertEqual(exit_codes.EXIT_ERROR, done.returncode, done.stderr)
        self.assertNotIn(b"Traceback", done.stderr)


class TestNonAsciiDigitsInTheLedger(_IntCase):
    def test_status_and_ingest_refuse_a_ledger_with_a_non_ascii_rounds_entry(self):
        self._write_ledger(self._ledger_text().replace("rounds: [1]", "rounds: [²]"))
        self.assertIn("rounds: [²]", paths.karte_path(5, self.root).read_text(encoding="utf-8"))
        code, _out, err = self.run_verb(["status", "--issue", "5"])
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        report = self._write_report(
            "### new\n" + "\n".join(f"{k}: {v}" for k, v in _FINDING.items()) + "\n"
        )
        code, _out, err = self.run_verb(ingest_argv(5, 2, report))
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


class TestHugeNumbersInHeadings(_IntCase):
    def test_report_heading_with_a_huge_sequence_is_exit_error(self):
        fields = "\n".join(f"{k}: {v}" for k, v in _FINDING.items())
        report = self._write_report(f"### F-6-{HUGE}\n{fields}\n")
        code, _out, err = self.run_verb(ingest_argv(6, 1, report))
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


class TestRoundAtTheConversionLimit(_IntCase):
    """変換上限ちょうどの ``--round`` は、次の自動補完（``+ 1``）で ``str()`` が落ちる前に拒否する（R5-01）。"""

    def test_limit_digit_round_flag_is_refused_without_a_traceback(self):
        code, _out, err = self.run_verb(ingest_argv(5, AT_CONVERSION_LIMIT))
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertFalse((self.root / "tmp" / "_karte").exists())  # 検証だけで拒否し、何も作らない

    def test_limit_digit_pointer_round_is_refused_when_ingest_completes_it(self):
        self.write_pointer(f'{{"issue": 5, "round": {AT_CONVERSION_LIMIT}}}')
        code, _out, err = self.run_verb(ingest_argv(None, None), "### new\n")
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("round", err)

    def test_the_longest_accepted_round_is_stored_and_its_successor_is_refused(self):
        """``+ 1`` した値が受理上限を超えるなら書かない（書けば台帳が以後読めなくなる）。"""
        code, _out, err = self.run_verb(ingest_argv(5, LONGEST), _report("new", _FINDING))
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        before = self._ledger_bytes()
        code, _out, err = self.run_verb(ingest_argv(5, None), _report("F-5-01", _FINDING))
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("桁数の上限", err)
        self.assertEqual(before, self._ledger_bytes())
        self.assertEqual(int(LONGEST), required_finding(self.ledger(5), "F-5-01").rounds[-1])


class TestNumbersAtTheDigitLimitAreNotExtended(_IntCase):
    """連番・Attempt 番号に ``+ 1`` した結果が読み戻せない桁数になるなら、書かずに拒否する。"""

    def test_a_new_finding_after_the_longest_sequence_is_refused_and_writes_nothing(self):
        self._write_ledger(self._ledger_text().replace("F-5-01", f"F-5-{LONGEST}"))
        before = self._ledger_bytes()
        fields = _report(f"F-5-{LONGEST}", _FINDING, "new", _OTHER)
        code, _out, err = self.run_verb(ingest_argv(5, 2), fields)
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("桁数が多すぎる", err)
        self.assertEqual(before, self._ledger_bytes())

    def test_two_new_findings_that_overflow_on_the_second_are_refused(self):
        """1 件目の採番は上限に収まり、その次（``+ 1``）が溢れる——2 件目の採番で拒否される。"""
        near = "9" * (MAX_DIGITS - 1) + "8"
        self._write_ledger(self._ledger_text().replace("F-5-01", f"F-5-{near}"))
        before = self._ledger_bytes()
        fields = _report(f"F-5-{near}", _FINDING, "new", _OTHER, "new", dict(_OTHER, locus="x.py::y"))
        code, _out, err = self.run_verb(ingest_argv(5, 2), fields)
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("桁数が多すぎる", err)
        self.assertEqual(before, self._ledger_bytes())

    def test_next_attempt_number_after_the_longest_is_refused(self):
        attempt = model.Attempt(
            number=int(LONGEST), round=1, finding_ids=["F-5-01"], root_cause="rc",
            change_kind="logic", targets=["a/b.py::f"],
        )
        self._write_ledger(self._ledger_text() + "\n" + model.render_attempt(attempt))
        before = self._ledger_bytes()
        argv = ["append", "--issue", "5", "--finding-ids", "F-5-01", "--root-cause", "other",
                "--change-kind", "interface", "--targets", "z.py::h"]
        code, _out, err = self.run_verb(argv)
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("桁数が多すぎる", err)
        self.assertEqual(before, self._ledger_bytes())


def _report(*pairs) -> str:
    """``(title, fields, title, fields, ...)`` の平らな列からレビューレポート本文を作る。"""
    return report_text(*zip(pairs[0::2], pairs[1::2]))


if __name__ == "__main__":
    unittest.main()
