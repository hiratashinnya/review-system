"""phase検証をmockせずproduction parserのIssue/repo/branch/OID結線を実gitで検査する。"""
import copy
import hashlib
import json
import subprocess
import unittest
from unittest.mock import patch
from issue_start.gate_dispatch import parse_dispatch_payload
from issue_start.gate_support import IssueStartError
from tests.unit import test_phase_dispatch_binding as phase_fixture
from tests.unit.codex_worktree_exec_support import git


class PhaseTargetBindingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = phase_fixture.PhaseDispatchBindingTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        git(self.root, "remote", "add", "origin", "https://github.com/owner/repo.git")
        self.native = dict(issue=371, round=3, branch_name="agent/test", repository="owner/repo",
                           expected_oid=git(self.root, "rev-parse", "HEAD"),
                           handoff_path="tmp/_handoff/issue-implementer--issue-371.yaml")
        self.fixture.approval["dispatch_target"] = {k: self.native[k] for k in
                                                     ("repository", "branch_name", "expected_oid")}
        receipt = self.root / "tmp/_handoff/collected/previous.yaml"
        receipt.parent.mkdir(parents=True)
        receipt.write_text("status: done\n")
        self.predecessor = dict(entry_id="previous", receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest())
        self.entry = dict(entry_id="previous", issue=371, branch_name="agent/test", agent_type="test-writer",
                          status="released", closed_at="now", collected_to="tmp/_handoff/collected/previous.yaml")

    def parse(self, initial=False):
        (self.root / "tmp/binding.json").write_text(json.dumps(self.fixture.binding))
        (self.root / "tmp/approval.json").write_text(json.dumps(self.fixture.approval))
        marker = dict(binding_file="tmp/binding.json", approval_file="tmp/approval.json")
        prompt = "ISSUE_PHASE_INPUT_V1=" + json.dumps(marker) + "\n"
        prompt += ("ISSUE_START_BINDING_V1=" if initial else "ISSUE_PHASE_BINDING_V1=") + json.dumps(self.native)
        prompt += "\nISSUE_PHASE_PREDECESSOR_V1=" + json.dumps(self.predecessor)
        payload = dict(tool_name="Agent", tool_input=dict(subagent_type=self.fixture.binding["recipient"],
                                                         isolation="worktree", prompt=prompt))
        runner = lambda *a, **kw: subprocess.CompletedProcess(a, 0,
            self.native.get("expected_oid", "") + "\trefs/heads/" + self.native["branch_name"] + "\n", "")
        with patch("issue_start.author_continuation.worktree_ledger.main_worktree_root", return_value=self.root), patch(
                "issue_start.author_continuation.worktree_ledger.read_ledger", return_value={"entries": [self.entry]}):
            return parse_dispatch_payload(payload, cwd=self.root, runner=runner)

    def test_followup_exact_worktree_accepts_and_each_native_identity_substitution_fails(self):
        self.assertEqual(self.parse().issue, 371)
        for key, value in (("issue", 999), ("repository", "other/repo"),
                           ("branch_name", "feature/999"), ("expected_oid", "a" * 40)):
            saved = copy.deepcopy(self.native)
            self.native[key] = value
            if key == "issue":
                self.native["handoff_path"] = "tmp/_handoff/issue-implementer--issue-999.yaml"
            with self.subTest(key=key), self.assertRaisesRegex(IssueStartError, "PHASE_TARGET_INVALID"):
                self.parse()
            self.native = saved

    def test_matching_native_and_approval_cannot_replace_the_inspected_worktree(self):
        for key, value in (("repository", "other/repo"), ("branch_name", "other"), ("expected_oid", "a" * 40)):
            saved = self.native[key]
            self.native[key] = self.fixture.approval["dispatch_target"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(IssueStartError, "PHASE_TARGET_INVALID"):
                self.parse()
            self.native[key] = self.fixture.approval["dispatch_target"][key] = saved

    def test_native_writer_requires_explicit_dispatch_target_approval(self):
        self.fixture.approval.pop("dispatch_target")
        with self.assertRaisesRegex(IssueStartError, "PHASE_TARGET_INVALID"):
            self.parse()

    def test_initial_author_approves_future_branch_and_inspected_base(self):
        oid = git(self.root, "rev-parse", "HEAD")
        issue = self.root / "tmp/issue.txt"
        issue.write_bytes(b"Issue371")
        self.fixture.binding = dict(recipient="ac-designer", input_file="tmp/issue.txt",
            input_digest=hashlib.sha256(issue.read_bytes()).hexdigest(), snapshot_oid=oid, issue=371,
            run_id="run-1", target_key="issue-371", investigation_reason="investigation complete")
        self.fixture.approval.update(recipient="ac-designer", snapshot_oid=oid, reviews=[])
        self.fixture.approval.pop("work_unit")
        self.native = dict(entrypoint="issue-pipeline", repository="owner/repo", issue=371,
                           branch_name="feature/371", base_ref="HEAD", base_oid=oid, base_pr=None)
        self.fixture.approval["dispatch_target"].update(branch_name="feature/371", expected_oid=oid)
        self.assertEqual(self.parse(initial=True).issue, 371)
        for key, value in (("issue", 999), ("repository", "other/repo"),
                           ("branch_name", "feature/999"), ("base_oid", "a" * 40)):
            saved = self.native[key]
            self.native[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(IssueStartError, "PHASE_TARGET_INVALID"):
                self.parse(initial=True)
            self.native[key] = saved
