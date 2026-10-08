import fnmatch
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ROLES = ("main", "pr-reviewer", "issue-implementer", "issue-fixer")


class NativeMergePermissionTests(unittest.TestCase):
    def test_claude_native_rules_cover_shell_and_mcp_for_every_role(self):
        settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        denies = settings["permissions"]["deny"]
        bash_patterns = [item[5:-1] for item in denies if item.startswith("Bash(")]
        commands = (
            "gh pr merge 123 --merge", "rtk gh pr merge 123",
            "rtk proxy gh pr merge 123", "git merge", "git merge topic",
            "git merge --no-ff topic", "rtk git merge",
            "rtk git merge --no-ff topic", "rtk proxy git merge",
            "rtk proxy git merge --no-ff topic",
            "gh -R owner/repo pr merge 123 --merge",
            "gh --repo owner/repo pr merge 123 --merge",
            "rtk gh -R owner/repo pr merge 123 --merge",
            "rtk gh --repo owner/repo pr merge 123 --merge",
            "rtk proxy gh -R owner/repo pr merge 123 --merge",
            "rtk proxy gh --repo owner/repo pr merge 123 --merge",
        )
        for role in ROLES:
            for command in commands:
                with self.subTest(role=role, command=command):
                    self.assertTrue(any(fnmatch.fnmatchcase(command, p) for p in bash_patterns))
            for tool in (
                "mcp__codex_apps__github_merge_pull_request",
                "mcp__codex_apps__github_enable_auto_merge",
                "mcp__github__merge_pull_request",
                "mcp__github__enable_auto_merge",
                "mcp__github__enable_pull_request_auto_merge",
                "github_merge_pull_request",
                "github_enable_auto_merge",
            ):
                self.assertIn(tool, denies)

    def test_claude_globs_do_not_reject_merge_as_a_read_argument(self):
        settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        patterns = [item[5:-1] for item in settings["permissions"]["deny"] if item.startswith("Bash(")]
        for command in (
            "git show merge", "git log merge", "git merge-base main topic",
            "git merge-tree main topic", "git merge-file current base other",
            "rtk git merge-base main topic", "rtk proxy git merge-base main topic",
        ):
            with self.subTest(command=command):
                self.assertFalse(any(fnmatch.fnmatchcase(command, pattern) for pattern in patterns))
        for command in ("git merge", "git merge topic", "git merge --no-ff topic"):
            with self.subTest(command=command):
                self.assertTrue(any(fnmatch.fnmatchcase(command, pattern) for pattern in patterns))


if __name__ == "__main__":
    unittest.main()
