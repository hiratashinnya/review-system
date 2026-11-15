"""正規表現の末尾アンカー（PR #696 第5回 R5-06）。

``$`` は末尾の改行の手前でも一致するため、``.match("5\\n")`` が真になる。公開された正規表現
（``paths.ISSUE_RE``）や、前段の ``strip()`` に守られているだけの正規表現（``touched.REF_RE``）は、
使い手が ``.match`` を選んでも末尾の改行を通さないことを固定する。
"""

import unittest

from karte import model, paths, touched

TRAILING = ("\n", "\r\n", " \n")


class TestIssuePatternRejectsATrailingNewline(unittest.TestCase):
    def test_the_published_pattern_matches_only_whole_numbers_whichever_method_is_used(self):
        for text in ("5", "10", "123456"):
            with self.subTest(text=text):
                self.assertTrue(paths.ISSUE_RE.match(text))
                self.assertTrue(paths.ISSUE_RE.fullmatch(text))
        for text in ("05", "0", "", "-5", "5 ", " 5", *("5" + tail for tail in TRAILING)):
            with self.subTest(text=repr(text)):
                self.assertIsNone(paths.ISSUE_RE.match(text))
                self.assertIsNone(paths.ISSUE_RE.fullmatch(text))

    def test_validate_issue_refuses_a_trailing_newline(self):
        self.assertEqual(5, paths.validate_issue("5"))
        with self.assertRaises(paths.KartePathError):
            paths.validate_issue("5\n")


class TestRefPatternAndTheStripThatGuardsIt(unittest.TestCase):
    def test_the_pattern_alone_rejects_a_trailing_newline(self):
        self.assertTrue(touched.REF_RE.match("HEAD~1"))
        for tail in TRAILING:
            with self.subTest(tail=repr(tail)):
                self.assertIsNone(touched.REF_RE.match("HEAD" + tail))

    def test_surrounding_whitespace_is_stripped_before_the_ref_is_used(self):
        """ref に空白・改行を残さない（``git diff`` へ渡す argv の 1 要素にそのまま入るため）。"""
        self.assertEqual("HEAD", touched.validate_ref("HEAD\n"))
        self.assertEqual("origin/main", touched.validate_ref("  origin/main \r\n"))

    def test_inner_whitespace_and_option_like_refs_are_refused(self):
        for text in ("HE AD", "HEAD\nmain", "--output=x", "-q", "", "  \n", "a;b"):
            with self.subTest(text=repr(text)), self.assertRaises(touched.TouchedError):
                touched.validate_ref(text)


class TestModelPatternsRejectATrailingNewline(unittest.TestCase):
    """``model`` の正規表現も、前段の ``strip()`` / ``check_scalar`` が無くても末尾の改行を通さない。"""

    CASES = (
        (model.SLUG_RE, "root-cause.1"),
        (model.FINDING_ID_RE, "F-312-03"),
        (model.ATTEMPT_TITLE_RE, "Attempt 2"),
        (model.RESULT_TITLE_RE, "Result 2"),
        (model.DEFERRED_TO_RE, "#123"),
        (model.DEFERRED_TO_RE, "https://github.com/o/r/issues/9"),
    )

    def test_each_pattern_accepts_the_bare_text_and_refuses_it_with_a_trailing_newline(self):
        for pattern, text in self.CASES:
            with self.subTest(pattern=pattern.pattern[:24], text=text):
                self.assertTrue(pattern.match(text))
                for tail in TRAILING:
                    self.assertIsNone(pattern.match(text + tail))


if __name__ == "__main__":
    unittest.main()
