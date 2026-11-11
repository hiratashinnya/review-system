"""Verify independently supplied evidence before it reaches the triager."""

import hashlib
import hmac
import json

CATEGORIES = ("ac", "vd_cp", "design", "change")


def verify_context(raw: bytes, expected_digest: str) -> dict:
    if not isinstance(raw, bytes) or not isinstance(expected_digest, str):
        raise ValueError("trusted context and digest required")
    if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_digest):
        raise ValueError("context digest mismatch")
    try:
        context = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid context JSON") from exc
    if not isinstance(context, dict) or set(context) != set(CATEGORIES):
        raise ValueError("missing context categories")
    if any(not isinstance(context[k], str) or not context[k].strip() for k in CATEGORIES):
        raise ValueError("empty context category")
    return context
