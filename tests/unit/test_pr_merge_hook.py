import io
import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pr_merge_gate.classifier import MergeOperation, PreUseClassification
from pr_merge_gate.hook import run


ROOT = Path(__file__).resolve().parents[2]


def operation() -> MergeOperation:
    return MergeOperation(
        repository="example/repo",
        pr_number=50,
        merge_method="squash",
        transport="connector",
        commit_title=None,
        commit_message=None,
        expected_head_oid=None,
        operation_fingerprint="sha256:" + "1" * 64,
    )


def allow_evidence() -> dict:
    return {
        "policy_version": "pr-merge-pre-use/1",
        "result": "ALLOW",
        "reason": "NO_VIOLATION",
        "binding": {
            "repository": "example/repo",
            "pr_number": 50,
            "merge_method": "squash",
            "transport": "connector",
            "operation_fingerprint": "sha256:" + "1" * 64,
        },
        "blocker_evidence": {"invocation_id": "inv-1"},
        "fetched_at": "2026-08-10T00:00:00Z",
        "permit_issued": True,
        "next_action": "invoke intercepted merge exactly once",
    }


class HookTest(unittest.TestCase):
    def invoke(self, payload: dict, audit_file: Path):
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run(stdin=stdin, stdout=stdout, stderr=stderr, audit_file=audit_file)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_non_merge_operation_is_ignored_without_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            code, stdout, stderr = self.invoke(
                {"tool_name": "Bash", "tool_input": {"command": "gh issue view 50"}},
                target,
            )
            self.assertEqual((code, stdout, stderr), (0, "", ""))
            self.assertFalse(target.exists())

    def test_auto_merge_is_denied_and_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            code, stdout, stderr = self.invoke(
                {
                    "tool_name": "mcp__codex_apps__github_enable_auto_merge",
                    "tool_input": {"repository_full_name": "example/repo", "pr_number": 50},
                },
                target,
            )
            decision = json.loads(stdout)
            record = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")
            self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertIn("AUTO_MERGE_DENIED", decision["hookSpecificOutput"]["permissionDecisionReason"])
            self.assertEqual(record["reason"], "AUTO_MERGE_DENIED")
            self.assertFalse(record["merge_api_called"])
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_allow_is_audited_to_stderr_without_tool_result_mutation(self):
        merge = operation()
        classification = PreUseClassification(
            "merge", "CLASSIFIED", merge, merge.operation_fingerprint
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "pr_merge_gate.hook.classify_pre_use", return_value=classification
        ), patch(
            "pr_merge_gate.hook.resolve_github_token", return_value="token"
        ), patch(
            "pr_merge_gate.hook.evaluate_merge_operation", return_value=allow_evidence()
        ):
            target = Path(directory) / "audit.jsonl"
            code, stdout, stderr = self.invoke(
                {"tool_name": "mcp__codex_apps__github_merge_pull_request", "tool_input": {}},
                target,
            )
            self.assertEqual(code, 0)
            self.assertEqual(stdout, "")
            self.assertEqual(json.loads(stderr)["result"], "ALLOW")
            self.assertTrue(json.loads(target.read_text(encoding="utf-8"))["permit_issued"])

    def test_audit_integrity_failure_changes_allow_to_deny(self):
        merge = operation()
        classification = PreUseClassification(
            "merge", "CLASSIFIED", merge, merge.operation_fingerprint
        )
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            target.write_text("", encoding="utf-8")
            target.chmod(0o644)
            with patch(
                "pr_merge_gate.hook.classify_pre_use", return_value=classification
            ), patch(
                "pr_merge_gate.hook.resolve_github_token", return_value="token"
            ), patch(
                "pr_merge_gate.hook.evaluate_merge_operation", return_value=allow_evidence()
            ):
                _, stdout, stderr = self.invoke(
                    {"tool_name": "mcp__codex_apps__github_merge_pull_request", "tool_input": {}},
                    target,
                )
            self.assertEqual(stderr, "")
            decision = json.loads(stdout)
            self.assertIn(
                "HOOK_INTEGRITY_ERROR",
                decision["hookSpecificOutput"]["permissionDecisionReason"],
            )

    def test_codex_and_claude_install_the_same_pre_use_gate(self):
        codex = json.loads((ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        codex_text = json.dumps(codex)
        claude_text = json.dumps(claude)

        for text, script in (
            (codex_text, ".codex/hooks/pr-merge-gate.sh"),
            (claude_text, ".claude/hooks/pr-merge-gate.sh"),
        ):
            self.assertIn("PreToolUse", text)
            self.assertIn("github_merge_pull_request", text)
            self.assertIn("github_enable_auto_merge", text)
            self.assertIn(script, text)
            shell = (ROOT / script).read_text(encoding="utf-8")
            self.assertIn("python3 -m pr_merge_gate.hook", shell)


if __name__ == "__main__":
    unittest.main()
