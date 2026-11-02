"""進行ポインタと ``--issue`` / ``--round`` の壊れた値は、全 verb で終了コード 4（traceback の 1 にしない）。

経路は CLI（``build_parser`` で解釈した argv）から通す。値の解釈を単体で見る
``test_karte_pointer_completion.py`` と違い、ここでは verb 境界の終了コード契約を固定する。
"""

import unittest

from karte import exit_codes, paths
from karte.round_resolution import MissingRoundHint
from tests.unit.karte_support import finding, make_tmp_repo, report_text, run_cli

ISSUE = "7"
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


class _PointerCase(unittest.TestCase):
    def setUp(self):
        self.root = make_tmp_repo(self, "karte-pcli-")
        code, _out, err = run_cli(
            self.root, ["ingest-review", "--issue", ISSUE, "--round", "1", "--from", "-"], _REPORT
        )
        self.assertEqual(exit_codes.EXIT_OK, code, err)  # 台帳とポインタ {7, 1} ができる

    def _point(self, text):
        paths.active_path(self.root, create_dir=True).write_text(text, encoding="utf-8")

    def _assert_refused(self, argv, stdin_text=_REPORT):
        code, _out, err = run_cli(self.root, argv, stdin_text)
        self.assertEqual(exit_codes.EXIT_ERROR, code, f"{argv}: {err}")
        return err


class TestUnreadablePointerIsRefused(_PointerCase):
    def test_deeply_nested_json_is_refused_not_a_recursion_traceback(self):
        for name, text in {"array": "[" * 200000, "object": '{"a":' * 100000}.items():
            self._point(text)
            for verb, argv in {**_ISSUE_FROM_POINTER, **_ISSUE_EXPLICIT}.items():
                with self.subTest(pointer=name, verb=verb):
                    self.assertIn("壊れている", self._assert_refused(argv))

    def test_non_object_json_is_refused_even_when_the_issue_is_explicit(self):
        for text in ("[]", "5", '"x"'):
            self._point(text)
            for verb in ("render", "append"):
                with self.subTest(pointer=text, verb=verb):
                    self.assertIn("JSON オブジェクトでない", self._assert_refused(_ISSUE_EXPLICIT[verb]))


class TestPointerValuesAreValidated(_PointerCase):
    def test_pointer_issue_that_is_not_an_ascii_positive_integer_is_refused(self):
        for issue in ('"²"', '"٣"', '"' + "9" * 5000 + '"', '"05"'):
            self._point(f'{{"issue": {issue}, "round": 1}}')
            for verb, argv in _ISSUE_FROM_POINTER.items():
                with self.subTest(issue=issue[:8], verb=verb):
                    self._assert_refused(argv)
            with self.subTest(issue=issue[:8], verb="check-explicit-issue"):
                self._assert_refused(_ISSUE_EXPLICIT["check"])

    def test_pointer_round_that_is_not_an_ascii_positive_integer_is_refused(self):
        # ``render`` は round を見出しに表示するだけで検証しない。``append`` は round 0 を
        # 「無い」と同じに扱いカルテ内の最大ラウンドへ縮退する（cli の docstring どおり）。
        for value in ('"²"', '"٣"', '"' + "9" * 5000 + '"', "[1]", "0"):
            self._point(f'{{"issue": 7, "round": {value}}}')
            for verb in ("append", "check", "ingest-review"):
                if verb == "append" and value == "0":
                    continue
                with self.subTest(round=value[:8], verb=verb):
                    self._assert_refused(_ISSUE_EXPLICIT[verb])

    def test_non_ascii_round_flag_is_refused(self):
        self._assert_refused(["append", "--issue", ISSUE, "--round", "²", *_APPEND])
        self._assert_refused(["check", "--issue", ISSUE, "--round", "²"])


class TestEmptyFlagIsExplicit(_PointerCase):
    """``--issue ""`` / ``--round ""`` は「省略」ではなく不正な明示値で、ポインタに倒さない。"""

    def test_empty_issue_flag_is_refused_without_falling_back_to_the_pointer(self):
        # 別の指摘なので、ポインタ（issue 7・round 1）へ倒れれば取り込みが成功してしまう。
        self.assertIn("issue", self._assert_refused(["ingest-review", "--issue", "", "--from", "-"], _OTHER))
        self.assertIn("issue", self._assert_refused(["status", "--issue", ""]))

    def test_empty_round_flag_is_refused_without_falling_back_to_the_pointer(self):
        argv = ["ingest-review", "--issue", ISSUE, "--round", "", "--from", "-"]
        self.assertIn("round", self._assert_refused(argv, _OTHER))
        self.assertIn("round", self._assert_refused(["check", "--issue", ISSUE, "--round", ""]))


class TestIssueFlagWithTrailingNewline(_PointerCase):
    def test_message_names_the_format_not_the_digit_count(self):
        err = self._assert_refused(["status", "--issue", "5\n"])
        self.assertIn("十進整数", err)
        self.assertNotIn("桁数", err)


class TestMissingPointerRoundHint(_PointerCase):
    """ポインタに ``round`` が無いときの案内は、呼び出した verb の用途に合わせる。"""

    def test_each_verb_gets_its_own_hint(self):
        self._point('{"issue": 7}')
        self.assertIn(
            MissingRoundHint.FIRST_INGEST.value,
            self._assert_refused(["ingest-review", "--issue", ISSUE, "--from", "-"]),
        )
        self.assertIn(
            MissingRoundHint.RUN_INGEST_FIRST.value,
            self._assert_refused(["check", "--issue", ISSUE]),
        )


if __name__ == "__main__":
    unittest.main()
