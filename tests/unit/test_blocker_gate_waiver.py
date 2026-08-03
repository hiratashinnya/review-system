"""read-only waiver parser/verifier contract。"""

from datetime import datetime, timezone
from pathlib import Path
import unittest

import blocker_gate
from blocker_gate.waiver import (
    WaiverContext,
    WaiverError,
    WaiverEvidence,
    parse_policy_yaml,
    parse_waiver_yaml,
    verify_waiver,
)


FIXTURES = Path(__file__).parents[1] / "fixtures" / "blocker_gate"
FP = "sha256:" + "a" * 64


def evidence(**overrides):
    values = {
        "default_branch": "main",
        "default_head": "0" * 40,
        "policy_blob_sha": "sha256:" + "1" * 64,
        "waiver_blob_sha": "sha256:" + "2" * 64,
        "approval_commit": "3" * 40,
        "commit_is_default_head_ancestor": True,
        "signature_verified": True,
        "signer_login": "owner-login",
        "ruleset_active": True,
        "history_bypass_free": True,
        "deletion_protected": True,
        "non_fast_forward_protected": True,
    }
    values.update(overrides)
    return WaiverEvidence(**values)


class WaiverParserTests(unittest.TestCase):
    def test_valid_policy_and_waiver(self):
        policy = parse_policy_yaml((FIXTURES / "policy.yml").read_bytes())
        waiver = parse_waiver_yaml((FIXTURES / "waiver_valid.yml").read_bytes())
        self.assertEqual(policy["policy_version"], "1.0")
        self.assertEqual(waiver["id"], "BW-20260801-001")

    def test_unknown_key_and_duplicate_key_are_schema_error(self):
        with self.assertRaisesRegex(WaiverError, "WAIVER_SCHEMA_INVALID"):
            parse_waiver_yaml((FIXTURES / "waiver_unknown_key.yml").read_bytes())
        duplicate = (FIXTURES / "policy.yml").read_bytes() + b"policy_version: \"1.0\"\n"
        with self.assertRaisesRegex(WaiverError, "WAIVER_SCHEMA_INVALID"):
            parse_policy_yaml(duplicate)

    def test_yaml_alias_document_and_non_utf8_are_denied(self):
        for raw in (b"schema: &x value\n", b"---\nschema: value\n", b"schema: \xff\n"):
            with self.subTest(raw=raw), self.assertRaisesRegex(WaiverError, "WAIVER_SCHEMA_INVALID"):
                parse_waiver_yaml(raw)

    def test_bool_is_not_accepted_as_integer_policy_or_subject_number(self):
        policy = (FIXTURES / "policy.yml").read_bytes().replace(b"168", b"true")
        waiver = (FIXTURES / "waiver_valid.yml").read_bytes().replace(
            b"number: 10", b"number: true"
        )
        for parser, data in ((parse_policy_yaml, policy), (parse_waiver_yaml, waiver)):
            with self.subTest(parser=parser.__name__), self.assertRaisesRegex(
                WaiverError, "WAIVER_SCHEMA_INVALID"
            ):
                parser(data)


class WaiverVerifierTests(unittest.TestCase):
    def setUp(self):
        self.policy = parse_policy_yaml((FIXTURES / "policy.yml").read_bytes())
        self.waiver = parse_waiver_yaml((FIXTURES / "waiver_valid.yml").read_bytes())
        self.context = WaiverContext(
            repository="example/repo",
            mode="issue-start",
            subject_type="issue",
            subject_number=10,
            finding_fingerprint=FP,
            now=datetime(2026, 8, 2, tzinfo=timezone.utc),
        )

    def test_valid_signed_waiver_returns_audit_evidence(self):
        result = verify_waiver(self.waiver, self.policy, self.context, evidence())
        self.assertEqual(result["waiver_id"], "BW-20260801-001")
        self.assertEqual(result["approval_commit"], "3" * 40)

    def test_expired_wrong_scope_and_unsigned_fail_close(self):
        expired = parse_waiver_yaml((FIXTURES / "waiver_expired.yml").read_bytes())
        wrong_scope = WaiverContext(**{**self.context.__dict__, "subject_number": 11})
        cases = (
            (expired, self.context, evidence()),
            (self.waiver, wrong_scope, evidence()),
            (self.waiver, self.context, evidence(signature_verified=False)),
            (self.waiver, self.context, evidence(signer_login="other-login")),
            (self.waiver, self.context, evidence(ruleset_active=False)),
            (self.waiver, self.context, evidence(history_bypass_free=False)),
            (self.waiver, self.context, evidence(default_branch="release")),
        )
        for waiver, context, proof in cases:
            with self.subTest(context=context, proof=proof), self.assertRaisesRegex(WaiverError, "WAIVER_INVALID"):
                verify_waiver(waiver, self.policy, context, proof)

    def test_evidence_requires_exact_class_scalars_and_true_booleans(self):
        class ForgedEvidence(WaiverEvidence):
            pass

        valid = evidence()
        cases = [
            ForgedEvidence(**valid.__dict__),
            evidence(default_branch=1),
            evidence(default_branch="refs/heads/../main"),
            evidence(default_head=True),
            evidence(default_head="0" * 41),
            evidence(policy_blob_sha=b"sha256:bad"),
            evidence(waiver_blob_sha="sha256:bad"),
            evidence(approval_commit=3),
            evidence(signer_login=True),
        ]
        for label in (
            "commit_is_default_head_ancestor",
            "signature_verified",
            "ruleset_active",
            "history_bypass_free",
            "deletion_protected",
            "non_fast_forward_protected",
        ):
            cases.append(evidence(**{label: "true"}))
        for proof in cases:
            with self.subTest(proof=proof), self.assertRaisesRegex(
                WaiverError, "WAIVER_INVALID"
            ):
                verify_waiver(self.waiver, self.policy, self.context, proof)

    def test_public_api_has_no_waiver_lifecycle_writes(self):
        public = set(blocker_gate.__all__)
        for forbidden in ("create_waiver", "save_waiver", "approve_waiver", "delete_waiver", "expire_waiver"):
            self.assertNotIn(forbidden, public)


if __name__ == "__main__":
    unittest.main()
