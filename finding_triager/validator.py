"""Recompute a proposal from the signed review and authenticated capture."""

from .adapter import propose


def validate_proposal(artifact, raw, signature, key, expected, context_raw, context_digest,
                      capture_raw, capture_signature, capture_key):
    canonical = propose(raw, signature, key, expected, context_raw, context_digest,
                        capture_raw, capture_signature, capture_key)
    if artifact != canonical:
        raise ValueError("triage artifact mismatch")
    return canonical
