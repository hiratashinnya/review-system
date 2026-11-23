"""Builders for signed review, context and capture inputs of any triage phase (#783)."""

import hashlib
import hmac
import json

from finding_triager.assessment import FIELDS
from triage_policy.evidence import required_categories
from triage_policy.phases import PHASE_ROUTES

REVIEW_KEY, CAPTURE_KEY = b"x" * 32, b"y" * 32


def expected_for(phase):
    return {"issue": 783, "phase": phase, "round": 1, "run_id": "run", "target_key": "target",
            "input_digest": "a" * 64, "snapshot_oid": "b" * 40, "review_oid": "c" * 40}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def context_raw(expected, documents):
    keys = ("issue", "snapshot_oid", "review_oid", "input_digest")
    context = {**{k: expected[k] for k in keys}, "approval_ref": "approved", "documents": documents}
    return json.dumps(context).encode()


def review_raw(expected, context_digest, producer):
    finding = {"finding_id": "F-1", "harm": "real", "scope": "in", "severity": "major",
               "harm_detail": "data loss", "evidence": "review evidence", "summary": "finding"}
    review = {**expected, "producer": producer, "findings": [finding],
              "reviewer_worktree": "/reviewer", "context_sha256": context_digest}
    return json.dumps(review).encode()


def assessment_for(evidence):
    facts = {**dict.fromkeys(FIELDS, False), "evidence_complete": True,
             "ac_relation_verified": True, "ac_violation": True}
    return {"finding_id": "F-1", "harm": "real", "scope": "in", "evidence": evidence, "facts": facts}


def propose_args(phase, documents=None, evidence=None, producer=None):
    """Arguments for ``propose``; defaults are the exact categories and reviewer the phase table requires."""
    categories = required_categories(phase)
    expected = expected_for(phase)
    context = context_raw(expected, documents or dict.fromkeys(categories, "source"))
    raw = review_raw(expected, sha(context), producer or PHASE_ROUTES[phase]["reviewer"])
    capture = {**expected, "producer": "finding-triager", "review_sha256": sha(raw),
               "context_sha256": sha(context),
               "assessments": [assessment_for(evidence or dict.fromkeys(categories, "grounds"))]}
    captured = json.dumps(capture).encode()
    signature = hmac.new(CAPTURE_KEY, b"finding-triage-capture/v1\0" + captured, hashlib.sha256).hexdigest()
    return (raw, hmac.new(REVIEW_KEY, raw, hashlib.sha256).hexdigest(), REVIEW_KEY, expected, context,
            sha(context), captured, signature, CAPTURE_KEY)
