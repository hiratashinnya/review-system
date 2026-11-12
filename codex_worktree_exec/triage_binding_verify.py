"""Verify host capture binds original reviewer output to the triage input."""

import hashlib
import hmac
import json
from dataclasses import asdict

from karte.review_report import parse_review
from .triage_review_capture import DOMAIN

BINDING_DOMAIN = b"finding-triage-binding/v1\0"
EXTRA = {"receipt", "receipt_signature", "reviewer_output", "binding_signature"}


def sign_binding(binding, key):
    data = json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(key, BINDING_DOMAIN + data, hashlib.sha256).hexdigest()


def verify_binding_capture(binding, key):
    if not isinstance(binding, dict) or not EXTRA <= set(binding):
        raise ValueError("host review capture required")
    core = {k: v for k, v in binding.items() if k != "binding_signature"}
    if not hmac.compare_digest(sign_binding(core, key), binding["binding_signature"]):
        raise ValueError("host binding signature mismatch")
    raw = binding["receipt"].encode()
    signature = hmac.new(key, DOMAIN + raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, binding["receipt_signature"]):
        raise ValueError("reviewer capture signature mismatch")
    receipt = json.loads(raw)
    body = binding["reviewer_output"].encode()
    review = json.loads(binding["review"])
    approval = receipt["approval"]
    if (receipt["schema"] != "finding-triage-review-capture/v1" or receipt["producer"] != "pr-reviewer"
            or receipt["worktree"] != binding["reviewer_worktree"]
            or receipt["review_oid"] != review["review_oid"]
            or receipt["review_sha256"] != hashlib.sha256(body).hexdigest()
            or any(approval[k] != review[k] for k in ("issue", "run_id", "target_key", "snapshot_oid", "input_digest"))):
        raise ValueError("reviewer capture mismatch")
    findings = []
    for index, finding in enumerate(parse_review(body.decode(), review["issue"]), 1):
        data = asdict(finding)
        data["finding_id"] = finding.finding_id or f"new-{index}"
        findings.append(data)
    if json.loads(json.dumps(findings)) != review["findings"]:
        raise ValueError("reviewer finding differs from captured original")
    return receipt
