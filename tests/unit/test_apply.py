"""TC-apply-001: P5 自動適用（finding 単位コミット／失敗時 rollback＝S4）。実 git。"""
import shutil
import tempfile
import unittest
from pathlib import Path

from review_system.domain.enums import ApplicationMode
from review_system.domain.ids import ExecutionId, RuleId, Location, LineRange
from review_system.domain.review import Finding, SuggestedFix, TriagedFinding
from review_system.domain.result import Success, Failure
from review_system.persistence.workspace_git import GitWorkspaceRepository
from review_system.core.apply import apply_auto

_HAS_GIT = shutil.which("git") is not None


def _auto(rule, file, new_content):
    f = Finding(RuleId(rule), Location(Path(file), LineRange(1, 1)), "r",
                suggested_fix=SuggestedFix("fix", new_content))
    return TriagedFinding(f, ApplicationMode.AUTO_FIX_LOG_ONLY)


@unittest.skipUnless(_HAS_GIT, "git バイナリが必要（DD5）")
class TestApplyAuto(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.repo = GitWorkspaceRepository(self.root)
        self.exec = ExecutionId("2026x-abc")
        self.targets = {"a.py": "uc = 0\n"}

    def test_applies_finding_unit_commits(self):
        out = apply_auto(self.exec, (_auto("naming", "a.py", "user_count = 0\n"),),
                         self.targets, self.repo, "now")
        self.assertIsInstance(out, Success)
        self.assertEqual(len(out.value), 1)
        self.assertEqual((self.repo.workdir(self.exec) / "a.py").read_text(), "user_count = 0\n")

    def test_failure_rolls_back_all(self):               # S4：存在しないパス→失敗→書込ゼロ
        out = apply_auto(self.exec,
                         (_auto("naming", "a.py", "ok\n"), _auto("x", "missing/b.py", "boom\n")),
                         self.targets, self.repo, "now")
        self.assertIsInstance(out, Failure)
        self.assertEqual((self.repo.workdir(self.exec) / "a.py").read_text(), "uc = 0\n")  # 全戻し

    def test_malicious_finding_path_fail_close(self):    # #2/#4：LLM 由来の脱出パス→fail-close＋rollback
        out = apply_auto(self.exec,
                         (_auto("naming", "a.py", "ok\n"), _auto("x", "../escape", "evil\n")),
                         self.targets, self.repo, "now")
        self.assertIsInstance(out, Failure)
        self.assertEqual((self.repo.workdir(self.exec) / "a.py").read_text(), "uc = 0\n")
        self.assertFalse((self.repo.workdir(self.exec).parent / "escape").exists())  # 外へ書かれない

    def test_open_failure_fail_close(self):              # #4：open 自体の失敗も例外漏れせず Failure
        out = apply_auto(ExecutionId("e2"), (_auto("naming", "a.py", "ok\n"),),
                         {"/etc/evil": "x"}, self.repo, "now")
        self.assertIsInstance(out, Failure)


if __name__ == "__main__":
    unittest.main()
