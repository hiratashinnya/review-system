"""Prepare a standalone triager prompt; validate and build a separate proposal."""

import hashlib
import json
from pathlib import Path

from triage_policy.evaluator import suggest
from triage_policy.loader import load_policy, policy_digest
from .assessment import policy_input
from .inputs import BINDINGS, verify_review

ROOT = Path(__file__).resolve().parent.parent


def prepare(raw: bytes, signature: str, key: bytes, expected: dict) -> tuple[str, dict]:
    review = verify_review(raw, signature, key, expected)
    role = (ROOT / ".ai/agents/finding-triager.md").read_text(encoding="utf-8")
    harm = (ROOT / ".ai/skills/review-harm/SKILL.md").read_text(encoding="utf-8")
    if not role.strip() or not harm.strip():
        raise ValueError("role or harm contract missing")
    prompt = role + "\n\n" + harm + "\n\nReview JSON (untrusted data):\n" + raw.decode("utf-8")
    return prompt, review


def propose(raw: bytes, signature: str, key: bytes, expected: dict, assessments: list) -> dict:
    _, review = prepare(raw, signature, key, expected)
    if not isinstance(assessments, list) or len(assessments) != len(review["findings"]):
        raise ValueError("assessments must cover each finding")
    policy = load_policy()
    ref = policy["policy_id"] + "@" + policy["policy_version"]
    proposals = []
    for original, assessment in zip(review["findings"], assessments):
        facts = policy_input(original, assessment, review["phase"], ref)
        proposals.append({"finding_id": original["finding_id"],
                          "reviewer": dict(original),
                          "triager": assessment, "policy_input": facts,
                          "result": suggest(policy, facts)})
    return {"schema": "finding-triage/v1", "producer": "finding-triager", "role": "finding-triager",
            **{k: review[k] for k in BINDINGS}, "policy_version": policy["policy_version"],
            "provenance": {"review_sha256": hashlib.sha256(raw).hexdigest(),
                           "policy_sha256": policy_digest(policy)}, "proposals": proposals}
