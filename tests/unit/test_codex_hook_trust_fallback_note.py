"""Warnings identify when the trust check had to use its input path."""

from pathlib import Path
import tempfile
import unittest

from tests.unit.codex_hook_trust_fake_server import make_fake_codex
from tests.unit.codex_hook_trust_repo_support import (
    init_repository,
    make_failing_git_path,
    make_repository_pair,
    make_separate_git_dir_pair,
    write_hooks,
)
from tests.unit.codex_hook_trust_support import run_check


class CodexHookTrustFallbackNoteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.codex = make_fake_codex(self.temp.name)
        self.failing_git_path = make_failing_git_path(self.directory)

    def tearDown(self):
        self.temp.cleanup()

    def test_git_failure_notes_input_path_for_missing_hook_warning(self):
        repo = self.directory / "git-failure"
        init_repository(repo, 2)
        result = run_check(
            self.codex, "zero-hooks", repo=repo,
            extra_env={"PATH": self.failing_git_path},
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("定義 2 件に対し発見 0 件", result.stdout)
        self.assertIn(f"渡されたパス（{repo}）で検査しました", result.stdout)
        self.assertIn(
            "信頼記録の実キーはメインのパスのため、確認先が異なる場合があります。",
            result.stdout,
        )

    def test_git_failure_notes_input_path_for_untrusted_hook_warning(self):
        repo = self.directory / "untrusted-git-failure"
        init_repository(repo, 1)
        result = run_check(
            self.codex, "mixed", repo=repo,
            extra_env={"PATH": self.failing_git_path},
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("未信頼の Codex フック", result.stdout)
        self.assertIn(f"渡されたパス（{repo}）で検査しました", result.stdout)
        self.assertIn(
            "信頼記録の実キーはメインのパスのため、確認先が異なる場合があります。",
            result.stdout,
        )

    def test_separate_git_dir_linked_worktree_falls_back_with_note(self):
        main, worktree = make_separate_git_dir_pair(self.directory, 2)
        write_hooks(worktree, 5)
        result = run_check(self.codex, "zero-hooks", repo=worktree)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("定義 5 件に対し発見 0 件", result.stdout)
        self.assertIn(f"渡されたパス（{worktree}）で検査しました", result.stdout)
        self.assertIn(
            "信頼記録の実キーはメインのパスのため、確認先が異なる場合があります。",
            result.stdout,
        )
        self.assertIn(f'[projects."{worktree}"]', result.stdout)
        self.assertNotIn(f'[projects."{main}"]', result.stdout)

    def test_identified_main_checkout_has_no_fallback_note(self):
        main, worktree = make_repository_pair(self.directory, 2)
        write_hooks(worktree, 5)
        result = run_check(self.codex, "zero-hooks", repo=worktree)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(f'[projects."{main}"]', result.stdout)
        self.assertNotIn("メインのチェックアウトを特定できなかった", result.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
