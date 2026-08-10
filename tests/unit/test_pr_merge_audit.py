import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from pr_merge_gate.audit import AuditError, append_completion, append_decision, audit_path


def evidence() -> dict:
    return {
        "policy_version": "pr-merge-pre-use/1",
        "classifier_version": "1.1",
        "hook_asset_hash": "sha256:" + "9" * 64,
        "hook_event_id": "tool-1",
        "invocation_id": "invocation-1",
        "result": "DENY",
        "reason": "BLOCKER_VIOLATION",
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
        "blocker_evidence": {"invocation_id": "inv-1"},
        "graphql_closing_set": ["example/repo#7"],
        "delivered_message_closing_set": ["example/repo#8"],
        "closing_set": ["example/repo#7", "example/repo#8"],
        "findings": [
            {
                "code": "OPEN_BLOCKER", "subject": "example/repo#7",
                "path": ["example/repo#7", "example/repo#6"],
                "fingerprint": "sha256:" + "2" * 64, "waiver_id": None,
            }
        ],
        "fetched_at": "2026-08-10T00:00:00Z",
        "permit_issued": False,
        "next_action": "fix blockers",
        "raw_command": "gh pr merge 50 --body secret",
        "token": "secret",
    }


class AuditTest(unittest.TestCase):
    def test_audit_path_prefers_xdg_and_rejects_relative_root(self):
        self.assertEqual(
            audit_path({"XDG_STATE_HOME": "/tmp/state"}),
            Path("/tmp/state/review-system/blocker-gate/audit.jsonl"),
        )
        with self.assertRaises(AuditError):
            audit_path({"XDG_STATE_HOME": "relative"})

    def test_append_is_private_durable_jsonl_without_raw_input(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state" / "audit.jsonl"
            append_decision(evidence(), path=target)
            record = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(target.parent.stat().st_mode), 0o700)
            self.assertEqual(record["reason"], "BLOCKER_VIOLATION")
            self.assertFalse(record["merge_api_called"])
            self.assertEqual(record["head_oid"], "a" * 40)
            self.assertEqual(record["base_ref_name"], "main")
            self.assertEqual(record["default_branch"], "main")
            self.assertEqual(record["closing_set"], ["example/repo#7", "example/repo#8"])
            self.assertEqual(record["dependency_paths"], [["example/repo#7", "example/repo#6"]])
            self.assertEqual(record["classifier_version"], "1.1")
            self.assertEqual(record["hook_event_id"], "tool-1")
            serialized = json.dumps(record)
            self.assertNotIn("secret", serialized)
            self.assertNotIn("raw_command", serialized)

    def test_completion_requires_matching_permit_and_redacts_response(self):
        allowed = evidence()
        allowed["result"] = "ALLOW"
        allowed["permit_issued"] = True
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            append_decision(allowed, path=target)
            append_completion(
                invocation_id="invocation-1", hook_event_id="tool-1",
                operation_fingerprint="sha256:" + "1" * 64,
                classifier_version="1.1", asset_hash="sha256:" + "9" * 64,
                tool_name="github_merge_pull_request",
                tool_response={"merged": True, "message": "sensitive-response"},
                path=target,
            )
            records = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(records[1]["record_type"], "post_use_completion")
            self.assertTrue(records[1]["merge_api_called"])
            self.assertEqual(records[1]["response_outcome"], "success")
            self.assertNotIn("sensitive-response", json.dumps(records[1]))
            with self.assertRaises(AuditError):
                append_completion(
                    invocation_id="missing", hook_event_id="tool-2",
                    operation_fingerprint="sha256:" + "1" * 64,
                    classifier_version="1.1", asset_hash="sha256:" + "9" * 64,
                    tool_name="github_merge_pull_request", tool_response={}, path=target,
                )

    def test_append_rejects_preexisting_file_with_unsafe_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            target.write_text("", encoding="utf-8")
            os.chmod(target, 0o644)
            with self.assertRaises(AuditError):
                append_decision(evidence(), path=target)


if __name__ == "__main__":
    unittest.main()
