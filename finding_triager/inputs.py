"""Verify trusted bindings before exposing immutable review data to a triager."""

import hashlib
import hmac
import json
import re

PHASES = ("review", "remediation_review")
BINDINGS = ("issue", "phase", "round", "run_id", "target_key", "input_digest", "snapshot_oid")


def verify_review(raw: bytes, signature: str, key: bytes, expected: dict) -> dict:
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("trusted signing key required")
    if not isinstance(signature, str) or not hmac.compare_digest(
        hmac.new(key, raw, hashlib.sha256).hexdigest(), signature
    ):
        raise ValueError("review signature mismatch")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid review JSON") from exc
    if not isinstance(data, dict) or set(data) != set(BINDINGS) | {"producer", "findings"}:
        raise ValueError("invalid review fields")
    if set(expected) != set(BINDINGS) or any(data[k] != expected[k] for k in BINDINGS):
        raise ValueError("review binding mismatch")
    if (data["producer"] != "pr-reviewer" or data["phase"] not in PHASES
            or type(data["issue"]) is not int or data["issue"] < 1
            or type(data["round"]) is not int or data["round"] < 1):
        raise ValueError("invalid review envelope")
    for field, length in (("input_digest", 64), ("snapshot_oid", 40)):
        if not isinstance(data[field], str) or not re.fullmatch(r"[0-9a-f]{%d}" % length, data[field]):
            raise ValueError("invalid " + field)
    for field in ("run_id", "target_key"):
        if not isinstance(data[field], str) or not data[field].strip():
            raise ValueError("invalid " + field)
    findings = data["findings"]
    if not isinstance(findings, list) or any(not isinstance(f, dict) for f in findings):
        raise ValueError("invalid findings")
    ids = [f.get("finding_id") for f in findings]
    if (any(not isinstance(i, str) or not i.strip() for i in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError("invalid finding ids")
    if any(f.get("harm") not in ("real", "none") or f.get("scope") not in ("in", "out")
           or f.get("severity") not in ("minor", "major", "blocker") for f in findings):
        raise ValueError("invalid review judgments")
    if any(not isinstance(f.get(k), str) or not f[k].strip()
           for f in findings for k in ("harm_detail", "evidence")):
        raise ValueError("missing reviewer rationale")
    return data
