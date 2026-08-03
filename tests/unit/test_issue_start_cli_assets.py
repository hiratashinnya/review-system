"""Issue-start CLI I/O/exit codes と Codex/Claude asset parity。"""

import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from issue_start.cli import run


ROOT = Path(__file__).resolve().parents[2]
OID = "a" * 40
ARGS = [
    "--entrypoint", "issue-pipeline", "--repository", "example/repo",
    "--issue", "10", "--branch-name", "issue-297", "--base-ref", "main",
    "--base-oid", OID,
]


class CliContractTests(unittest.TestCase):
    def test_allow_block_error_exit_codes_and_json_stdout(self):
        for verdict, code, reason in [
            ("ALLOW", 0, "ISSUE_START_ALLOWED"),
            ("BLOCK", 10, "OPEN_BLOCKER"),
            ("ERROR", 20, "API_UNAVAILABLE"),
        ]:
            evidence = {
                "schema_version": "issue-start-evidence/1",
                "policy_version": "issue-start/1.0",
                "result": verdict,
                "exit_code": code,
                "reason": reason,
            }
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch("issue_start.cli.evaluate_issue_start", return_value=evidence):
                actual = run(ARGS, stdout=stdout, stderr=stderr, cwd=ROOT)
            self.assertEqual(actual, code)
            self.assertEqual(json.loads(stdout.getvalue())["result"], verdict)
            self.assertIn(reason, stderr.getvalue())


class AssetParityTests(unittest.TestCase):
    def test_both_harnesses_register_common_hook_core(self):
        codex = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        codex_matchers = {item.get("matcher") for item in codex["hooks"]["PreToolUse"]}
        claude_matchers = {item.get("matcher") for item in claude["hooks"]["PreToolUse"]}
        self.assertIn("spawn_agent", codex_matchers)
        self.assertIn("Task", claude_matchers)
        for script in [
            ROOT / ".codex" / "hooks" / "issue-start-gate.sh",
            ROOT / ".claude" / "hooks" / "issue-start-gate.sh",
        ]:
            self.assertIn("python3 -m issue_start.hook", script.read_text(encoding="utf-8"))

    def test_manifest_names_managed_and_unmanaged_paths(self):
        manifest = json.loads(
            (ROOT / "issue_start" / "managed-entrypoints-v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["managed"][0]["entrypoint"], "issue-pipeline")
        self.assertTrue(manifest["unmanaged"])


if __name__ == "__main__":
    unittest.main()
