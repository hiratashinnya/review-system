"""project trust の事前検査（要設計2）。trust の記録キーは main checkout のパス。"""

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from codex_hook_trust.repository import MainCheckoutResolution
from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.project_trust import codex_home, verify_project_trusted
from tests.unit.codex_worktree_exec_support import make_repository, write_trust


class ProjectTrustTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.main, self.worktree = make_repository(self.directory)
        self.home = self.directory / "codex-home"

    def tearDown(self):
        self.temp.cleanup()

    def assert_refused(self, error_id):
        with self.assertRaises(CodexExecError) as caught:
            verify_project_trusted(self.worktree, self.home)
        self.assertEqual(caught.exception.error_id, error_id)

    def test_trusted_main_checkout_is_accepted_for_its_linked_worktree(self):
        write_trust(self.home, self.main)
        verify_project_trusted(self.worktree, self.home)

    def test_untrusted_level_is_refused(self):
        write_trust(self.home, self.main, level="untrusted")
        self.assert_refused("CODEX_EXEC_PROJECT_UNTRUSTED")

    def test_trusting_only_another_path_is_refused(self):
        write_trust(self.home, self.directory / "other")
        self.assert_refused("CODEX_EXEC_PROJECT_UNTRUSTED")

    def test_missing_or_broken_config_is_unresolved(self):
        self.assert_refused("CODEX_EXEC_TRUST_UNRESOLVED")
        self.home.mkdir()
        (self.home / "config.toml").write_text("[projects\n", encoding="utf-8")
        self.assert_refused("CODEX_EXEC_TRUST_UNRESOLVED")

    def test_unidentified_main_checkout_is_unresolved(self):
        # 渡されたパスへのフォールバック（identified=False）を trust の根拠にしない。
        write_trust(self.home, self.worktree)
        fallback = MainCheckoutResolution(self.worktree, False)
        with mock.patch(
            "codex_worktree_exec.project_trust.resolve_main_checkout", return_value=fallback
        ):
            self.assert_refused("CODEX_EXEC_TRUST_UNRESOLVED")

    def test_codex_home_follows_the_environment(self):
        self.assertEqual(codex_home({"CODEX_HOME": "/srv/codex"}), Path("/srv/codex"))
        self.assertEqual(codex_home({}), Path.home() / ".codex")
        self.assertEqual(codex_home({"CODEX_HOME": ""}), Path.home() / ".codex")


if __name__ == "__main__":
    unittest.main()
