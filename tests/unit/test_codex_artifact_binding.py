"""committed artifactの内容・入力snapshot・単一workunitを検証する。"""
import hashlib
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from codex_worktree_exec.artifact_binding import verify_artifact_binding
from codex_worktree_exec.errors import CodexExecError
from issue_envelope.handoff import BINDINGS
from issue_envelope.schema import SPECS
from feedback_ledger.tomlwrite import dumps
from tests.unit.codex_worktree_exec_support import git, make_repository
from tests.unit.phase_artifact_support import write_valid_plan_set


class ArtifactBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        _, self.root = make_repository(Path(self.temp.name))
        documents, _ = write_valid_plan_set(self.root, git(self.root, "rev-parse", "HEAD"))
        self.raw, self.path = documents["ChangePlan"]
        self.binding = dict(recipient="issue-implementer", artifact="change_plan/CP-371.toml",
                            artifact_digest=hashlib.sha256(self.path.read_bytes()).hexdigest(),
                            expected={key: self.raw[key] for key in BINDINGS})
        self.binding["expected"].update(ac_refs=["AC-1"], work_unit="WU-1")
        self.request = SimpleNamespace(role="issue-implementer", binding_file=Path("tmp/binding.json"))

    def verify(self):
        (self.root / "tmp").mkdir(exist_ok=True)
        (self.root / "tmp/binding.json").write_text(json.dumps(self.binding))
        verify_artifact_binding(self.request, self.root, self.root)

    def test_artifact_commit_does_not_make_its_source_snapshot_stale(self):
        self.verify()

    def test_untracked_source_and_extra_tc_cannot_enter_codex_binding(self):
        for name in ("tool/unapproved.py", "tests/tool/test_extra.py"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"unapproved = True\n")
            with self.subTest(name=name), self.assertRaisesRegex(CodexExecError, "untracked source"):
                self.verify()
            path.unlink()
        self.verify()

    def test_committed_invalid_graph_cannot_reach_executor(self):
        invalid = [dict(input_refs=["VD-999"]), dict(owner_decisions=["FBK-missing"]),
                   dict(children=[]), dict(work_units=[dict(id="WU-1", depends_on=["WU-1"],
                                                          scope=["tool"], ac_refs=["AC-1"])])]
        for fields in invalid:
            data = {**copy.deepcopy(self.raw), **fields}
            self.path.write_text(dumps(SPECS["ChangePlan"], data))
            git(self.root, "add", str(self.path.relative_to(self.root)))
            git(self.root, "commit", "-qm", "invalid committed plan")
            self.binding["artifact_digest"] = hashlib.sha256(self.path.read_bytes()).hexdigest()
            self.binding["expected"].update({key: data[key] for key in BINDINGS})
            with self.subTest(fields=fields), self.assertRaisesRegex(CodexExecError, "repository artifact"):
                self.verify()

    def test_uncommitted_referenced_artifact_is_rejected(self):
        path = self.root / "verification_design/VD-371.toml"
        path.write_text(path.read_text().replace('st_tc = ["ST-TC-1"]', 'st_tc = ["changed"]'))
        with self.assertRaisesRegex(CodexExecError, "uncommitted"):
            self.verify()

    def test_source_change_after_snapshot_fails_even_when_snapshot_is_ancestor(self):
        (self.root / "source.py").write_text("x = 1\n")
        git(self.root, "add", "source.py")
        git(self.root, "commit", "-qm", "source drift")
        with self.assertRaisesRegex(CodexExecError, "CODEX_EXEC_BINDING_INVALID"):
            self.verify()

    def test_digests_producer_and_workunit_cannot_be_substituted(self):
        for changes in ({"artifact_digest": "b" * 64}, {"recipient": "test-writer"},
                        {"expected": {**self.binding["expected"], "producer": "adviser"}},
                        {"expected": {**self.binding["expected"], "work_unit": "WU-2"}}):
            saved = self.binding
            self.binding = {**saved, **changes}
            with self.subTest(changes=changes), self.assertRaises(CodexExecError):
                self.verify()
            self.binding = saved

    def test_implementer_must_have_a_binding_while_fixer_remains_compatible(self):
        for role in ("issue-implementer", "ac-designer", "adviser", "pr-reviewer"):
            with self.subTest(role=role), self.assertRaisesRegex(CodexExecError, "BINDING_MISSING"):
                verify_artifact_binding(SimpleNamespace(role=role, binding_file=None), self.root, self.root)
        verify_artifact_binding(SimpleNamespace(role="issue-fixer", binding_file=None), self.root, self.root)

    def test_empty_collector_cannot_hide_expected_input(self):
        with patch("codex_worktree_exec.repository_artifacts.index", return_value={"nodes": []}):
            with self.assertRaisesRegex(CodexExecError, "outside verified repository collection"):
                self.verify()
