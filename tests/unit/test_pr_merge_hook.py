import io
import json
import stat
import subprocess
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
            "head_oid": "a" * 40,
            "base_ref_name": "main",
            "default_branch": "main",
        },
        "graphql_closing_set": ["example/repo#7"],
        "delivered_message_closing_set": [],
        "closing_set": ["example/repo#7"],
        "findings": [
            {
                "code": "OPEN_BLOCKER",
                "subject": "example/repo#7",
                "path": ["example/repo#7", "example/repo#6"],
                "fingerprint": "sha256:" + "2" * 64,
                "waiver_id": "waiver-1",
            }
        ],
        "blocker_evidence": {"invocation_id": "inv-1"},
        "fetched_at": "2026-08-10T00:00:00Z",
        "permit_issued": True,
        "next_action": "invoke intercepted merge exactly once",
    }


class HookTest(unittest.TestCase):
    def invoke(self, payload: dict, audit_file: Path):
        payload = dict(payload)
        payload.setdefault("session_id", "session-1")
        payload.setdefault("turn_id", "turn-1")
        payload.setdefault("tool_use_id", "tool-1")
        payload.setdefault("hook_event_name", "PreToolUse")
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
            self.assertFalse(record["operation_dispatched"])
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

    def test_actions_free_pre_allow_call_and_post_response_are_correlated(self):
        payload = {
            "session_id": "session-e2e",
            "turn_id": "turn-e2e",
            "tool_use_id": "tool-e2e",
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__codex_apps__github_merge_pull_request",
            "tool_input": {
                "repository_full_name": "example/repo",
                "pr_number": 50,
                "merge_method": "squash",
            },
        }
        classified = __import__("pr_merge_gate.classifier", fromlist=["classify_pre_use"]).classify_pre_use(payload)
        permitted = allow_evidence()
        permitted["binding"]["operation_fingerprint"] = classified.operation.operation_fingerprint
        calls = []
        with tempfile.TemporaryDirectory() as directory, patch(
            "pr_merge_gate.hook.resolve_github_token", return_value="token"
        ), patch(
            "pr_merge_gate.hook.evaluate_merge_operation", return_value=permitted
        ):
            target = Path(directory) / "audit.jsonl"
            code, stdout, _ = self.invoke(payload, target)
            self.assertEqual((code, stdout), (0, ""))
            calls.append("managed merge invoked once")
            response = {"merged": True, "message": "secret-free result"}
            post_payload = dict(payload)
            post_payload["hook_event_name"] = "PostToolUse"
            post_payload["tool_response"] = response
            from pr_merge_gate.hook import post_run
            post_stdout = io.StringIO()
            post_stderr = io.StringIO()
            post_run(
                stdin=io.StringIO(json.dumps(post_payload)), stdout=post_stdout,
                stderr=post_stderr, audit_file=target,
            )
            records = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(calls, ["managed merge invoked once"])
        self.assertEqual(post_stdout.getvalue(), "")
        self.assertEqual([item["record_type"] for item in records], ["pre_use_decision", "post_use_completion"])
        self.assertFalse(records[0]["merge_api_called"])
        self.assertFalse(records[0]["operation_dispatched"])
        self.assertTrue(records[1]["merge_api_called"])
        self.assertTrue(records[1]["operation_dispatched"])
        self.assertEqual(records[0]["invocation_id"], records[1]["invocation_id"])
        self.assertEqual(records[1]["response_outcome"], "success")

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
            self.assertIn("PostToolUse", text)
            self.assertIn("github_merge_pull_request", text)
            self.assertIn("github_enable_auto_merge", text)
            self.assertIn(script, text)
            shell = (ROOT / script).read_text(encoding="utf-8")
            self.assertIn("python3 -m pr_merge_gate.hook", shell)

    def test_codex_and_claude_scripts_actually_fire_without_actions(self):
        payload = {
            "session_id": "session-probe",
            "turn_id": "turn-probe",
            "tool_use_id": "tool-probe",
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__codex_apps__github_enable_auto_merge",
            "tool_input": {"repository_full_name": "example/repo", "pr_number": 50},
        }
        for script in (
            ROOT / ".codex/hooks/pr-merge-gate.sh",
            ROOT / ".claude/hooks/pr-merge-gate.sh",
        ):
            with self.subTest(script=script), tempfile.TemporaryDirectory() as directory:
                script_payload = dict(payload)
                if ".claude" in script.parts:
                    script_payload.pop("turn_id")
                completed = subprocess.run(
                    ["bash", str(script)], input=json.dumps(script_payload), text=True,
                    cwd=ROOT, capture_output=True,
                    env={
                        "HOME": directory,
                        "XDG_STATE_HOME": directory,
                        "CLAUDE_PROJECT_DIR": str(ROOT),
                        "PATH": __import__("os").environ["PATH"],
                    },
                    check=False,
                )
                self.assertEqual(completed.returncode, 0)
                decision = json.loads(completed.stdout)
                self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
                audit = Path(directory) / "review-system/blocker-gate/audit.jsonl"
                record = json.loads(audit.read_text(encoding="utf-8"))
                self.assertEqual(record["hook_event_id"], "tool-probe")
                self.assertTrue(record["hook_asset_hash"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
