"""TC-workspace-001: 内部 git ワークスペース（DS3・S4）。実 git を tmp で動かす。"""
import shutil
import tempfile
import unittest
from pathlib import Path

from review_system.domain.ids import ExecutionId
from review_system.persistence.workspace_git import GitWorkspaceRepository

_HAS_GIT = shutil.which("git") is not None


@unittest.skipUnless(_HAS_GIT, "git バイナリが必要（DD5 前提）")
class TestGitWorkspace(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.repo = GitWorkspaceRepository(self.root)
        self.exec = ExecutionId("2026-06-07T00:00:00-abcdef012345")
        self.repo.open(self.exec, {"a.py": "uc = 0\n"})

    def _content(self, rel):
        return (self.repo.workdir(self.exec) / rel).read_text()

    def test_commit_fix_is_finding_unit(self):           # finding 単位コミット（Q3/S4）
        ref = self.repo.commit_fix(self.exec, "naming@a.py:1-1", "a.py", "user_count = 0\n")
        self.assertTrue(ref)
        self.assertEqual(self._content("a.py"), "user_count = 0\n")

    def test_revert_single_finding(self):                # 個別 revert（O-6）
        ref = self.repo.commit_fix(self.exec, "naming@a.py:1-1", "a.py", "user_count = 0\n")
        self.repo.revert(self.exec, ref)
        self.assertEqual(self._content("a.py"), "uc = 0\n")   # 元へ戻る

    def test_rollback_execution_all_or_nothing(self):    # S4：実行内失敗→書込ゼロ
        self.repo.commit_fix(self.exec, "f1@a.py:1-1", "a.py", "step1\n")
        self.repo.rollback_execution(self.exec)
        self.assertEqual(self._content("a.py"), "uc = 0\n")   # 基準点へ全戻し

    def test_commit_fix_rejects_absolute_path(self):     # #2/#3 パストラバーサル（絶対）
        with self.assertRaises(ValueError):
            self.repo.commit_fix(self.exec, "f@x", "/etc/evil", "boom\n")

    def test_commit_fix_rejects_parent_escape(self):     # #2/#3 パストラバーサル（..）
        with self.assertRaises(ValueError):
            self.repo.commit_fix(self.exec, "f@x", "../escape.txt", "boom\n")

    def test_open_rejects_absolute_path(self):           # #2 open も検証
        with self.assertRaises(ValueError):
            self.repo.open(ExecutionId("other"), {"/etc/evil": "x"})


if __name__ == "__main__":
    unittest.main()
