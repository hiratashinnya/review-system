"""permission profile の base 一致検査（D1）。"""

from pathlib import Path
import tempfile
import unittest

from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.profile_pin import verify_profile_pinned
from tests.unit.codex_worktree_exec_support import git, make_repository


class ProfilePinTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def assert_refused(self, worktree, role, error_id):
        with self.assertRaises(CodexExecError) as caught:
            verify_profile_pinned(worktree, role)
        self.assertEqual(caught.exception.error_id, error_id)

    def test_profile_identical_to_origin_main_is_accepted(self):
        _, worktree = make_repository(self.directory)
        for role in ("issue-implementer", "issue-fixer"):
            with self.subTest(role=role):
                verify_profile_pinned(worktree, role)

    def test_locally_edited_profile_is_refused(self):
        _, worktree = make_repository(self.directory)
        config = worktree / ".codex" / "config.toml"
        config.write_text(config.read_text(encoding="utf-8") + "\n# local edit\n", encoding="utf-8")
        self.assert_refused(worktree, "issue-implementer", "CODEX_EXEC_PROFILE_DRIFT")

    def test_committed_but_unmerged_profile_change_is_refused(self):
        # commit 済みでも origin/main に入っていない profile は使わない。
        _, worktree = make_repository(self.directory)
        config = worktree / ".codex" / "config.toml"
        config.write_text(config.read_text(encoding="utf-8").replace('"deny"', '"read"', 1), encoding="utf-8")
        git(worktree, "commit", "-q", "-am", "weaken profile")
        self.assert_refused(worktree, "issue-fixer", "CODEX_EXEC_PROFILE_DRIFT")

    def test_missing_or_symlinked_profile_is_refused(self):
        _, worktree = make_repository(self.directory)
        config = worktree / ".codex" / "config.toml"
        target = self.directory / "elsewhere.toml"
        target.write_bytes(config.read_bytes())
        config.unlink()
        self.assert_refused(worktree, "issue-implementer", "CODEX_EXEC_PROFILE_MISSING")
        config.symlink_to(target)
        self.assert_refused(worktree, "issue-implementer", "CODEX_EXEC_PROFILE_MISSING")

    def test_unresolvable_base_is_refused(self):
        main, worktree = make_repository(self.directory)
        git(main, "update-ref", "-d", "refs/remotes/origin/main")
        self.assert_refused(worktree, "issue-implementer", "CODEX_EXEC_PROFILE_BASE_UNRESOLVED")

    def test_profile_without_the_role_table_is_refused(self):
        _, worktree = make_repository(
            self.directory, profile='[permissions.other]\nextends = ":workspace"\n'
        )
        self.assert_refused(worktree, "issue-implementer", "CODEX_EXEC_PROFILE_UNDEFINED")


if __name__ == "__main__":
    unittest.main()
