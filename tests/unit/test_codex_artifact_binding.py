"""committed artifactの内容・入力snapshot・単一workunitを検証する。"""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from codex_worktree_exec.artifact_binding import verify_artifact_binding
from codex_worktree_exec.errors import CodexExecError
from issue_envelope.handoff import BINDINGS
from issue_envelope.store import write
from tests.issue_envelope.fixtures import artifact
from tests.unit.codex_worktree_exec_support import git, make_repository


class ArtifactBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        _, self.root = make_repository(Path(self.temp.name))
        self.raw = artifact("ChangePlan")
        self.raw["snapshot_oid"] = git(self.root, "rev-parse", "HEAD")
        self.path = self.root / "change_plan/CP-371.toml"
        write(self.path, self.raw)
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "plan artifact")
        self.binding = dict(recipient="issue-implementer", artifact="change_plan/CP-371.toml",
                            artifact_digest=hashlib.sha256(self.path.read_bytes()).hexdigest(),
                            expected={key: self.raw[key] for key in BINDINGS})
        self.binding["expected"].update(ac_refs=["AC-1"], work_unit="WU-1")
        self.request = SimpleNamespace(role="issue-implementer", binding_file=Path("binding.json"))

    def verify(self):
        (self.root / "binding.json").write_text(json.dumps(self.binding))
        verify_artifact_binding(self.request, self.root, self.root)

    def test_artifact_commit_does_not_make_its_source_snapshot_stale(self):
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
