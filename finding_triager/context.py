"""Verify independently supplied evidence before it reaches the triager."""

import hashlib
import hmac
import json

CATEGORIES = ("ac", "vd_cp", "design", "change")


def verify_context(raw: bytes, expected_digest: str, review: dict) -> dict:
    if not isinstance(raw, bytes) or not isinstance(expected_digest, str):
        raise ValueError("trusted context and digest required")
    if not hmac.compare_digest(expected_digest, review["context_sha256"]):
        raise ValueError("context is not bound to signed review")
    if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_digest):
        raise ValueError("context digest mismatch")
    try:
        context = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid context JSON") from exc
    fields = {"issue", "snapshot_oid", "input_digest", "approval_ref", "documents"}
    if not isinstance(context, dict) or set(context) != fields:
        raise ValueError("invalid context envelope")
    if any(context[k] != review[k] for k in ("issue", "snapshot_oid", "input_digest")):
        raise ValueError("context target mismatch")
    if not isinstance(context["approval_ref"], str) or not context["approval_ref"].strip():
        raise ValueError("missing approved design reference")
    documents = context["documents"]
    if not isinstance(documents, dict) or set(documents) != set(CATEGORIES):
        raise ValueError("missing context categories")
    if any(not isinstance(documents[k], str) or not documents[k].strip() for k in CATEGORIES):
        raise ValueError("empty context category")
    return context
