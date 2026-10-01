"""Repository path behavior for Codex hook trust checks."""

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from codex_hook_trust.repository import resolve_main_checkout
from tests.unit.codex_hook_trust_repo_support import (
    init_bare_repository,
    init_repository,
    make_separate_git_dir_pair,
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

    def test_separate_git_dir_falls_back_when_git_lists_external_metadata(self):
        main, worktree = make_separate_git_dir_pair(self.directory, 2)
        write_hooks(worktree, 5)

        cases = ((main, "separate-main", 2), (worktree, "separate-linked", 5))
        for repo, name, defined_count in cases:
            with self.subTest(repo=repo):
                self.assertEqual(resolve_main_checkout(repo), repo)
                result, trace = self._run_zero_hooks(repo, name)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(f"定義 {defined_count} 件に対し発見 0 件", result.stdout)
                self.assertIn(f'[projects."{repo}"]', result.stdout)
                self._assert_trace(trace, repo)

    def test_regular_repository_keeps_its_path(self):
        repo = self.directory / "ordinary"
        init_repository(repo, 3)
        result, trace = self._run_zero_hooks(repo, "ordinary")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("定義 3 件に対し発見 0 件", result.stdout)
        self.assertIn(f'[projects."{repo}"]', result.stdout)
        self._assert_trace(trace, repo)

    def test_bare_repository_falls_back_to_given_path(self):
        repo = self.directory / "bare"
        init_bare_repository(repo, 3)
        result, trace = self._run_zero_hooks(repo, "bare")

        self.assertEqual(resolve_main_checkout(repo), repo)
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

    def test_git_failure_empty_output_and_missing_worktree_fall_back(self):
        repo = self.directory / "input-repository"
        repo.mkdir()
        responses = (
            subprocess.CompletedProcess([], 1, "", "git error"),
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess(
                [], 0, f"worktree {self.directory / 'missing'}\n\n", "",
            ),
        )

        for response in responses:
            with self.subTest(returncode=response.returncode, stdout=response.stdout):
                with patch(
                    "codex_hook_trust.repository.subprocess.run", return_value=response,
                ):
                    self.assertEqual(resolve_main_checkout(repo), repo)

    def test_missing_git_falls_back_to_given_path(self):
        repo = self.directory / "without-git"

        with patch(
            "codex_hook_trust.repository.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            self.assertEqual(resolve_main_checkout(repo), repo)

    def test_git_worktree_query_uses_argument_list_without_shell(self):
        repo = self.directory / "query-contract"
        repo.mkdir()
        response = subprocess.CompletedProcess([], 0, f"worktree {repo}\n\n", "")

        with patch(
            "codex_hook_trust.repository.subprocess.run", return_value=response,
        ) as run_git:
            self.assertEqual(resolve_main_checkout(repo), repo)

        run_git.assert_called_once_with(
            ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
            stdin=subprocess.DEVNULL,
            timeout=2,
        )

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
