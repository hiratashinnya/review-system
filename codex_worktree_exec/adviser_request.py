"""相談は既存runの一時入力として検証し、新しい台帳を作らない。"""
import hashlib
import json
from pathlib import Path
from issue_envelope.schema import CONTRACTS
from .adviser_budget import validate_budget

REQUEST_FIELDS = {"run_id", "issue", "target_key", "caller_role", "snapshot_oid", "model",
                  "question", "input_refs", "max_calls", "calls_used", "max_tokens",
                  "tokens_used", "reserve_tokens", "max_cost_microusd", "cost_used_microusd",
                  "reserve_cost_microusd", "phase", "work_unit",
                  "max_seconds", "seconds_used", "reserve_seconds"}


def request_digest(raw: dict) -> str:
    return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_adviser_request(raw: dict, worktree: Path, oid: str) -> str:
    """予算と参照を trusted caller の観測値へ束縛する。"""
    from issue_start.gated_roles import GATED_ROLES
    if not isinstance(raw, dict) or set(raw) != REQUEST_FIELDS:
        raise ValueError("AdviceRequest fields mismatch")
    if raw["caller_role"] not in GATED_ROLES - {"adviser"} or raw["snapshot_oid"] != oid:
        raise ValueError("AdviceRequest caller/snapshot mismatch")
    for key in ("run_id", "target_key", "model", "question", "phase", "work_unit"):
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise ValueError(f"missing {key}")
    if type(raw["issue"]) is not int or raw["issue"] <= 0:
        raise ValueError("invalid issue")
    phases = {producer: {phase} for producer, phase, _ in CONTRACTS.values()}
    phases.update({"issue-implementer": {"implementation"}, "issue-fixer": {"implementation"},
                   "plan-reviewer": {"verification_design", "solution_planning"},
                   "pr-reviewer": {"test_design", "solution_planning", "implementation"}})
    if raw["phase"] not in phases.get(raw["caller_role"], set()):
        raise ValueError("AdviceRequest caller/phase mismatch")
    validate_budget(raw)
    refs = raw["input_refs"]
    if not isinstance(refs, list) or not refs:
        raise ValueError("input refs required")
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {"path", "digest"}:
            raise ValueError("invalid input ref")
        path = worktree / ref["path"]
        if path.is_symlink() or not path.resolve().is_relative_to(worktree.resolve()):
            raise ValueError("input ref outside worktree")
        if hashlib.sha256(path.read_bytes()).hexdigest() != ref["digest"]:
            raise ValueError("input ref digest mismatch")
    return request_digest(raw)
