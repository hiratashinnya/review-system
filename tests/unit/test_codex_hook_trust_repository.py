"""Repository path behavior for Codex hook trust checks."""

from pathlib import Path
import tempfile
import unittest

from tests.unit.codex_hook_trust_repo_support import (
    init_repository,
    make_repository_pair,
    read_trace,
    write_hooks,
)
from tests.unit.codex_hook_trust_support import make_fake_codex, run_check


class CodexHookTrustRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.codex = make_fake_codex(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_worktree_uses_main_checkout_for_config_warning_and_app_server(self):
        main, worktree = make_repository_pair(self.directory, 2)
        write_hooks(worktree, 5)
        result, trace = self._run_zero_hooks(worktree, "worktree")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("定義 2 件に対し発見 0 件", result.stdout)
        self.assertIn(f'[projects."{main}"]', result.stdout)
        self.assertNotIn(str(worktree), result.stdout)
        self._assert_trace(trace, main)

    def test_regular_repository_keeps_its_path(self):
        repo = self.directory / "ordinary"
        init_repository(repo, 3)
        result, trace = self._run_zero_hooks(repo, "ordinary")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("定義 3 件に対し発見 0 件", result.stdout)
        self.assertIn(f'[projects."{repo}"]', result.stdout)
        self._assert_trace(trace, repo)

    def test_git_managed_external_directory_falls_back_to_given_path(self):
        repo = self.directory / "outside-git"
        write_hooks(repo, 4)
        result, trace = self._run_zero_hooks(repo, "outside-git")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("定義 4 件に対し発見 0 件", result.stdout)
        self.assertIn(f'[projects."{repo}"]', result.stdout)
        self._assert_trace(trace, repo)

    def _run_zero_hooks(self, repo, name):
        trace = self.directory / f"{name}-app-server.jsonl"
        result = run_check(
            self.codex, "zero-hooks", repo=repo,
            extra_env={"FAKE_CODEX_TRACE": str(trace)},
        )
        return result, trace

    def _assert_trace(self, trace, repo):
        self.assertEqual(read_trace(trace), {
            "cwd": str(repo),
            "cwds": [str(repo)],
            "config_path": str(repo / ".codex" / "hooks.json"),
        })


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
