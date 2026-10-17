"""明示available fixtureでread-only工程がworktree台帳を書かず受理される。"""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from issue_start.gate_dispatch import parse_dispatch_payload
from issue_start.gate_manifest import ENTRYPOINT_MANIFEST
from issue_start.gate_support import IsolationOnlyAck
from issue_start.gated_roles import READ_ONLY_ROLES
from issue_start.hook_early import handle_early_request
from issue_start.phase_tool_gate import decision
from issue_start.readonly_phase_ack import ReadOnlyPhaseAck
from tests.unit.codex_worktree_exec_support import git, make_repository


class ReadonlyPhaseDispatchTests(unittest.TestCase):
    def test_shared_checkout_needs_no_isolation_and_creates_no_completion_handoff(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, _ = make_repository(Path(temporary))
            oid = git(root, "rev-parse", "HEAD")
            (root / "tmp").mkdir()
            (root / "tmp/issue.txt").write_bytes(b"issue")
            binding = dict(recipient="issue-investigator", input_file="tmp/issue.txt",
                           input_digest=hashlib.sha256(b"issue").hexdigest(), snapshot_oid=oid,
                           issue=371, run_id="r1", target_key="issue-371",
                           investigation_reason="原因未確定のため調査")
            approval = dict(recipient="issue-investigator", run_id="r1", issue=371,
                            target_key="issue-371", snapshot_oid=oid, context_id="investigator-1",
                            owner_approved=True, reviews=[])
            (root / "tmp/binding.json").write_text(json.dumps(binding))
            (root / "tmp/approval.json").write_text(json.dumps(approval))
            manifest = json.loads(ENTRYPOINT_MANIFEST.read_text())
            for entry in manifest["readonly"]:
                entry["binding_transports"]["claude"]["availability"] = "available"
            manifest_path = root / "tmp/manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            marker = "ISSUE_PHASE_INPUT_V1=" + json.dumps(dict(
                binding_file="tmp/binding.json", approval_file="tmp/approval.json"))
            before = sorted(str(path) for path in root.rglob("*"))
            with patch("issue_start.gate_manifest.ENTRYPOINT_MANIFEST", manifest_path):
                ack = parse_dispatch_payload(dict(tool_name="Agent", tool_input=dict(
                    subagent_type="issue-investigator", prompt=marker)), cwd=root)
            self.assertIsInstance(ack, ReadOnlyPhaseAck)
            recorder = Mock(side_effect=AssertionError("read-only must not write ownership ledger"))
            output = io.StringIO()
            result = handle_early_request(
                ack, isolation_ack_type=IsolationOnlyAck, policy_version="issue-start/2.0",
                residue={}, stamp=datetime.now(timezone.utc), cwd=root, ledger_root=root,
                record_isolation_entry=recorder, stderr=output)
            self.assertEqual(result, 0)
            self.assertIn("READ_ONLY_PHASE", output.getvalue())
            recorder.assert_not_called()
            self.assertEqual(before, sorted(str(path) for path in root.rglob("*")))

    def test_every_readonly_role_is_denied_direct_edit_tools(self):
        for role in READ_ONLY_ROLES:
            with self.subTest(role=role):
                result = decision(dict(agent_type=role, tool_name="Edit"))
                self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIsNone(decision(dict(agent_type="test-writer", tool_name="Edit")))
