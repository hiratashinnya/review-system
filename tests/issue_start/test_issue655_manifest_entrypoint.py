"""Issue #655 AC12: real readonly manifest transport + categorized failure."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_worktree_exec.untracked_recovery import main as recover
from issue_start.gate_dispatch import parse_dispatch_payload
from issue_start.gate_manifest import ENTRYPOINT_MANIFEST
from issue_start.gate_support import IssueStartError
from issue_start.readonly_phase_ack import ReadOnlyPhaseAck
from tests.unit.codex_worktree_exec_support import git, make_repository


class ReadonlyManifestRecoveryTests(unittest.TestCase):
    def test_actual_readonly_manifest_dispatch_refuses_then_recovers(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, _ = make_repository(base)
            oid = git(root, "rev-parse", "HEAD")
            (root / "tmp").mkdir()
            payload = b"fixture only: issue 822"
            (root / "tmp/issue.txt").write_bytes(payload)
            binding = {
                "recipient": "issue-investigator", "input_file": "tmp/issue.txt",
                "input_digest": hashlib.sha256(payload).hexdigest(),
                "snapshot_oid": oid, "issue": 822, "run_id": "dummy-822",
                "target_key": "dummy-822", "investigation_reason": "fixture",
            }
            approval = {
                "recipient": "issue-investigator", "run_id": "dummy-822",
                "issue": 822, "target_key": "dummy-822", "snapshot_oid": oid,
                "context_id": "dummy-isolated", "owner_approved": True, "reviews": [],
            }
            (root / "tmp/binding.json").write_text(json.dumps(binding))
            (root / "tmp/approval.json").write_text(json.dumps(approval))
            manifest = json.loads(ENTRYPOINT_MANIFEST.read_text())
            for entry in manifest["readonly"]:
                entry["binding_transports"]["claude"]["availability"] = "available"
            path = base / "fixture-manifest.json"
            path.write_text(json.dumps(manifest))
            tool_input = {"subagent_type": "issue-investigator",
                          "prompt": "ISSUE_PHASE_INPUT_V1=" + json.dumps({
                              "binding_file": "tmp/binding.json",
                              "approval_file": "tmp/approval.json",
                          })}
            (root / ".coverage").write_text("dummy")
            (root / "htmlcov").mkdir()
            (root / "htmlcov" / "index.html").write_text("dummy")
            with patch("issue_start.gate_manifest.ENTRYPOINT_MANIFEST", path):
                with self.assertRaises(IssueStartError) as raised:
                    parse_dispatch_payload({"tool_name": "Agent", "tool_input": tool_input},
                                           cwd=root)
                self.assertIn("coverage_output count=2", raised.exception.detail)
                safe = base / "preserved"
                safe.mkdir()
                self.assertEqual(recover(["--worktree", str(root),
                                          "--quarantine-parent", str(safe), "--apply"]), 0)
                ack = parse_dispatch_payload({"tool_name": "Agent", "tool_input": tool_input},
                                             cwd=root)
                self.assertIsInstance(ack, ReadOnlyPhaseAck)
