"""Verify host capture binds original reviewer output to the triage input."""

import hashlib
import hmac
import json
from dataclasses import asdict

from karte.review_report import parse_review
from karte.finding_id import parse_finding_id
from .triage_review_capture import DOMAIN

BINDING_DOMAIN = b"finding-triage-binding/v1\0"
EXTRA = {"receipt", "receipt_signature", "reviewer_output", "binding_signature"}


def normalized_ingested_findings(body: bytes, issue: int, assigned_ids=None) -> list[dict]:
    """Bind parsed reviewer blocks to the official IDs attested by the host receipt."""
    report = parse_review(body.decode("utf-8"), issue)
    if assigned_ids is None:
        assigned_ids = [item.finding_id for item in report]
    if (not isinstance(assigned_ids, list) or len(report) != len(assigned_ids)
            or any(not isinstance(fid, str) for fid in assigned_ids)
            or len(set(assigned_ids)) != len(assigned_ids)):
        raise ValueError("invalid ingested finding IDs")
    findings = []
    for item, fid in zip(report, assigned_ids):
        try:
            id_issue, _seq = parse_finding_id(fid)
        except ValueError as exc:
            raise ValueError("invalid official finding ID") from exc
        if id_issue != issue or (item.finding_id is not None and fid != item.finding_id):
            raise ValueError("ingested finding differs from reviewer ID")
        data = asdict(item)
        data["finding_id"] = fid
        findings.append(data)
    return findings


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
            or receipt.get("source") != "ingested-review"
            or receipt.get("phase") != review["phase"] or approval.get("triage_phase") != review["phase"]
            or type(receipt.get("round")) is not int or receipt.get("round") != review["round"]
            or receipt["worktree"] != binding["reviewer_worktree"]
            or receipt["review_oid"] != review["review_oid"]
            or receipt["review_sha256"] != hashlib.sha256(body).hexdigest()
            or any(approval[k] != review[k] for k in ("issue", "run_id", "target_key", "snapshot_oid", "input_digest"))):
        raise ValueError("reviewer capture mismatch")
    findings = normalized_ingested_findings(body, review["issue"], receipt.get("finding_ids"))
    if json.loads(json.dumps(findings)) != review["findings"]:
        raise ValueError("reviewer finding differs from captured original")
    return receipt
