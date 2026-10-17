"""primary trusted callerからreadonly専用linked cwdへ束縛する。"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from codex_worktree_exec.cli import main as execute
from codex_worktree_exec.errors import CodexExecError
from issue_start.gate_support import IssueStartError
from issue_envelope.handoff import BINDINGS
from issue_start.readonly_workspace import main, prepare_readonly_workspace
from issue_start.gate_manifest import ENTRYPOINT_MANIFEST
from tests.unit.codex_worktree_exec_support import (
    clean_environ, git, make_fake_codex, make_repository, write_trust,
)
from tests.unit.phase_artifact_support import write_valid_plan_set


class ReadOnlyWorkspaceTests(unittest.TestCase):
    def test_four_readonly_roles_from_primary_reach_pinned_trusted_executor(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source, target = make_repository(directory)
            manifest = json.loads(ENTRYPOINT_MANIFEST.read_text())
            for entry in manifest["readonly"]:
                entry["binding_transports"]["claude"]["availability"] = "available"
            manifest_path = directory / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            self.enterContext(patch("issue_start.gate_manifest.ENTRYPOINT_MANIFEST", manifest_path))
            documents, changes = write_valid_plan_set(source, git(source, "rev-parse", "HEAD"), True)
            git(target, "reset", "--hard", git(source, "rev-parse", "HEAD"))
            home = directory / "codex-home"
            write_trust(home, source)
            fake = make_fake_codex(directory)
            data, artifact = documents["ChangePlan"]
            issue = b"raw issue input"
            (source / "tmp").mkdir()
            (source / "tmp/issue.txt").write_bytes(issue)
            (source / "tmp/prompt.md").write_text("read-only task")
            reviews = [dict(phase=d["phase"], artifact=str(p.relative_to(source)),
                            artifact_digest=hashlib.sha256(p.read_bytes()).hexdigest(),
                            status="clean", producer_context="author-" + kind,
                            review_context="review-" + kind,
                            reviewer="pr-reviewer" if kind == "TestDesign" else "plan-reviewer")
                       for kind, (d, p) in documents.items()]
            for role in ("issue-investigator", "plan-reviewer", "pr-reviewer", "adviser"):
                oid = git(source, "rev-parse", "HEAD")
                binding = dict(recipient=role, artifact=str(artifact.relative_to(source)),
                               artifact_digest=hashlib.sha256(artifact.read_bytes()).hexdigest(),
                               expected={**{k: data[k] for k in BINDINGS},
                                         "ac_refs": ["AC-1"], "source_changes": changes})
                source_values, receipts = data, reviews
                if role == "issue-investigator":
                    binding = dict(recipient=role, input_file="tmp/issue.txt",
                                   input_digest=hashlib.sha256(issue).hexdigest(), snapshot_oid=oid,
                                   issue=371, run_id="run-1", target_key="issue-371",
                                   investigation_reason="調査が必要")
                    source_values, receipts = binding, []
                if role == "adviser":
                    consultation = dict(run_id="run-1", issue=371, target_key="issue-371",
                        caller_role="test-writer", phase="test_design", work_unit="WU-1",
                        max_seconds=60, seconds_used=0, reserve_seconds=10, snapshot_oid=oid, model="test-model", question="相談",
                        max_calls=1, calls_used=0, max_tokens=1000, tokens_used=0, reserve_tokens=100,
                        max_cost_microusd=1000, cost_used_microusd=0, reserve_cost_microusd=10)
                    consultation["input_refs"] = [dict(path="tmp/issue.txt", digest=hashlib.sha256(issue).hexdigest())]
                    binding = dict(recipient=role, consultation=consultation)
                    source_values, receipts = consultation, []
                approval = {key: source_values[key] for key in ("run_id", "issue", "target_key", "snapshot_oid")}
                approval.update(recipient=role, context_id="readonly-" + role,
                                owner_approved=True, reviews=receipts)
                for name, payload in ((f"{role}-binding", binding), (f"{role}-approval", approval)):
                    (source / f"tmp/{name}.json").write_text(json.dumps(payload))
                args = ["--source", str(source), "--approval-file", f"tmp/{role}-approval.json",
                        "--role", role, "-C", str(target), "--binding-file", f"tmp/{role}-binding.json",
                        "--prompt-file", "tmp/prompt.md", "--output-file", f"tmp/{role}-out.md",
                        "--model", binding.get("consultation", {}).get("model", "test-model"),
                        "--reasoning-effort", "high"]
                for root in (source, target):
                    for relative in ("tool/unapproved.py", "tests/tool/test_extra.py"):
                        extra = root / relative
                        extra.write_text("unapproved = True\n")
                        with self.subTest(role=role, root=root, relative=relative), self.assertRaisesRegex(
                                ValueError, "untracked source"):
                            main(args)
                        extra.unlink()
                with self.subTest(role=role), patch("issue_start.readonly_workspace.execute",
                        side_effect=lambda a, cwd: execute(a, cwd=cwd,
                            environ=clean_environ(CODEX_HOME=str(home)), codex=str(fake))):
                    self.assertEqual(main(args), 0)

    def test_primary_target_and_writer_cannot_use_prepare(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, target = make_repository(Path(temporary))
            with self.assertRaises(ValueError):
                prepare_readonly_workspace(source, target, "issue-implementer", {}, "tmp/prompt.md")
            with self.assertRaises(CodexExecError):
                prepare_readonly_workspace(source, source, "pr-reviewer", {}, "tmp/prompt.md")
            with self.assertRaisesRegex(IssueStartError, "BINDING_INVALID"):
                prepare_readonly_workspace(source, target, "issue-investigator", {}, "tmp/prompt.md")
            (source / "source.py").write_text("new committed input")
            git(source, "add", "source.py")
            git(source, "commit", "-qm", "source changed")
            with self.assertRaisesRegex(ValueError, "HEAD mismatch"):
                prepare_readonly_workspace(source, target, "issue-investigator", {}, "tmp/prompt.md")
