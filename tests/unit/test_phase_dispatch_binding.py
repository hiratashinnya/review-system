"""工程承認はcommit済みartifact・別contextの必須レビューへ束縛する。"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from issue_envelope.handoff import BINDINGS
from issue_envelope.store import write
from issue_start.gate_support import IssueStartError
from issue_start.phase_dispatch import validate_phase_dispatch
from tests.issue_envelope.fixtures import artifact
from tests.unit.codex_worktree_exec_support import git, make_repository


class PhaseDispatchBindingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        _, self.root = make_repository(Path(temporary.name))
        self.oid = git(self.root, "rev-parse", "HEAD")
        self.documents, self.reviews = {}, []
        for kind, directory in (("VerificationDesign", "verification_design"),
                                ("ChangePlan", "change_plan"), ("TestDesign", "test_design")):
            data = artifact(kind)
            data["snapshot_oid"] = self.oid
            path = self.root / directory / f"{data['id']}.toml"
            write(path, data)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            relative = str(path.relative_to(self.root))
            self.documents[kind] = (data, relative, digest)
            self.reviews.append(dict(phase=data["phase"], artifact=relative, artifact_digest=digest,
                                     status="clean", producer_context=f"author-{kind}",
                                     review_context=f"review-{kind}", reviewer=(
                                         "pr-reviewer" if kind == "TestDesign" else "plan-reviewer")))
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "reviewed artifacts")
        data, path, digest = self.documents["ChangePlan"]
        self.binding = dict(recipient="issue-implementer", artifact=path, artifact_digest=digest,
                            expected={key: data[key] for key in BINDINGS})
        self.binding["expected"].update(ac_refs=["AC-1"], work_unit="WU-1")
        self.approval = dict(recipient="issue-implementer", run_id=data["run_id"], issue=371,
                             target_key=data["target_key"], snapshot_oid=self.oid,
                             context_id="green-context", owner_approved=True, reviews=self.reviews)

    def validate(self):
        (self.root / "binding.json").write_text(json.dumps(self.binding))
        (self.root / "approval.json").write_text(json.dumps(self.approval))
        validate_phase_dispatch(dict(binding_file="binding.json", approval_file="approval.json"),
                                "issue-implementer", self.root)

    def test_complete_separate_reviews_allow_approved_single_workunit(self):
        self.validate()

    def test_missing_or_nonclean_review_cannot_be_replaced_by_owner_approval(self):
        for index in range(3):
            saved = copy.deepcopy(self.reviews)
            for operation in ("remove", "finding"):
                self.approval["reviews"] = copy.deepcopy(saved)
                if operation == "remove":
                    self.approval["reviews"].pop(index)
                else:
                    self.approval["reviews"][index]["status"] = "finding"
                with self.subTest(index=index, operation=operation), self.assertRaises(IssueStartError):
                    self.validate()

    def test_context_and_approval_scope_mismatch_fail_closed(self):
        for key, value in (("context_id", "author-ChangePlan"), ("context_id", 1),
                           ("target_key", "other-target"), ("snapshot_oid", "c" * 40),
                           ("owner_approved", False)):
            saved = self.approval[key]
            self.approval[key] = value
            with self.subTest(key=key), self.assertRaises(IssueStartError):
                self.validate()
            self.approval[key] = saved

    def test_review_digest_and_cross_role_context_reuse_fail_closed(self):
        for key, value in (("artifact_digest", "c" * 64), ("review_context", "author-TestDesign")):
            saved = self.reviews[0][key]
            self.reviews[0][key] = value
            with self.subTest(key=key), self.assertRaises(IssueStartError):
                self.validate()
            self.reviews[0][key] = saved

    def test_later_reviewers_require_completed_upstream_reviews(self):
        for role in ("plan-reviewer", "pr-reviewer"):
            self.binding["recipient"] = self.approval["recipient"] = role
            self.approval["reviews"] = []
            (self.root / "binding.json").write_text(json.dumps(self.binding))
            (self.root / "approval.json").write_text(json.dumps(self.approval))
            with self.subTest(role=role), self.assertRaisesRegex(IssueStartError, "missing mandatory review"):
                validate_phase_dispatch(dict(binding_file="binding.json", approval_file="approval.json"),
                                        role, self.root)
