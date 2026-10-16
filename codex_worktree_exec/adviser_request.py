"""相談は既存runの一時入力として検証し、新しい台帳を作らない。"""
import hashlib
import json
from pathlib import Path

REQUEST_FIELDS = {"run_id", "issue", "target_key", "caller_role", "snapshot_oid", "model",
                  "question", "input_refs", "max_calls", "calls_used", "max_tokens",
                  "tokens_used", "reserve_tokens", "max_cost_microusd", "cost_used_microusd",
                  "reserve_cost_microusd"}


def request_digest(raw: dict) -> str:
    return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_adviser_request(raw: dict, worktree: Path, oid: str) -> str:
    """予算と参照を trusted caller の観測値へ束縛する。"""
    from issue_start.gated_roles import GATED_ROLES
    if not isinstance(raw, dict) or set(raw) != REQUEST_FIELDS:
        raise ValueError("AdviceRequest fields mismatch")
    if raw["caller_role"] not in GATED_ROLES - {"adviser"} or raw["snapshot_oid"] != oid:
        raise ValueError("AdviceRequest caller/snapshot mismatch")
    for key in ("run_id", "target_key", "model", "question"):
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise ValueError(f"missing {key}")
    if type(raw["issue"]) is not int or raw["issue"] <= 0:
        raise ValueError("invalid issue")
    for key in REQUEST_FIELDS - {"run_id", "issue", "target_key", "caller_role", "snapshot_oid",
                                 "model", "question", "input_refs"}:
        if type(raw[key]) is not int or raw[key] < 0:
            raise ValueError(f"invalid budget {key}")
    if (raw["calls_used"] >= raw["max_calls"] or raw["reserve_tokens"] <= 0
            or raw["tokens_used"] + raw["reserve_tokens"] > raw["max_tokens"]
            or raw["cost_used_microusd"] + raw["reserve_cost_microusd"] > raw["max_cost_microusd"]):
        raise ValueError("adviser budget reached")
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
