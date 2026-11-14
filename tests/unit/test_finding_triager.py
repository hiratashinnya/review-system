import hashlib
import hmac
import json
import unittest

from finding_triager.adapter import prepare, propose
from finding_triager.assessment import FIELDS


class FindingTriagerTest(unittest.TestCase):
    def setUp(self):
        self.key = b"x" * 32
        self.capture_key = b"y" * 32
        self.expected = {"issue": 783, "phase": "review", "round": 1, "run_id": "run",
                         "target_key": "target", "input_digest": "a" * 64, "snapshot_oid": "b" * 40, "review_oid": "c" * 40}
        context = {"issue": 783, "snapshot_oid": "b" * 40, "review_oid": "c" * 40, "input_digest": "a" * 64,
                   "approval_ref": "approved-design-1", "documents": dict.fromkeys(
                       ("ac", "vd_cp", "design", "change"), "source evidence")}
        self.context = json.dumps(context).encode()
        self.context_digest = hashlib.sha256(self.context).hexdigest()
        review = {**self.expected, "reviewer_worktree": "/reviewer", "context_sha256": self.context_digest,
                  "producer": "pr-reviewer", "findings": [
            {"finding_id": "F-1", "harm": "real", "scope": "in", "severity": "major",
             "harm_detail": "data loss", "evidence": "review evidence", "summary": "finding"}]}
        self.raw = json.dumps(review).encode()
        self.signature = hmac.new(self.key, self.raw, hashlib.sha256).hexdigest()
        facts = dict.fromkeys(FIELDS, False)
        facts.update(evidence_complete=True, ac_relation_verified=True, ac_violation=True)
        self.assessment = {"finding_id": "F-1", "harm": "real", "scope": "in",
                           "evidence": dict.fromkeys(("ac", "vd_cp", "design", "change"), "evidence"),
                           "facts": facts}

    def prepare(self):
        return prepare(self.raw, self.signature, self.key, self.expected, self.context, self.context_digest)

    def args(self):
        capture = {**self.expected, "producer": "finding-triager",
                   "review_sha256": hashlib.sha256(self.raw).hexdigest(),
                   "context_sha256": self.context_digest, "assessments": [self.assessment]}
        raw = json.dumps(capture).encode()
        signature = hmac.new(self.capture_key, b"finding-triage-capture/v1\0" + raw, hashlib.sha256).hexdigest()
        return (self.raw, self.signature, self.key, self.expected, self.context,
                self.context_digest, raw, signature, self.capture_key)

    def test_standalone_prompt_and_candidate(self):
        prompt, _ = self.prepare()
        self.assertIn("harm_detail に書くのは実害だけ", prompt)
        self.assertIn("source evidence", prompt)
        artifact = propose(*self.args())
        self.assertEqual(artifact["proposals"][0]["result"]["candidate"], "fix-here")
        self.assertEqual(artifact["provenance"]["review_sha256"], hashlib.sha256(self.raw).hexdigest())

    def test_conflict_and_unknown_relation_fail_closed(self):
        self.assessment["scope"] = "out"
        proposal = propose(*self.args())["proposals"][0]
        self.assertEqual(proposal["result"]["candidate"], "owner-review")
        self.assertEqual(proposal["reviewer"]["scope"], "in")
        self.assertEqual(proposal["reviewer"]["harm_detail"], "data loss")
        self.assertEqual(proposal["reviewer"]["evidence"], "review evidence")
        self.assertEqual(proposal["reviewer"]["summary"], "finding")
        self.assertEqual(proposal["triager"]["scope"], "out")
        self.assessment["scope"] = "in"
        self.assessment["facts"]["ac_relation_verified"] = False
        proposal = propose(*self.args())["proposals"][0]
        self.assertEqual(proposal["result"]["candidate"], "owner-review")

    def test_context_and_capture_tampering_are_rejected(self):
        args = list(self.args())
        for index, value in ((4, self.context + b" "), (6, args[6] + b" "),
                             (7, "0" * 64), (8, b"z" * 32)):
            altered = args.copy()
            altered[index] = value
            with self.subTest(index=index), self.assertRaises(ValueError):
                propose(*altered)
        context = json.dumps({"ac": "source"}).encode()
        altered = args.copy()
        altered[4:6] = [context, hashlib.sha256(context).hexdigest()]
        with self.assertRaises(ValueError):
            propose(*altered)
        capture = json.loads(args[6]); capture["run_id"] = "other"
        raw = json.dumps(capture).encode()
        altered = args.copy(); altered[6] = raw
        altered[7] = hmac.new(self.capture_key, b"finding-triage-capture/v1\0" + raw, hashlib.sha256).hexdigest()
        with self.assertRaises(ValueError):
            propose(*altered)

    def test_missing_reviewer_rationale_is_rejected(self):
        review = json.loads(self.raw)
        del review["findings"][0]["evidence"]
        raw = json.dumps(review).encode()
        signature = hmac.new(self.key, raw, hashlib.sha256).hexdigest()
        with self.assertRaises(ValueError):
            propose(raw, signature, self.key, self.expected, *self.args()[4:])

    def test_rejects_untrusted_inputs(self):
        for raw, signature, expected in ((self.raw + b" ", self.signature, self.expected),
                                         (self.raw, self.signature, {**self.expected, "snapshot_oid": "c" * 40}),
                                         (self.raw, "0" * 64, self.expected)):
            with self.subTest(raw=raw, expected=expected), self.assertRaises(ValueError):
                propose(raw, signature, self.key, expected, *self.args()[4:])
        self.assessment["evidence"]["ac"] = ""
        with self.assertRaises(ValueError):
            propose(*self.args())


if __name__ == "__main__":
    unittest.main()

class ProposalValidationTest(FindingTriagerTest):
    def test_recomputes_artifact_and_rejects_tampering(self):
        from finding_triager.validator import validate_proposal
        artifact = propose(*self.args())
        self.assertEqual(validate_proposal(artifact, *self.args()), artifact)
        artifact["proposals"][0]["result"]["candidate"] = "advisory"
        with self.assertRaises(ValueError):
            validate_proposal(artifact, *self.args())
