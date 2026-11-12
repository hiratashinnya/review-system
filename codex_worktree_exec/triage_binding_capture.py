"""Construct a triager binding only from reviewer execution and live evidence."""

import hashlib
import hmac
import json
from dataclasses import asdict

from finding_triager.github_evidence import github_evidence
from karte.review_report import parse_review
from .triage_review_capture import DOMAIN, capture_reviewer
from .triage_binding_verify import sign_binding


def capture_binding(request, cwd, marker, environ, codex, key, *, pr, phase, round_no):
    """Trusted caller chooses PR, triage phase and round; no arbitrary review is accepted."""
    if phase not in ("review", "remediation_review") or type(round_no) is not int or round_no < 1:
        raise ValueError("invalid triage phase or round")
    body, receipt_raw, signature = capture_reviewer(request, cwd, marker, environ, codex, key)
    if not hmac.compare_digest(hmac.new(key, DOMAIN + receipt_raw, hashlib.sha256).hexdigest(), signature):
        raise ValueError("review capture signature mismatch")
    receipt = json.loads(receipt_raw)
    if receipt["review_sha256"] != hashlib.sha256(body).hexdigest():
        raise ValueError("review output changed")
    approval = receipt["approval"]
    expected = {k: approval[k] for k in ("issue", "run_id", "target_key", "snapshot_oid")}
    expected.update(phase=phase, round=round_no, input_digest=approval["input_digest"])
    github = github_evidence(cwd, expected["issue"], pr, expected["snapshot_oid"])
    material = approval["materials"]
    vd, cp = material["verification_design"], material["solution_planning"]
    documents = {"ac": github["issue_body"], "vd_cp": vd["content"] + "\n" + cp["content"],
                 "design": cp["content"], "change": github["change"] or "(empty PR diff)"}
    context = {"issue": expected["issue"], "snapshot_oid": expected["snapshot_oid"],
               "input_digest": expected["input_digest"], "approval_ref": approval["approval_context"],
               "documents": documents}
    context_raw = json.dumps(context, ensure_ascii=False, sort_keys=True).encode()
    findings = []
    for index, finding in enumerate(parse_review(body.decode("utf-8"), expected["issue"]), 1):
        data = asdict(finding)
        data["finding_id"] = finding.finding_id or f"new-{index}"
        findings.append(data)
    review = {**expected, "producer": "pr-reviewer", "findings": findings,
              "reviewer_worktree": receipt["worktree"],
              "context_sha256": hashlib.sha256(context_raw).hexdigest()}
    raw = json.dumps(review, ensure_ascii=False, sort_keys=True).encode()
    result = {"review": raw.decode(), "review_signature": hmac.new(key, raw, hashlib.sha256).hexdigest(),
              "expected": expected, "context": context_raw.decode(),
              "context_digest": review["context_sha256"], "reviewer_worktree": receipt["worktree"],
              "receipt": receipt_raw.decode(), "receipt_signature": signature,
              "reviewer_output": body.decode()}
    result["binding_signature"] = sign_binding(result, key)
    return result
