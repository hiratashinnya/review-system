"""Issue #822: no-op issue marker + dummy harness output through real dispatch validation."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_worktree_exec.source_snapshot import verify_untracked_sources
from issue_start.gate_support import IssueStartError
from issue_start.phase_dispatch import validate_phase_dispatch
from issue_start.readonly_workspace import prepare_readonly_workspace
from tests.unit.codex_worktree_exec_support import git, make_repository

ISSUE = 822
REPO = Path(__file__).resolve().parents[2]


class DummyDispatchIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.source, self.target = make_repository(self.directory)
        self.quarantine = self.directory / "preserved"
        self.quarantine.mkdir()

    def put(self, root, name, content=b"harmless dummy"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def marker(self):
        oid = git(self.source, "rev-parse", "HEAD")
        input_data = b"dummy validation-only issue 822; no external actions"
        self.put(self.source, "tmp/issue.txt", input_data)
        self.put(self.source, "tmp/prompt.md", b"Only validate; no agent calls.")
        binding = {
            "recipient": "issue-investigator", "input_file": "tmp/issue.txt",
            "input_digest": hashlib.sha256(input_data).hexdigest(),
            "snapshot_oid": oid, "issue": ISSUE, "run_id": "dummy-822",
            "target_key": "dummy-822", "investigation_reason": "isolation smoke",
        }
        approval = {
            "recipient": "issue-investigator", "run_id": "dummy-822",
            "issue": ISSUE, "target_key": "dummy-822", "snapshot_oid": oid,
            "context_id": "dummy-not-a-real-approval", "owner_approved": True,
            "reviews": [],
        }
        self.put(self.source, "tmp/binding.json", json.dumps(binding).encode())
        self.put(self.source, "tmp/approval.json", json.dumps(approval).encode())
        return {"binding_file": "tmp/binding.json", "approval_file": "tmp/approval.json"}

    def recover(self, worktree):
        return subprocess.run(
            [sys.executable, "-B", "-m", "codex_worktree_exec.untracked_recovery",
             "--worktree", str(worktree), "--quarantine-parent",
             str(self.quarantine), "--apply"],
            cwd=REPO, text=True, capture_output=True, check=True,
        )

    def test_generated_artifacts_block_then_one_command_recovers_phase_dispatch(self):
        marker = self.marker()
        locks = (".claude/scheduled_tasks.lock", "tmp/_karte/.writer.lock",
                 "issue_start/adr/.write.lock", "issue_start/adr/.file-issue.lock")
        for name in locks:
            self.put(self.source, name)
        artifacts = {
            "tmp/_adr-notify/" + "a" * 64 + ".root": b"ADR pointer",
            "tmp/pr-diffs/pr-822-dummy.diff": b"diff --git a/x b/x\n",
            "tmp/_feedback/FBK-822-smoke.toml": b"status = 'dummy'\n",
            ".coverage": b"dummy-coverage",
            "htmlcov/index.html": b"dummy-report",
            ".serena/.gitignore": b"dummy-serena-state",
            "tmp/manual.out": b"temporary output",
        }
        for name, content in artifacts.items():
            self.put(self.source, name, content)
        with self.assertRaises(IssueStartError) as error:
            validate_phase_dispatch(marker, "issue-investigator", self.source)
        self.assertEqual(error.exception.reason, "ISSUE_START_PHASE_BINDING_INVALID")
        for term in ("unapproved_tmp count=4", "coverage_output count=2",
                     "tool_state count=1"):
            self.assertIn(term, error.exception.detail)
        self.recover(self.source)
        self.assertEqual(validate_phase_dispatch(
            marker, "issue-investigator", self.source)["issue"], ISSUE)
        for name in locks:
            self.assertTrue((self.source / name).is_file(), name)
        saved = list(self.quarantine.glob("review-system-quarantine-*"))
        self.assertEqual(len(saved), 1)
        for name, content in artifacts.items():
            self.assertFalse((self.source / name).exists(), name)
            self.assertEqual((saved[0] / name).read_bytes(), content)

    def test_unapproved_source_is_not_quarantined_even_if_gitignored(self):
        self.put(self.source, ".gitignore", b"*.py\n")
        git(self.source, "add", ".gitignore")
        git(self.source, "commit", "-qm", "dummy ignore rule")
        marker = self.marker()
        extra = self.put(self.source, "unauthorized.py", b"print('no-op')\n")
        with self.assertRaisesRegex(IssueStartError, "unapproved_source"):
            validate_phase_dispatch(marker, "issue-investigator", self.source)
        self.recover(self.source)
        self.assertEqual(extra.read_bytes(), b"print('no-op')\n")
        with self.assertRaisesRegex(IssueStartError, "unapproved_source"):
            validate_phase_dispatch(marker, "issue-investigator", self.source)

    def test_readonly_source_and_target_both_refuse_generated_artifacts(self):
        marker = self.marker()
        self.put(self.source, ".coverage", b"source")
        self.put(self.target, "tmp/_adr-notify/dummy.root", b"target")
        with patch("issue_start.readonly_workspace.parse_readonly_phase",
                   return_value=None):
            with self.assertRaisesRegex(IssueStartError, "coverage_output"):
                prepare_readonly_workspace(
                    self.source, self.target, "issue-investigator", marker, "tmp/prompt.md")
            self.recover(self.source)
            with self.assertRaisesRegex(IssueStartError, "unapproved_tmp"):
                prepare_readonly_workspace(
                    self.source, self.target, "issue-investigator", marker, "tmp/prompt.md")
            self.recover(self.target)
            result = prepare_readonly_workspace(
                self.source, self.target, "issue-investigator", marker, "tmp/prompt.md")
            self.assertEqual(result, self.target)
