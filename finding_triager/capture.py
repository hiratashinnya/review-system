"""Authenticate a trusted host capture and bind it to its inputs."""

import hashlib
import hmac
import json

from .inputs import BINDINGS


def verify_capture(raw: bytes, signature: str, key: bytes, review: dict,
                   review_raw: bytes, context_digest: str) -> list:
    if not isinstance(key, bytes) or len(key) < 32 or not isinstance(raw, bytes):
        raise ValueError("trusted capture key required")
    mac = hmac.new(key, b"finding-triage-capture/v1\0" + raw, hashlib.sha256).hexdigest()
    if not isinstance(signature, str) or not hmac.compare_digest(mac, signature):
        raise ValueError("capture signature mismatch")
    try:
        capture = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid capture JSON") from exc
    fields = set(BINDINGS) | {"producer", "review_sha256", "context_sha256", "assessments"}
    if not isinstance(capture, dict) or set(capture) != fields:
        raise ValueError("invalid capture fields")
    if (capture["producer"] != "finding-triager"
            or any(capture[k] != review[k] for k in BINDINGS)
            or capture["review_sha256"] != hashlib.sha256(review_raw).hexdigest()
            or capture["context_sha256"] != context_digest
            or not isinstance(capture["assessments"], list)):
        raise ValueError("capture binding mismatch")
    return capture["assessments"]
