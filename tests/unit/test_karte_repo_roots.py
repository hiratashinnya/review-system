"""``karte.repo_roots``：台帳の repo-root は 1 箇所で、呼び出しごとに遅延解決する。"""

import argparse
import ast
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import karte
from karte import cli, repo_roots


class TestRepoRootPrecedence(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="karte-rr-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.other = Path(tempfile.mkdtemp(prefix="karte-rr2-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.other, ignore_errors=True))

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

    def test_every_builtin_verb_resolves_the_root_exactly_once(self):
        subparsers = next(a for a in cli.build_parser()._actions if a.dest == "verb")
        self.assertEqual(
            {"ingest-review", "render", "append", "close-attempt", "check", "status"},
            set(subparsers.choices),
        )
        for verb, parser in subparsers.choices.items():
            with self.subTest(verb=verb):
                func = parser.get_default("func")
                with mock.patch(
                    "karte.verb_boundary.repo_root_of", side_effect=OSError("stop here")
                ) as resolver, mock.patch("sys.stderr"):
                    self.assertEqual(4, func(argparse.Namespace()))
                self.assertEqual(1, resolver.call_count)


if __name__ == "__main__":
    unittest.main()
