"""Exercise project command rules with Codex's native local policy checker."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / ".codex/rules/default.rules"
COMMANDS = (
    ("gh", "pr", "merge", "123"),
    ("rtk", "gh", "pr", "merge", "123"),
    ("rtk", "proxy", "gh", "pr", "merge", "123"),
    ("gh", "-R", "owner/repo", "pr", "merge", "123"),
    ("gh", "--repo", "owner/repo", "pr", "merge", "123"),
    ("rtk", "gh", "-R", "owner/repo", "pr", "merge", "123"),
    ("rtk", "gh", "--repo", "owner/repo", "pr", "merge", "123"),
    ("rtk", "proxy", "gh", "-R", "owner/repo", "pr", "merge", "123"),
    ("rtk", "proxy", "gh", "--repo", "owner/repo", "pr", "merge", "123"),
    ("gh", "-R", "owner/repo", "pr", "view", "123"),
    ("git", "merge", "topic"),
    ("rtk", "git", "merge", "topic"),
    ("rtk", "proxy", "git", "merge", "topic"),
    ("git", "-C", "/tmp/repo", "merge", "topic"),
    ("rtk", "git", "-C", "/tmp/repo", "merge", "topic"),
    ("rtk", "proxy", "git", "-C", "/tmp/repo", "merge", "topic"),
    ("git", "-C", "/tmp/repo", "status", "--short"),
    ("git", "-c", "alias.m=merge", "m", "topic"),
    ("rtk", "git", "-c", "alias.m=merge", "m", "topic"),
    ("rtk", "proxy", "git", "-c", "alias.m=merge", "m", "topic"),
    ("gh", "api", "--method", "PUT", "repos/o/r/pulls/1/merge"),
    ("gh", "api", "graphql", "-F", "query=@payload.txt"),
    ("rtk", "gh", "api", "graphql", "-F", "query=@payload.txt"),
    ("rtk", "proxy", "gh", "api", "graphql", "-F", "query=@payload.txt"),
)


@unittest.skipUnless(shutil.which("codex"), "Codex CLI is required for native policy checks")
class CodexExecpolicyRuleTests(unittest.TestCase):
    def test_native_checker_forbids_direct_and_wrapped_mutations(self):
        rule_files = [RULES]
        inherited = Path.home() / ".codex/rules/default.rules"
        if inherited.is_file():
            rule_files.append(inherited)
        for command in COMMANDS:
            with self.subTest(command=command):
                args = [shutil.which("codex"), "execpolicy", "check", "--pretty"]
                for path in rule_files:
                    args.extend(("--rules", str(path)))
                result = subprocess.run(
                    [*args, "--", *command], cwd=ROOT, capture_output=True, text=True
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["decision"], "forbidden")


if __name__ == "__main__":
    unittest.main()
