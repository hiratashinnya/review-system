"""``karte.verb_boundary``：verb が関数として振る舞う契約（名前・docstring）と、``git diff`` 失敗の fail-close。

``fail_close`` が返すのは ``cmd(args) -> 終了コード`` で、``functools.wraps`` により元の関数の
``__name__`` / ``__doc__`` を引き継ぐ（フックの診断・argparse のヘルプ・``inspect`` が頼る）。
``TouchedError``（``close-attempt`` の ``--base`` が解決できず ``git diff`` が失敗した）は終了コード契約
{0,2,3,4} の中で 4 に収める。``_REFUSALS`` から外れると traceback の終了コード 1 になる。
"""

import unittest

from karte import cli, exit_codes
from karte.verb_boundary import fail_close
from tests.unit.karte_support import RootedCase, finding, ingest_argv, report_text


def _documented_verb(args, repo_root):
    """元の関数の説明。"""
    return 0


class TestVerbKeepsTheWrappedFunctionsIdentity(unittest.TestCase):
    def test_wrapper_carries_the_name_doc_and_wrapped_function(self):
        for locked in (True, False):
            with self.subTest(locked=locked):
                verb = fail_close(locked=locked)(_documented_verb)
                self.assertEqual("_documented_verb", verb.__name__)
                self.assertEqual("元の関数の説明。", verb.__doc__)
                self.assertIs(_documented_verb, getattr(verb, "__wrapped__"))
                self.assertIs(locked, verb.locked)

    def test_builtin_verbs_keep_their_own_names(self):
        for name in ("ingest_review", "render", "append", "close_attempt", "check", "status"):
            with self.subTest(verb=name):
                verb = getattr(cli, f"cmd_{name}")
                self.assertEqual(f"cmd_{name}", verb.__name__)
        for name in ("ingest_review", "render", "check", "status"):  # docstring を持つ verb
            with self.subTest(doc=name):
                self.assertTrue(getattr(cli, f"cmd_{name}").__doc__)


class TestGitDiffFailureIsAFailClose(RootedCase):
    prefix = "karte-vb-"

    def test_close_attempt_with_an_unresolvable_base_is_exit_error(self):
        code, _out, err = self.run_verb(
            ingest_argv(7, 1), report_text(("new", finding("a.py::f", "f が入力検査をしていない")))
        )
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        code, _out, err = self.run_verb(
            ["append", "--finding-ids", "F-7-01", "--root-cause", "rc", "--change-kind", "logic",
             "--targets", "a.py::f"]
        )
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        code, _out, err = self.run_verb(
            ["close-attempt", "--outcome", "fixed", "--base", "no-such-ref-for-karte-test"]
        )
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("git diff が失敗した", err)
        self.assertEqual([], self.ledger().results)


if __name__ == "__main__":
    unittest.main()
