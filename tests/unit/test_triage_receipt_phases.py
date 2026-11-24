"""Issue #783 F-783-07: review receipts and bindings follow the phase table for every phase."""

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any
import unittest

from codex_worktree_exec.triage_binding_capture import binding_from_capture
from codex_worktree_exec.triage_binding_verify import (normalized_ingested_findings, sign_binding,
                                                       verify_binding_capture)
from codex_worktree_exec.triage_review_capture import DOMAIN, capture_existing
from triage_policy.phases import PHASE_ROUTES, PROPOSAL_PHASES

KEY = b"k" * 32
BODY = (b"### F-783-01\nharm: real\nharm_detail: data loss\nseverity: major\nscope: in\n"
        b"locus: a.py\nsummary: s\nevidence: observed\nexpected: fixed\nrecheck: run it\n")


def approval_for(phase):
    route = PHASE_ROUTES[phase]
    return {"issue": 783, "run_id": "r", "target_key": "k", "snapshot_oid": "a" * 40,
            "input_digest": "b" * 64, "source_changes": {}, "approval_context": "approved",
            "triage_phase": phase,
            "materials": {key: {"content": key} for key in (*route["prior"], route["reviewed"])}}


def sign_receipt(receipt):
    raw = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return raw, hmac.new(KEY, DOMAIN + raw, hashlib.sha256).hexdigest()


def binding_for(phase, *, review: Any = None, receipt: Any = None, body: Any = BODY):
    """A fully signed binding; ``review``/``receipt`` are mutators applied before signing."""
    _, raw, _ = capture_existing(BODY, Path("/reviewer"), approval_for(phase), "c" * 40, KEY, phase, 1,
                                 assigned_ids=["F-783-01"])
    data = json.loads(raw)
    if receipt:
        receipt(data)
    receipt_raw, receipt_signature = sign_receipt(data)
    expected = {"issue": 783, "phase": phase, "round": 1, "run_id": "r", "target_key": "k",
                "input_digest": "b" * 64, "snapshot_oid": "a" * 40, "review_oid": "c" * 40}
    reviewed = {**expected, "producer": PHASE_ROUTES[phase]["reviewer"], "reviewer_worktree": "/reviewer",
                "findings": normalized_ingested_findings(BODY, 783, ["F-783-01"]), "context_sha256": "d" * 64}
    if review:
        review(reviewed)
    review_raw = json.dumps(reviewed, sort_keys=True).encode()
    binding = {"review": review_raw.decode(), "review_signature": hmac.new(KEY, review_raw, hashlib.sha256).hexdigest(),
               "expected": expected, "context": "{}", "context_digest": "d" * 64,
               "reviewer_worktree": "/reviewer", "receipt": receipt_raw.decode(),
               "receipt_signature": receipt_signature, "reviewer_output": body.decode()}
    binding["binding_signature"] = sign_binding(binding, KEY)
    return binding


class PhaseReceiptTest(unittest.TestCase):
    def test_every_phase_receipt_names_its_reviewer_and_verifies(self):
        for phase in PROPOSAL_PHASES:
            with self.subTest(phase=phase):
                receipt = verify_binding_capture(binding_for(phase), KEY)
                self.assertEqual(receipt["producer"], PHASE_ROUTES[phase]["reviewer"])
                self.assertEqual(receipt["phase"], phase)

    def test_producer_must_match_the_phase_reviewer_in_review_and_receipt(self):
        for phase in PROPOSAL_PHASES:
            wrong = "pr-reviewer" if PHASE_ROUTES[phase]["reviewer"] == "plan-reviewer" else "plan-reviewer"
            for name, mutation in (("review", {"review": lambda d: d.update(producer=wrong)}),
                                   ("receipt", {"receipt": lambda d: d.update(producer=wrong)})):
                with self.subTest(phase=phase, wrong=name), self.assertRaises(ValueError):
                    verify_binding_capture(binding_for(phase, **mutation), KEY)

    def test_materials_must_be_exactly_prior_receipts_plus_reviewed_artifact(self):
        for phase in PROPOSAL_PHASES:
            for key in PHASE_ROUTES[phase]["prior"] + (PHASE_ROUTES[phase]["reviewed"],):
                missing = lambda d, key=key: d["approval"]["materials"].pop(key)
                with self.subTest(phase=phase, missing=key), self.assertRaises(ValueError):
                    verify_binding_capture(binding_for(phase, receipt=missing), KEY)
            extra = lambda d: d["approval"]["materials"].update(unrelated={"content": "x"})
            with self.subTest(phase=phase, extra=True), self.assertRaises(ValueError):
                verify_binding_capture(binding_for(phase, receipt=extra), KEY)

    def test_phase_must_agree_between_review_receipt_and_approval(self):
        for phase in PROPOSAL_PHASES:
            other = next(p for p in PROPOSAL_PHASES if p != phase)
            for mutation in ({"review": lambda d: d.update(phase=other)},
                             {"receipt": lambda d: d.update(phase=other)},
                             {"receipt": lambda d: d["approval"].update(triage_phase=other)}):
                with self.subTest(phase=phase, other=other), self.assertRaises(ValueError):
                    verify_binding_capture(binding_for(phase, **mutation), KEY)

    def test_unknown_phase_and_changed_reviewer_output_are_rejected(self):
        with self.assertRaises(ValueError):
            verify_binding_capture(binding_for("review", review=lambda d: d.update(phase="planning")), KEY)
        for phase in PROPOSAL_PHASES:
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                verify_binding_capture(binding_for(phase, body=BODY + b"\n"), KEY)

    def test_capture_rejects_unknown_phase_and_undeclared_approval_phase(self):
        for phase in ("planning", "", None, ["review"]):
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                capture_existing(BODY, Path("/r"), approval_for("review"), "c" * 40, KEY, phase, 1)
        for phase in PROPOSAL_PHASES:
            other = next(p for p in PROPOSAL_PHASES if p != phase)
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                capture_existing(BODY, Path("/r"), approval_for(other), "c" * 40, KEY, phase, 1)

    def test_pr_diff_binding_builder_stays_limited_to_implementation_reviews(self):
        for phase in ("verification_design", "solution_planning", "test_design", "planning", "", None):
            with self.subTest(phase=phase), self.assertRaisesRegex(ValueError, "invalid triage phase"):
                binding_from_capture(b"", b"", "", Path("."), KEY, pr=1, phase=phase, round_no=1)


if __name__ == "__main__":
    unittest.main()
