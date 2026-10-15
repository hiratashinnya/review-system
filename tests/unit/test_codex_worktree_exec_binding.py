"""`-C` の束縛検査（D5）。実物の Git で linked worktree を作って確かめる。"""

from pathlib import Path
import subprocess
import tempfile
import unittest

from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.worktree_binding import bind_worktree
from tests.unit.codex_worktree_exec_support import add_worktree, make_repository


class WorktreeBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.main, self.worktree = make_repository(self.directory)

    def tearDown(self):
        self.temp.cleanup()

    def assert_refused(self, requested, cwd, error_id, **kwargs):
        with self.assertRaises(CodexExecError) as caught:
            bind_worktree(requested, cwd, **kwargs)
        self.assertEqual(caught.exception.error_id, error_id)

    def test_own_linked_worktree_is_accepted(self):
        self.assertEqual(bind_worktree(Path("."), self.worktree), self.worktree)
        self.assertEqual(bind_worktree(self.worktree, self.worktree), self.worktree)

    def test_subdirectory_cwd_binds_to_its_worktree_root(self):
        subdirectory = self.worktree / "pkg"
        subdirectory.mkdir()
        self.assertEqual(bind_worktree(self.worktree, subdirectory), self.worktree)

    def test_main_checkout_is_refused(self):
        # main worktree は linked worktree の列挙に入らない（主文脈の checkout を Codex に渡さない）。
        self.assert_refused(Path("."), self.main, "CODEX_EXEC_WORKTREE_UNREGISTERED")

    def test_another_worktree_than_the_callers_is_refused(self):
        other = add_worktree(self.main, "agent-other")
        self.assert_refused(other, self.worktree, "CODEX_EXEC_WORKTREE_CWD_MISMATCH")

    def test_missing_path_is_refused(self):
        self.assert_refused(self.directory / "absent", self.worktree, "CODEX_EXEC_WORKTREE_MISSING")

    def test_cwd_outside_any_repository_is_refused(self):
        outside = self.directory / "outside"
        outside.mkdir()
        self.assert_refused(Path("."), outside, "CODEX_EXEC_CWD_NOT_IN_REPOSITORY")

    def test_unregistered_directory_is_refused_even_if_it_is_a_checkout(self):
        clone = self.directory / "clone"
        subprocess.run(["git", "clone", "-q", str(self.main), str(clone)], check=True, capture_output=True)
        self.assert_refused(Path("."), clone.resolve(), "CODEX_EXEC_WORKTREE_UNREGISTERED")

    def test_worktree_listing_failure_is_refused(self):
        def runner(argv, **kwargs):
            if "worktree" in argv:
                return subprocess.CompletedProcess(argv, 1, "", "boom")
            return subprocess.run(argv, **kwargs)

        self.assert_refused(Path("."), self.worktree, "CODEX_EXEC_GIT_FAILED", runner=runner)


if __name__ == "__main__":
    unittest.main()
