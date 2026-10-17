"""工程承認はcommit済みartifact・別contextの必須レビューへ束縛する。"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from issue_envelope.handoff import BINDINGS
from issue_envelope.schema import SPECS
from feedback_ledger.tomlwrite import dumps
from issue_start.gate_support import IssueStartError
from issue_start.phase_dispatch import validate_phase_dispatch
from tests.unit.codex_worktree_exec_support import git, make_repository
from tests.unit.phase_artifact_support import write_valid_plan_set


class PhaseDispatchBindingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        _, self.root = make_repository(Path(temporary.name))
        self.oid = git(self.root, "rev-parse", "HEAD")
        self.documents, self.reviews = {}, []
        documents, self.source_changes = write_valid_plan_set(self.root, self.oid, include_tests=True)
        for kind, (data, path) in documents.items():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            relative = str(path.relative_to(self.root))
            self.documents[kind] = (data, relative, digest)
            self.reviews.append(dict(phase=data["phase"], artifact=relative, artifact_digest=digest,
                                     status="clean", producer_context=f"author-{kind}",
                                     review_context=f"review-{kind}",
                                     reviewer="pr-reviewer" if kind == "TestDesign" else "plan-reviewer"))
        data, path, digest = self.documents["ChangePlan"]
        self.binding = dict(recipient="issue-implementer", artifact=path, artifact_digest=digest,
                            expected={key: data[key] for key in BINDINGS})
        self.binding["expected"].update(ac_refs=["AC-1"], work_unit="WU-1",
                                        source_changes=self.source_changes)
        self.approval = dict(recipient="issue-implementer", run_id=data["run_id"], issue=371,
                             target_key=data["target_key"], snapshot_oid=self.oid,
                             context_id="green-context", owner_approved=True, reviews=self.reviews)

    def validate(self):
        (self.root / "tmp").mkdir(exist_ok=True)
        (self.root / "tmp/binding.json").write_text(json.dumps(self.binding))
        (self.root / "tmp/approval.json").write_text(json.dumps(self.approval))
        validate_phase_dispatch(dict(binding_file="tmp/binding.json", approval_file="tmp/approval.json"),
                                "issue-implementer", self.root)

    def test_complete_separate_reviews_allow_approved_single_workunit(self):
        frozen_reviews = copy.deepcopy(self.reviews)
        self.validate()
        self.assertEqual(self.reviews, frozen_reviews)

    def test_untracked_source_and_extra_tc_cannot_enter_native_phase(self):
        for name in ("tool/unapproved.py", "tests/tool/test_extra.py"):
            path = self.root / name
            path.write_bytes(b"unapproved = True\n")
            with self.subTest(name=name), self.assertRaisesRegex(IssueStartError, "untracked source"):
                self.validate()
            path.unlink()
        self.validate()

    def test_later_approved_implementation_keeps_historical_reviews_unchanged(self):
        frozen_reviews = copy.deepcopy(self.reviews)
        path = self.root / "tool/implementation.py"
        path.write_bytes(b"implementation = True\n")
        git(self.root, "add", "tool/implementation.py")
        git(self.root, "commit", "-qm", "later implementation")
        with self.assertRaisesRegex(IssueStartError, "outside canonical"):
            self.validate()
        self.source_changes["tool/implementation.py"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.validate()
        self.assertEqual(self.reviews, frozen_reviews)

    def test_historical_review_artifact_snapshot_must_match_approval(self):
        data, relative, _ = self.documents["TestDesign"]
        data = {**copy.deepcopy(data), "snapshot_oid": "c" * 40}
        path = self.root / relative
        path.write_text(dumps(SPECS["TestDesign"], data))
        git(self.root, "add", relative)
        git(self.root, "commit", "-qm", "mismatched reviewed snapshot")
        self.reviews[2]["artifact_digest"] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(IssueStartError, "reviewed artifact mismatch"):
            self.validate()

    def test_native_dispatch_rejects_committed_graph_errors_with_correct_digest(self):
        original, relative, _ = self.documents["ChangePlan"]
        for fields in (dict(input_refs=["VD-999"]), dict(owner_decisions=["FBK-missing"]),
                       dict(children=[]), dict(work_units=[dict(id="WU-1", depends_on=["WU-1"],
                                                              scope=["tool"], ac_refs=["AC-1"])]),
                       dict(work_units=[dict(id="WU-1", depends_on=[], scope=["tool"],
                                            ac_refs=["AC-unknown"])])):
            data = {**copy.deepcopy(original), **fields}
            path = self.root / relative
            path.write_text(dumps(SPECS["ChangePlan"], data))
            git(self.root, "add", relative)
            git(self.root, "commit", "-qm", "invalid committed plan")
            self.binding["artifact_digest"] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.binding["expected"].update({key: data[key] for key in BINDINGS})
            self.reviews[1]["artifact_digest"] = self.binding["artifact_digest"]
            with self.subTest(fields=fields), self.assertRaisesRegex(IssueStartError, "repository artifact"):
                self.validate()

    def test_native_dispatch_rejects_missing_or_changed_reviewed_test_assets(self):
        for filename in ("tests/tool/test_unit.py", "tool/verify/designs/UT-TD-1.md",
                         "tool/verify/logs/red.log"):
            path = self.root / filename
            content = path.read_bytes()
            path.write_bytes(content + b"unreviewed change\n")
            with self.subTest(filename=filename), self.assertRaisesRegex(IssueStartError, "repository artifact"):
                self.validate()
            path.write_bytes(content)

    def test_native_dispatch_rejects_missing_uncommitted_tc_and_absent_red_evidence(self):
        original, relative, _ = self.documents["TestDesign"]
        path = self.root / relative
        for case in ("missing", "uncommitted", "no-red"):
            data = copy.deepcopy(original)
            if case == "no-red":
                data["red_evidence"] = []
            else:
                filename = f"tests/tool/{case}.py"
                data["ut_tc"] = [filename]
                data["red_evidence"][0]["tc"] = filename
                if case == "uncommitted":
                    (self.root / filename).write_bytes(b"assert False\n")
                    data["red_evidence"][0]["tc_sha256"] = hashlib.sha256(b"assert False\n").hexdigest()
            path.write_text(dumps(SPECS["TestDesign"], data))
            git(self.root, "add", relative)
            git(self.root, "commit", "-qm", "invalid committed test design")
            self.reviews[2]["artifact_digest"] = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.subTest(case=case), self.assertRaisesRegex(IssueStartError, "repository artifact"):
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
            (self.root / "tmp").mkdir(exist_ok=True)
            (self.root / "tmp/binding.json").write_text(json.dumps(self.binding))
            (self.root / "tmp/approval.json").write_text(json.dumps(self.approval))
            with self.subTest(role=role), self.assertRaisesRegex(IssueStartError, "missing mandatory review"):
                validate_phase_dispatch(dict(binding_file="tmp/binding.json", approval_file="tmp/approval.json"),
                                        role, self.root)

    def test_empty_collector_cannot_hide_native_expected_input(self):
        with patch("codex_worktree_exec.repository_artifacts.index", return_value={"nodes": []}):
            with self.assertRaisesRegex(IssueStartError, "outside verified repository collection"):
                self.validate()
