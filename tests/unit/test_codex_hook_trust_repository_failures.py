"""Fallback behavior when Git cannot identify a usable main worktree."""

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from codex_hook_trust.repository import resolve_main_checkout


class CodexHookTrustRepositoryFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_git_failure_unparseable_output_and_missing_worktree_fall_back(self):
        repo = self.directory / "input-repository"
        repo.mkdir()
        missing = self.directory / "missing"
        responses = (
            subprocess.CompletedProcess([], 1, b"", b"git error"),
            subprocess.CompletedProcess([], 0, b"", b""),
            subprocess.CompletedProcess(
                [], 0, f"worktree {missing}\0\0".encode(), b"",
            ),
            subprocess.CompletedProcess([], 0, b"worktree \0\0", b""),
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

    def test_git_worktree_query_uses_nul_porcelain_without_shell(self):
        repo = self.directory / "query-contract"
        repo.mkdir()
        response = subprocess.CompletedProcess(
            [], 0, f"worktree {repo}\0HEAD deadbeef\0\0".encode(), b"",
        )

        with patch(
            "codex_hook_trust.repository.subprocess.run", return_value=response,
        ) as run_git:
            self.assertEqual(resolve_main_checkout(repo), repo)

        run_git.assert_called_once_with(
            ["git", "-C", str(repo), "worktree", "list", "--porcelain", "-z"],
            check=False,
            capture_output=True,
            text=False,
            shell=False,
            stdin=subprocess.DEVNULL,
            timeout=2,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
