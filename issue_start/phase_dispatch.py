"""工程 dispatch の入力と必須独立レビューを機械検証する。"""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from codex_worktree_exec.artifact_binding import verify_artifact_binding
from codex_worktree_exec.errors import CodexExecError
from .gate_support import IssueStartError
from .phase_review_receipts import validate_review_receipts

REQUIRED_REVIEWS = {
    "change-planner": ("verification_design",),
    "test-writer": ("verification_design", "solution_planning"),
    "issue-implementer": ("verification_design", "solution_planning", "test_design"),
}


def _head_oid(root):
    return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()


def validate_phase_dispatch(raw, role, cwd):
    """期待値・context ID・review対象digestを trusted dispatcher の承認へ束縛する。"""
    try:
        if set(raw) != {"binding_file", "approval_file"}:
            raise ValueError("phase marker fields mismatch")
        root = Path.cwd() if cwd is None else Path(cwd)
        inspected_oid = _head_oid(root)
        binding_path = root / raw["binding_file"]
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        request = SimpleNamespace(role=role, binding_file=binding_path,
                                  model=binding.get("consultation", {}).get("model", ""))
        verify_artifact_binding(request, root, root)
        approval = json.loads((root / raw["approval_file"]).read_text(encoding="utf-8"))
        expected = {"recipient", "run_id", "issue", "target_key", "snapshot_oid",
                    "context_id", "owner_approved", "reviews"}
        if role in {"test-writer", "issue-implementer", "pr-reviewer"}:
            expected.add("work_unit")
        if set(approval) - {"dispatch_target"} != expected or approval["recipient"] != role:
            raise ValueError("approval fields/recipient mismatch")
        source = binding.get("expected", binding.get("consultation", binding))
        if any(approval[key] != source[key] for key in ("run_id", "issue", "target_key", "snapshot_oid")):
            raise ValueError("approval run/issue/target/snapshot mismatch")
        if "work_unit" in expected and approval["work_unit"] != source.get("work_unit"):
            raise ValueError("approval work_unit mismatch")
        if (approval["owner_approved"] is not True
                or not isinstance(approval["context_id"], str) or not approval["context_id"].strip()):
            raise ValueError("owner approval/context required")
        seen = validate_review_receipts(approval["reviews"], approval, root)
        required = REQUIRED_REVIEWS.get(role, ())
        if role == "plan-reviewer" and source.get("phase") == "solution_planning":
            required = ("verification_design",)
        if role == "pr-reviewer":
            required = ("verification_design", "solution_planning")
            if source.get("phase") == "solution_planning":
                required += ("test_design",)
        for phase in required:
            if phase not in seen:
                raise ValueError(f"missing mandatory review {phase}")
        if "test_design" in seen and "test_design" in source:
            if any(seen["test_design"][key] != source["test_design"][key]
                   for key in ("artifact", "artifact_digest")):
                raise ValueError("reviewed and consumed TestDesign mismatch")
        phase = source.get("phase")
        if phase in seen and seen[phase]["artifact_digest"] != binding["artifact_digest"]:
            raise ValueError("review artifact digest mismatch")
        if _head_oid(root) != inspected_oid:
            raise ValueError("phase inspected HEAD changed during validation")
        return {**approval, "_inspected_oid": inspected_oid}
    except (OSError, ValueError, TypeError, KeyError, CodexExecError, subprocess.SubprocessError) as error:
        raise IssueStartError("ISSUE_START_PHASE_BINDING_INVALID", str(error)) from None
