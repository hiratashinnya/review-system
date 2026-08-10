import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from pr_merge_gate.audit import AuditError, append_decision, audit_path


def evidence() -> dict:
    return {
        "policy_version": "pr-merge-pre-use/1",
        "result": "DENY",
        "reason": "BLOCKER_VIOLATION",
        "binding": {
            "repository": "example/repo",
            "pr_number": 50,
            "merge_method": "squash",
            "transport": "connector",
            "operation_fingerprint": "sha256:" + "1" * 64,
        },
        "blocker_evidence": {"invocation_id": "inv-1"},
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
            serialized = json.dumps(record)
            self.assertNotIn("secret", serialized)
            self.assertNotIn("raw_command", serialized)

    def test_append_rejects_preexisting_file_with_unsafe_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            target.write_text("", encoding="utf-8")
            os.chmod(target, 0o644)
            with self.assertRaises(AuditError):
                append_decision(evidence(), path=target)


if __name__ == "__main__":
    unittest.main()
