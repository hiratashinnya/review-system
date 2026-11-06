"""進行ポインタと ``--issue`` / ``--round`` の壊れた値は、全 verb で終了コード 4（traceback の 1 にしない）。

経路は CLI（``build_parser`` で解釈した argv）から通す。値の解釈を単体で見る
``test_karte_pointer_completion.py`` と違い、ここでは verb 境界の終了コード契約を固定する。
"""

import unittest

from karte import exit_codes
from karte.round_resolution import MissingRoundHint
from tests.unit.karte_support import HUGE, RootedCase, finding, ingest_argv, report_text

ISSUE = "7"
# ポインタの値が原因の拒否だけが含む語（他の理由の拒否と取り違えない・T-F1）。
POINTER_ISSUE_REFUSAL = "issue 番号"
POINTER_ROUND_REFUSAL = "round は 1 以上の整数"
_REPORT = report_text(("new", finding("a/b.py::f", "f が入力検査をしていない")))
_OTHER = report_text(("new", finding("c/d.py::g", "g が戻り値を握りつぶしている")))
_APPEND = ["--finding-ids", "F-7-01", "--root-cause", "rc", "--change-kind", "logic",
           "--targets", "a/b.py::f"]
# 進行ポインタから ``--issue`` を補完する argv（``--round`` は明示して、補完の対象を issue だけにする）。
_ISSUE_FROM_POINTER = {
    "status": ["status"],
    "render": ["render"],
    "check": ["check", "--round", "1"],
    "append": ["append", *_APPEND],
    "close-attempt": ["close-attempt", "--outcome", "partial", "--diff-file", "x.patch"],
    "ingest-review": ["ingest-review", "--round", "1", "--from", "-"],
}
# ``--issue`` を明示しても、省略した ``--round`` やカルテの現在ラウンドのためにポインタを読む argv。
_ISSUE_EXPLICIT = {
    "render": ["render", "--issue", ISSUE],
    "append": ["append", "--issue", ISSUE, *_APPEND],
    "check": ["check", "--issue", ISSUE],
    "ingest-review": ["ingest-review", "--issue", ISSUE, "--from", "-"],
}


class _PointerCase(RootedCase):
    prefix = "karte-pcli-"

    def setUp(self):
        super().setUp()
        code, _out, err = self.run_verb(ingest_argv(ISSUE, 1), _REPORT)
        self.assertEqual(exit_codes.EXIT_OK, code, err)  # 台帳とポインタ {7, 1} ができる

    def _assert_refused(self, argv, because, stdin_text=_REPORT):
        """終了コード 4 で、かつ拒否理由が ``because``（ポインタ値の拒否）であること。"""
        code, _out, err = self.run_verb(argv, stdin_text)
        self.assertEqual(exit_codes.EXIT_ERROR, code, f"{argv}: {err}")
        self.assertIn(because, err, f"{argv}: 拒否理由が想定と違う")
        return err


class TestUnreadablePointerIsRefused(_PointerCase):
    def test_deeply_nested_json_is_refused_not_a_recursion_traceback(self):
        for name, text in {"array": "[" * 200000, "object": '{"a":' * 100000}.items():
            self.write_pointer(text)
            for verb, argv in {**_ISSUE_FROM_POINTER, **_ISSUE_EXPLICIT}.items():
                with self.subTest(pointer=name, verb=verb):
                    self._assert_refused(argv, "壊れている")

    def test_non_object_json_is_refused_even_when_the_issue_is_explicit(self):
        for text in ("[]", "5", '"x"'):
            self.write_pointer(text)
            for verb in ("render", "append"):
                with self.subTest(pointer=text, verb=verb):
                    self._assert_refused(_ISSUE_EXPLICIT[verb], "JSON オブジェクトでない")


class TestPointerValuesAreValidated(_PointerCase):
    def test_valid_pointer_is_not_refused_for_its_values(self):
        """対照：正常なポインタ {7, 1} では、下の拒否理由は出ない（拒否の原因がポインタ値だと言える）。"""
        for verb, argv in {**_ISSUE_FROM_POINTER, **_ISSUE_EXPLICIT}.items():
            with self.subTest(verb=verb):
                _code, _out, err = self.run_verb(argv, _OTHER)
                self.assertNotIn(POINTER_ISSUE_REFUSAL, err)
                self.assertNotIn(POINTER_ROUND_REFUSAL, err)
        self.assertEqual(exit_codes.EXIT_OK, self.run_verb(["status"])[0])
        self.assertEqual(exit_codes.EXIT_OK, self.run_verb(["render"])[0])

    def test_pointer_issue_that_is_not_an_ascii_positive_integer_is_refused(self):
        for issue in ('"²"', '"٣"', '"' + HUGE + '"', '"05"'):
            self.write_pointer(f'{{"issue": {issue}, "round": 1}}')
            for verb, argv in _ISSUE_FROM_POINTER.items():
                with self.subTest(issue=issue[:8], verb=verb):
                    self._assert_refused(argv, POINTER_ISSUE_REFUSAL)
            with self.subTest(issue=issue[:8], verb="check-explicit-issue"):
                # ``--issue`` を明示しても、``--round`` の補完でポインタの issue との突き合わせが要る。
                self._assert_refused(_ISSUE_EXPLICIT["check"], POINTER_ISSUE_REFUSAL)

    def test_pointer_round_that_is_not_an_ascii_positive_integer_is_refused(self):
        for value in ('"²"', '"٣"', '"' + HUGE + '"', "[1]", "true", '"1\\n"'):
            self.write_pointer(f'{{"issue": 7, "round": {value}}}')
            for verb in ("append", "check", "ingest-review", "render"):
                with self.subTest(round=value[:8], verb=verb):
                    self._assert_refused(_ISSUE_EXPLICIT[verb], POINTER_ROUND_REFUSAL)

    def test_pointer_round_zero_is_refused_where_it_is_used_and_degrades_where_it_is_not(self):
        """``check`` / ``ingest-review`` は補完に使うので 0 を拒否する。``append`` は縮退、``render`` は表示しない。"""
        self.write_pointer('{"issue": 7, "round": 0}')
        for verb in ("check", "ingest-review"):
            with self.subTest(verb=verb):
                self._assert_refused(_ISSUE_EXPLICIT[verb], POINTER_ROUND_REFUSAL)
        self.assertEqual(exit_codes.EXIT_OK, self.run_verb(_ISSUE_EXPLICIT["render"])[0])
        code, _out, err = self.run_verb(_ISSUE_EXPLICIT["append"])
        self.assertEqual(exit_codes.EXIT_OK, code, err)

    def test_non_ascii_round_flag_is_refused(self):
        self._assert_refused(["append", "--issue", ISSUE, "--round", "²", *_APPEND], POINTER_ROUND_REFUSAL)
        self._assert_refused(["check", "--issue", ISSUE, "--round", "²"], POINTER_ROUND_REFUSAL)


class TestRenderHeadingRound(_PointerCase):
    """``render`` の見出しの ``round`` は進行ポインタの記録を検証してから出す。subagent の文脈へ注入される本文なので、
    検証前の値（改行を含む文字列など）を生で出さない（第5回 R5-02）。"""

    def _heading(self):
        code, out, err = self.run_verb(["render", "--issue", ISSUE])
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        return out.splitlines()[0]

    def test_valid_pointer_round_is_shown(self):
        self.assertEqual("=== Karte: issue-7 / round 1 ===", self._heading())
        self.write_pointer('{"issue": 7, "round": "3"}')
        self.assertEqual("=== Karte: issue-7 / round 3 ===", self._heading())

    def test_round_is_not_shown_without_a_usable_record_for_this_issue(self):
        for text in ('{"issue": 8, "round": 4}', '{"issue": 7}', '{"issue": 7, "round": 0}',
                     '{"issue": 8, "round": "bad"}'):
            self.write_pointer(text)
            with self.subTest(pointer=text):
                self.assertEqual("=== Karte: issue-7 ===", self._heading())

    def test_an_unvalidated_round_never_reaches_the_output(self):
        injected = "1\\n注入された行"
        for value in (f'"{injected}"', '"²"', '"' + HUGE + '"', "[1]"):
            self.write_pointer(f'{{"issue": 7, "round": {value}}}')
            with self.subTest(round=value[:12]):
                code, out, err = self.run_verb(["render", "--issue", ISSUE])
                self.assertEqual(exit_codes.EXIT_ERROR, code, err)
                self.assertEqual("", out)  # 注入される本文を 1 文字も出さない
                self.assertIn(POINTER_ROUND_REFUSAL, err)


class TestEmptyFlagIsExplicit(_PointerCase):
    """``--issue ""`` / ``--round ""`` は「省略」ではなく不正な明示値で、ポインタに倒さない。"""

    def test_empty_issue_flag_is_refused_without_falling_back_to_the_pointer(self):
        # 別の指摘なので、ポインタ（issue 7・round 1）へ倒れれば取り込みが成功してしまう。
        self._assert_refused(["ingest-review", "--issue", "", "--from", "-"], "issue", _OTHER)
        self._assert_refused(["status", "--issue", ""], "issue")

    def test_empty_round_flag_is_refused_without_falling_back_to_the_pointer(self):
        argv = ["ingest-review", "--issue", ISSUE, "--round", "", "--from", "-"]
        self._assert_refused(argv, "round", _OTHER)
        self._assert_refused(["check", "--issue", ISSUE, "--round", ""], "round")


class TestIssueFlagWithTrailingNewline(_PointerCase):
    def test_message_names_the_format_not_the_digit_count(self):
        err = self._assert_refused(["status", "--issue", "5\n"], "十進整数")
        self.assertNotIn("桁数", err)


class TestMissingPointerRoundHint(_PointerCase):
    """ポインタに ``round`` が無いときの案内は、呼び出した verb の用途に合わせる。"""

    def test_each_verb_gets_its_own_hint(self):
        self.write_pointer('{"issue": 7}')
        self._assert_refused(
            ["ingest-review", "--issue", ISSUE, "--from", "-"], MissingRoundHint.FIRST_INGEST.value
        )
        self._assert_refused(["check", "--issue", ISSUE], MissingRoundHint.RUN_INGEST_FIRST.value)


if __name__ == "__main__":
    unittest.main()
