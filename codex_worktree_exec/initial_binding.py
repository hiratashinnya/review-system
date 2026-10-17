"""上流 artifact がまだ無い調査・1aの Issue snapshot を束縛する。"""
import hashlib
import re
from pathlib import Path

INITIAL_ROLES = frozenset({"issue-investigator", "ac-designer"})
INITIAL_FIELDS = {"recipient", "input_file", "input_digest", "snapshot_oid", "issue",
                  "run_id", "target_key", "investigation_reason"}


def validate_initial_binding(binding: dict, role: str, worktree: Path, oid: str) -> None:
    """調査判定理由と raw Issue 入力の digest を必須にし循環を避ける。"""
    if role not in INITIAL_ROLES or set(binding) != INITIAL_FIELDS:
        raise ValueError("initial binding contract mismatch")
    if binding["snapshot_oid"] != oid:
        raise ValueError("stale snapshot_oid")
    if type(binding["issue"]) is not int or binding["issue"] < 1:
        raise ValueError("invalid issue")
    for key in ("run_id", "target_key", "investigation_reason"):
        if not isinstance(binding[key], str) or not binding[key].strip():
            raise ValueError(f"missing {key}")
    path = worktree / binding["input_file"]
    if path.is_symlink() or not path.resolve().is_relative_to(worktree.resolve()):
        raise ValueError("input outside worktree")
    content = path.read_bytes()
    digest = binding["input_digest"]
    if not content or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("invalid initial input")
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValueError("input digest mismatch")
