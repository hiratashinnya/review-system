"""``karte.repo_roots``：台帳の repo-root は 1 箇所で、呼び出しごとに遅延解決する。"""

import argparse
import ast
import contextlib
import io
import unittest
from pathlib import Path
from unittest import mock

import karte
from karte import cli, repo_roots
from tests.unit.karte_support import finding, make_tmp_repo, report_text, run_cli, verb_parsers


class TestRepoRootPrecedence(unittest.TestCase):
    def setUp(self):
        self.root = make_tmp_repo(self, "karte-rr-", with_tmp=False)
        self.other = make_tmp_repo(self, "karte-rr2-", with_tmp=False)

    def test_args_override_wins_over_module_override(self):
        with mock.patch.object(repo_roots, "_REPO_ROOT", self.other):
            args = argparse.Namespace(repo_root=str(self.root))
            self.assertEqual(self.root, repo_roots.repo_root_of(args))

    def test_module_override_is_used_without_deriving_the_main_worktree(self):
        with mock.patch.object(repo_roots, "_REPO_ROOT", self.root), mock.patch(
            "karte.repo_roots.paths.main_worktree_root"
        ) as derive:
            self.assertEqual(self.root, repo_roots.repo_root_of(argparse.Namespace()))
        derive.assert_not_called()

    def test_without_overrides_the_main_worktree_is_derived_on_every_call(self):
        with mock.patch.object(repo_roots, "_REPO_ROOT", None), mock.patch(
            "karte.repo_roots.paths.main_worktree_root", return_value=self.root
        ) as derive:
            first = repo_roots.repo_root_of(argparse.Namespace())
            second = repo_roots.repo_root_of(argparse.Namespace())
        self.assertEqual((self.root, self.root), (first, second))
        self.assertEqual(2, derive.call_count)  # キャッシュしない（K-12）
        derive.assert_called_with(repo_roots._PACKAGE_ROOT)

    def test_invoking_worktree_is_not_converged_to_the_main_worktree(self):
        with mock.patch.object(repo_roots, "_PACKAGE_ROOT", self.other), mock.patch.object(
            repo_roots, "_REPO_ROOT", self.root
        ):
            self.assertEqual(self.other, repo_roots.invoking_worktree())


class TestRepoRootIsDerivedInOnePlace(unittest.TestCase):
    """台帳 root の導出（``main_worktree_root``）を呼ぶのは ``repo_roots`` だけ。"""

    ALLOWED = {"repo_roots.py", "paths.py", "path_roots.py"}

    def test_no_other_module_derives_the_ledger_root(self):
        package = Path(karte.__file__).parent
        offenders = []
        for path in package.glob("*.py"):
            if path.name in self.ALLOWED:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and "main_worktree_root" in ast.dump(node.func):
                    offenders.append(path.name)
        self.assertEqual([], offenders)


_FINDING = finding("a.py::f", "f が入力検査をしていない")


class TestEveryVerbResolvesTheRootExactlyOnce(unittest.TestCase):
    """各 verb を**台帳つきで本体の最後まで**走らせ、その間に台帳 root の導出が 1 回だけであることを数える。

    台帳が無いと verb は冒頭の未検出で終わり、本体の途中（``load_karte`` のあと・ロック内）で
    起きる再解決を見逃す。数える対象は ``paths.main_worktree_root``（root を導出する唯一の入口）で、
    どのモジュール経由で ``repo_root_of`` を呼んでも数えられる。
    """

    DIFF = "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@ def f\n-a\n+b\n"
    # verb ごとの、台帳を用意したあとの argv（終了コード 0 で本体の最後まで走る）。
    ARGV = {
        "ingest-review": ["--issue", "7", "--round", "2", "--from", "tmp/review-2.md"],
        "render": ["--issue", "7"],
        "append": [
            "--issue", "7", "--round", "1", "--finding-ids", "F-7-01", "--root-cause", "other",
            "--change-kind", "interface", "--targets", "z.py::h",
        ],
        "close-attempt": ["--issue", "7", "--attempt", "2", "--outcome", "fixed",
                          "--diff-file", "tmp/x.diff"],
        "check": ["--issue", "7", "--round", "1"],
        "status": ["--issue", "7"],
    }

    def _prepared_root(self, verb):
        root = make_tmp_repo(self, "karte-rr3-")
        (root / "tmp" / "review-2.md").write_text(report_text(("F-7-01", _FINDING)), encoding="utf-8")
        (root / "tmp" / "x.diff").write_text(self.DIFF, encoding="utf-8")
        steps = [
            (["ingest-review", "--issue", "7", "--round", "1", "--from", "-"],
             report_text(("new", _FINDING))),
            (["append", "--finding-ids", "F-7-01", "--root-cause", "rc", "--change-kind", "logic",
              "--targets", "a.py::f"], ""),
            (["close-attempt", "--outcome", "fixed", "--diff-file", "tmp/x.diff"], ""),
        ]
        if verb == "close-attempt":  # 閉じる対象（未クローズの Attempt 2）を用意する
            steps.append(
                (["append", "--finding-ids", "F-7-01", "--root-cause", "second",
                  "--change-kind", "interface", "--targets", "y.py::g"], "")
            )
        for argv, stdin_text in steps:
            code, _out, err = run_cli(root, argv, stdin_text)
            self.assertEqual(0, code, f"{verb} の準備 {argv}: {err}")
        return root

    def test_every_builtin_verb_resolves_the_root_exactly_once(self):
        parser = cli.build_parser()
        self.assertEqual(set(self.ARGV), set(verb_parsers(parser)))
        for verb, argv in self.ARGV.items():
            with self.subTest(verb=verb):
                root = self._prepared_root(verb)
                args = parser.parse_args([verb, *argv])  # ``repo_root`` を与えない＝本物の導出経路を通る
                with mock.patch.object(repo_roots, "_REPO_ROOT", None), mock.patch(
                    "karte.repo_roots.paths.main_worktree_root", return_value=root
                ) as derive, mock.patch.object(
                    repo_roots, "invoking_worktree", return_value=root
                ), contextlib.redirect_stderr(io.StringIO()) as err, contextlib.redirect_stdout(
                    io.StringIO()
                ):
                    code = args.func(args)
                self.assertEqual(0, code, err.getvalue())  # 本体の最後まで走っている
                self.assertEqual(1, derive.call_count)


if __name__ == "__main__":
    unittest.main()
