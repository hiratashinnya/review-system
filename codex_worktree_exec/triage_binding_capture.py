"""Construct a triager binding only from reviewer execution and live evidence."""

import hashlib
import hmac
import json

from finding_triager.github_evidence import github_evidence
from triage_policy.evidence import CHANGE_SOURCE, PULL_REQUEST_DIFF
from triage_policy.phases import PHASE_ROUTES, PROPOSAL_PHASES
from .triage_review_capture import DOMAIN
from .triage_binding_verify import sign_binding, normalized_ingested_findings


def binding_from_capture(body, receipt_raw, signature, cwd, key, *, pr, phase, round_no):
    if (phase not in PROPOSAL_PHASES or CHANGE_SOURCE[phase] != PULL_REQUEST_DIFF
            or type(round_no) is not int or round_no < 1):
        raise ValueError("invalid triage phase or round")
    if not hmac.compare_digest(hmac.new(key, DOMAIN + receipt_raw, hashlib.sha256).hexdigest(), signature):
        raise ValueError("review capture signature mismatch")
    receipt = json.loads(receipt_raw)
    if (receipt.get("source") != "ingested-review" or receipt.get("phase") != phase
            or receipt.get("approval", {}).get("triage_phase") != phase
            or receipt.get("round") != round_no):
        raise ValueError("review capture phase or round mismatch")
    if receipt["review_sha256"] != hashlib.sha256(body).hexdigest():
        raise ValueError("review output changed")
    approval = receipt["approval"]
    expected = {k: approval[k] for k in ("issue", "run_id", "target_key", "snapshot_oid")}
    expected.update(phase=phase, round=round_no, input_digest=approval["input_digest"],
                    review_oid=receipt["review_oid"])
    github = github_evidence(cwd, expected["issue"], pr, expected["review_oid"])
    material = approval["materials"]
    vd, cp = material["verification_design"], material["solution_planning"]
    documents = {"ac": github["issue_body"], "vd_cp": vd["content"] + "\n" + cp["content"],
                 "design": cp["content"], "change": github["change"] or "(empty PR diff)"}
    context = {"issue": expected["issue"], "snapshot_oid": expected["snapshot_oid"],
               "review_oid": expected["review_oid"],
               "input_digest": expected["input_digest"], "approval_ref": approval["approval_context"],
               "documents": documents}
    context_raw = json.dumps(context, ensure_ascii=False, sort_keys=True).encode()
    findings = normalized_ingested_findings(body, expected["issue"], receipt.get("finding_ids"))
    review = {**expected, "producer": PHASE_ROUTES[phase]["reviewer"], "findings": findings,
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
