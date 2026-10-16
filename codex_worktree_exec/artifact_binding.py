"""入力 artifact を dispatch expectation と現在の OID に束縛する。"""
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path

from issue_envelope.handoff import validate_handoff
from issue_envelope.placement import validate_placement
from .errors import CodexExecError
from .adviser_request import validate_adviser_request
from .initial_binding import validate_initial_binding
from .source_snapshot import verify_source_snapshot
from .committed_artifact import read_committed_artifact

INPUT_KINDS = {
    "ac-designer": {"InvestigationReport"},
    "change-planner": {"VerificationDesign"},
    "test-writer": {"ChangePlan"},
    "plan-reviewer": {"VerificationDesign", "ChangePlan"},
    "pr-reviewer": {"TestDesign", "ChangePlan"},
    "issue-implementer": {"ChangePlan"},
}


def verify_artifact_binding(request, cwd: Path, worktree: Path) -> None:
    """binding は trusted dispatcher が用意し、期待値を artifact から補わない。"""
    if request.binding_file is None:
        if request.role != "issue-fixer":
            raise CodexExecError("CODEX_EXEC_BINDING_MISSING", request.role)
        return
    try:
        binding = json.loads((cwd / request.binding_file).read_text(encoding="utf-8"))
        if binding["recipient"] != request.role:
            raise ValueError("recipient mismatch")
        result = subprocess.run(
            ["git", "-C", str(worktree), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        oid = result.stdout.strip()
        if request.role == "adviser":
            if set(binding) != {"recipient", "consultation"}:
                raise ValueError("adviser binding fields mismatch")
            if binding["consultation"]["model"] != request.model:
                raise ValueError("consultation model mismatch")
            validate_adviser_request(binding["consultation"], worktree, oid)
            return
        if "input_file" in binding:
            validate_initial_binding(binding, request.role, worktree, oid)
            return
        if set(binding) != {"recipient", "artifact", "artifact_digest", "expected"}:
            raise ValueError("binding fields mismatch")
        path = worktree / binding["artifact"]
        if path.is_symlink() or not path.resolve().is_relative_to(worktree.resolve()):
            raise ValueError("artifact outside worktree")
        content = read_committed_artifact(path, worktree)
        if hashlib.sha256(content).hexdigest() != binding["artifact_digest"]:
            raise ValueError("artifact digest mismatch")
        raw = tomllib.loads(content.decode("utf-8"))
        expected = binding["expected"]
        verify_source_snapshot(worktree, expected["snapshot_oid"], expected["issue"])
        data = validate_handoff(raw, expected)
        validate_placement(path, data, worktree)
        if data["artifact_type"] not in INPUT_KINDS.get(request.role, set()):
            raise ValueError("input kind incompatible with recipient")
        if request.role == "issue-implementer":
            units = [unit for unit in data["work_units"] if unit["id"] == expected.get("work_unit")]
            if len(units) != 1:
                raise ValueError("single approved work unit required")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        raise CodexExecError("CODEX_EXEC_BINDING_INVALID", str(error)) from None
