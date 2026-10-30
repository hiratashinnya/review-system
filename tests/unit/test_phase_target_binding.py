"""phase検証をmockせずproduction parserのIssue/repo/branch/OID結線を実gitで検査する。"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from issue_start.gate_dispatch import parse_dispatch_payload
from issue_start.gate_support import IssueStartError
from issue_start.phase_target_binding import _require_branch_unheld, _require_detached
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

    def test_followup_detached_exact_worktree_accepts_and_each_native_identity_substitution_fails(self):
        git(self.root, "switch", "-q", "--detach", "HEAD")
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
        for key, value, detail in (("repository", "other/repo", "repository/HEAD mismatch"),
                                   ("branch_name", "other", "phase inspected branch mismatch"),
                                   ("expected_oid", "a" * 40, "inspected OID/native OID mismatch")):
            saved = self.native[key]
            self.native[key] = self.fixture.approval["dispatch_target"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(IssueStartError, "PHASE_TARGET_INVALID: .*" + detail):
                self.parse()
            self.native[key] = self.fixture.approval["dispatch_target"][key] = saved

    def test_followup_on_target_branch_is_rejected_with_detach_recovery(self):
        oid = self.native["expected_oid"]
        before = self.surface()
        with self.assertRaises(IssueStartError) as caught:
            self.parse()
        self.assertEqual(caught.exception.reason, "ISSUE_START_PHASE_TARGET_INVALID")
        self.assertIn("holds target branch agent/test", str(caught.exception))
        self.assertIn(f"git switch --detach {oid}", str(caught.exception))
        self.assertEqual(self.surface(), before)

    def test_detached_exact_head_is_accepted_without_changing_head_refs_or_index(self):
        git(self.root, "switch", "-q", "--detach", "HEAD")
        before = self.surface()
        self.assertEqual(self.parse().issue, 371)
        self.assertEqual(self.surface(), before)

    def test_detached_head_or_repository_substitution_is_still_rejected(self):
        git(self.root, "switch", "-q", "--detach", "HEAD")
        for key, value in (("repository", "other/repo"), ("expected_oid", "a" * 40)):
            saved = self.native[key]
            self.native[key] = self.fixture.approval["dispatch_target"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(IssueStartError, "PHASE_TARGET_INVALID"):
                self.parse()
            self.native[key] = self.fixture.approval["dispatch_target"][key] = saved

    def test_detached_branch_rename_is_rejected_by_the_latest_ledger_owner_check(self):
        git(self.root, "switch", "-q", "--detach", "HEAD")
        self.native["branch_name"] = self.fixture.approval["dispatch_target"]["branch_name"] = "other"
        with self.assertRaisesRegex(IssueStartError, "CONTINUATION_INVALID: predecessor must be latest branch owner"):
            self.parse()

    def test_detached_surface_is_rejected_while_another_worktree_holds_the_target_branch(self):
        oid = self.native["expected_oid"]
        git(self.root, "switch", "-q", "--detach", "HEAD")
        main = Path(git(self.root, "rev-parse", "--path-format=absolute", "--git-common-dir")).parent
        other = main.parent / "other-holder"
        for holder, place in (("linked", lambda: git(main, "worktree", "add", "-q", str(other), "agent/test")),
                              ("primary", lambda: git(main, "switch", "-q", "agent/test"))):
            place()
            before = self.surface()
            with self.subTest(holder=holder), self.assertRaises(IssueStartError) as caught:
                self.parse()
            self.assertEqual(caught.exception.reason, "ISSUE_START_PHASE_TARGET_INVALID")
            self.assertIn(str(other if holder == "linked" else main), str(caught.exception))
            self.assertIn(f"git switch --detach {oid}", str(caught.exception))
            self.assertEqual(self.surface(), before)
            if holder == "linked":
                git(main, "worktree", "remove", "--force", str(other))

    def test_worktree_listing_failure_is_rejected_not_treated_as_unheld(self):
        git(self.root, "switch", "-q", "--detach", "HEAD")
        failure = subprocess.CalledProcessError(128, ["git", "worktree", "list"])
        with patch("issue_start.phase_target_binding._require_branch_unheld", side_effect=failure), \
                self.assertRaisesRegex(IssueStartError, "PHASE_TARGET_INVALID"):
            self.parse()
        failing = lambda *args: (_ for _ in ()).throw(failure)
        with self.assertRaises(subprocess.CalledProcessError):
            _require_branch_unheld(failing, "agent/test", "a" * 40)

    def test_git_failure_other_than_detached_is_not_treated_as_detached(self):
        with tempfile.TemporaryDirectory() as outside, self.assertRaises(subprocess.CalledProcessError):
            _require_detached(Path(outside), "agent/test", "a" * 40)

    def surface(self):
        return (git(self.root, "rev-parse", "HEAD"), git(self.root, "for-each-ref"),
                git(self.root, "status", "--porcelain=v2", "--branch", "--untracked-files=no"),
                hashlib.sha256((self.root / git(self.root, "rev-parse", "--git-path", "index")).read_bytes()).hexdigest())

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
