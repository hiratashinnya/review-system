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
    ("git", "merge", "topic"),
    ("rtk", "git", "merge", "topic"),
    ("rtk", "proxy", "git", "merge", "topic"),
)
READ_COMMANDS = (
    ("git", "-C", "/tmp/repo", "status", "--short"),
    ("gh", "pr", "view", "123"),
    ("gh", "--repo", "owner/repo", "pr", "view", "123"),
    ("gh", "api", "--method", "GET", "repos/o/r/issues/123"),
    ("gh", "api", "graphql", "-F", "query={ viewer { login } }"),
)


@unittest.skipUnless(shutil.which("codex"), "Codex CLI is required for native policy checks")
class CodexExecpolicyRuleTests(unittest.TestCase):
    def check_command(self, command):
        rule_files = [RULES]
        inherited = Path.home() / ".codex/rules/default.rules"
        if inherited.is_file():
            rule_files.append(inherited)
        args = [shutil.which("codex"), "execpolicy", "check", "--pretty"]
        for path in rule_files:
            args.extend(("--rules", str(path)))
        return subprocess.run(
            [*args, "--", *command], cwd=ROOT, capture_output=True, text=True
        )

    def test_native_checker_forbids_direct_and_wrapped_mutations(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.check_command(command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["decision"], "forbidden")

    def test_native_checker_does_not_forbid_read_only_commands(self):
        for command in READ_COMMANDS:
            with self.subTest(command=command):
                result = self.check_command(command)
                self.assertEqual(result.returncode, 0, result.stderr)
                result_payload = json.loads(result.stdout)
                self.assertNotEqual(result_payload.get("decision"), "forbidden")
                self.assertEqual(result_payload.get("matchedRules", []), [])


if __name__ == "__main__":
    unittest.main()
