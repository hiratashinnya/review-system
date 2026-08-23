"""runtime schema、semantic validator、CLI integration contract。"""

from datetime import datetime, timezone
from io import StringIO
import json
import os
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch
import unittest

from blocker_gate.cli import run
from blocker_gate.contract import ContractError, validate_result_semantics
from blocker_gate.model import ALLOW_REASONS, BLOCK_REASONS, ERROR_REASONS
from blocker_gate.resolver import evaluate_snapshot, resolve_issue, resolve_pull_request
from blocker_gate.waiver import WaiverCollection, WaiverEvidence, WaiverMaterial


ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "blocker_gate"
WAIVER_VALID_AT = datetime(2026, 8, 2, tzinfo=timezone.utc)


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def evaluate_during_waiver_validity(raw, waiver_provider):
    """waiver の有効性以外を検証する契約テストを wall clock から分離する。"""
    with patch("blocker_gate.resolver.datetime", wraps=datetime) as clock:
        clock.now.return_value = WAIVER_VALID_AT
        return evaluate_snapshot(raw, waiver_provider=waiver_provider)


class FakeCollector:
    def __init__(self, token=None):
        self.token = token

    def collect_issue(self, repository, number):
        return load("closed_direct.json")

    def collect_pull_request(self, repository, number, merge_method):
        return load("pr_same_parent_child.json")


class FakeWaiverProvider:
    def __init__(self, collection: Any):
        self.collection = collection

    def collect_waiver_materials(self, repository: str) -> Any:
        self.repository = repository
        return self.collection


def waiver_material(finding_fingerprint, **evidence_overrides):
    waiver = (FIXTURES / "waiver_valid.yml").read_bytes().replace(
        b"sha256:" + b"a" * 64, finding_fingerprint.encode("ascii")
    )
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
    values.update(evidence_overrides)
    return WaiverMaterial(
        (FIXTURES / "policy.yml").read_bytes(), waiver, WaiverEvidence(**values)
    )


class SharedResolverTests(unittest.TestCase):
    def test_issue_and_pr_adapters_call_same_core(self):
        collector = FakeCollector()
        with patch("blocker_gate.resolver.evaluate_snapshot", wraps=evaluate_snapshot) as core:
            issue = resolve_issue(collector, "example/repo", 10)
            pr = resolve_pull_request(collector, "example/repo", 50, "rebase")
        self.assertEqual(core.call_count, 2)
        self.assertEqual(issue["result"], "ALLOW")
        self.assertEqual(pr["result"], "ALLOW")

    def test_verified_waiver_evidence_is_preserved(self):
        snapshot = load("open_direct.json")
        blocked = evaluate_snapshot(snapshot)
        target_fp = blocked["findings"][0]["fingerprint"]

        provider = FakeWaiverProvider(
            WaiverCollection((waiver_material(target_fp),))
        )
        allowed = evaluate_during_waiver_validity(snapshot, provider)
        self.assertEqual((allowed["result"], allowed["primary_reason"]), ("ALLOW", "WAIVER_APPLIED"))
        self.assertEqual(allowed["findings"][0]["waiver_evidence"]["approval_commit"], "3" * 40)

    def test_arbitrary_mapping_and_unverified_material_never_permit(self):
        snapshot = load("open_direct.json")
        target_fp = evaluate_snapshot(snapshot)["findings"][0]["fingerprint"]
        arbitrary = evaluate_during_waiver_validity(
            snapshot,
            cast(
                Any,
                lambda _: {
                    "waiver_id": "BW-20260801-001",
                    "approval_commit": "3" * 40,
                },
            ),
        )
        unsigned = evaluate_during_waiver_validity(
            snapshot,
            FakeWaiverProvider(
                WaiverCollection((waiver_material(target_fp, signature_verified=False),))
            ),
        )
        for result in (arbitrary, unsigned):
            self.assertEqual((result["result"], result["exit_code"]), ("ERROR", 20))
            self.assertFalse(result["permit_issued"])
            self.assertIn("WAIVER_INVALID", result["reasons"])

    def test_provider_collection_material_and_error_contract_is_closed(self):
        class DerivedCollection(WaiverCollection):
            pass

        class DerivedMaterial(WaiverMaterial):
            pass

        snapshot = load("open_direct.json")
        target_fp = evaluate_snapshot(snapshot)["findings"][0]["fingerprint"]
        material = waiver_material(target_fp)
        malformed = (
            DerivedCollection((material,)),
            WaiverCollection(cast(Any, [material])),
            WaiverCollection((material,), cast(Any, ["WAIVER_INVALID"])),
            WaiverCollection((material,), ("UNKNOWN_COLLECTION_REASON",)),
            WaiverCollection((material,), cast(Any, (True,))),
            WaiverCollection((cast(Any, {"evidence": material.evidence}),)),
            WaiverCollection(
                (
                    DerivedMaterial(
                        material.policy_bytes,
                        material.waiver_bytes,
                        material.evidence,
                    ),
                )
            ),
            WaiverCollection(
                (
                    WaiverMaterial(
                        cast(Any, "not-bytes"),
                        material.waiver_bytes,
                        material.evidence,
                    ),
                )
            ),
        )
        for collection in malformed:
            with self.subTest(collection=collection):
                result = evaluate_during_waiver_validity(
                    snapshot, FakeWaiverProvider(collection)
                )
                self.assertEqual((result["result"], result["exit_code"]), ("ERROR", 20))
                self.assertFalse(result["permit_issued"])
                self.assertIn("WAIVER_INVALID", result["reasons"])


class ContractTests(unittest.TestCase):
    def test_runtime_schema_reason_enums_and_policy_doc_are_in_sync(self):
        schema = json.loads(
            (ROOT / "blocker_gate" / "schemas" / "blocker-gate-result-v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(schema["$defs"]["allowReason"]["enum"]), ALLOW_REASONS)
        self.assertEqual(set(schema["$defs"]["blockReason"]["enum"]), BLOCK_REASONS)
        self.assertEqual(set(schema["$defs"]["errorReason"]["enum"]), ERROR_REASONS)
        policy = (ROOT / "docs" / "methods" / "blocker-gate-pre-use-policy.md").read_text(encoding="utf-8")
        normative = policy.split("### 10.4 機械 JSON Schema", 1)[1]
        normative = normative.split("```json", 1)[1].split("```", 1)[0]
        self.assertEqual(schema, json.loads(normative))

    def test_semantic_validator_rejects_allow_error_and_union_mismatch(self):
        base = evaluate_snapshot(load("closed_direct.json"))
        bad_pages = {**base, "pages_complete": False}
        with self.assertRaises(ContractError):
            validate_result_semantics(bad_pages, process_exit=0)
        bad_exit = {**base, "exit_code": 10}
        with self.assertRaises(ContractError):
            validate_result_semantics(bad_exit, process_exit=10)
        pr = evaluate_snapshot(load("pr_same_parent_child.json"))
        bad_union = {**pr, "closing_set": []}
        with self.assertRaises(ContractError):
            validate_result_semantics(bad_union, process_exit=0)

    def test_pr_binding_and_method_specific_fingerprints_are_required(self):
        pr = evaluate_snapshot(load("pr_same_parent_child.json"))
        for key in (
            "head_oid", "expected_commit_count", "base_ref_name", "default_branch", "merge_method",
            "operation_fingerprint", "snapshot_fingerprint",
            "message_source_fingerprint", "delivered_message_fingerprint",
        ):
            with self.subTest(key=key):
                bad = {**pr, "binding": {**pr["binding"], key: None}}
                with self.assertRaises(ContractError):
                    validate_result_semantics(bad, process_exit=0)
        bad_rebase = {
            **pr,
            "binding": {
                **pr["binding"],
                "repository_merge_settings_fingerprint": "sha256:" + "9" * 64,
            },
        }
        with self.assertRaises(ContractError):
            validate_result_semantics(bad_rebase, process_exit=0)
        bad_merge = {**pr, "binding": {**pr["binding"], "merge_method": "merge"}}
        with self.assertRaises(ContractError):
            validate_result_semantics(bad_merge, process_exit=0)

    def test_waiver_evidence_correlation_is_closed(self):
        snapshot = load("open_direct.json")
        target_fp = evaluate_snapshot(snapshot)["findings"][0]["fingerprint"]
        allowed = evaluate_during_waiver_validity(
            snapshot,
            FakeWaiverProvider(
                WaiverCollection((waiver_material(target_fp),))
            ),
        )
        finding = allowed["findings"][0]
        mutations = (
            {key: value for key, value in finding.items() if key != "waiver_evidence"},
            {**finding, "code": "CLOSURE_OPEN_DESCENDANT"},
            {
                **finding,
                "waiver_evidence": {
                    **finding["waiver_evidence"],
                    "expires_at": "2026-08-01T00:00:00Z",
                },
            },
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                bad = {**allowed, "findings": [mutation]}
                with self.assertRaises(ContractError):
                    validate_result_semantics(bad, process_exit=0)

    def test_ambiguous_snapshot_never_becomes_allow(self):
        malformed = load("closed_direct.json")
        malformed["mode"] = "unknown"
        result = evaluate_snapshot(malformed)
        self.assertEqual((result["result"], result["exit_code"]), ("ERROR", 20))
        self.assertFalse(result["permit_issued"])
        self.assertEqual((result["mode"], result["repository"], result["subject"]), ("issue-start", None, None))
        validate_result_semantics(result, process_exit=20)


class CliIntegrationTests(unittest.TestCase):
    def test_offline_evaluate_writes_one_json_and_stderr_summary(self):
        stdout, stderr = StringIO(), StringIO()
        code = run(
            ["evaluate", "--snapshot", str(FIXTURES / "open_direct.json")],
            stdout=stdout,
            stderr=stderr,
        )
        self.assertEqual(code, 10)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["result"], "BLOCK")
        self.assertEqual(stdout.getvalue().count("\n"), 1)
        self.assertIn("blocker-gate BLOCK OPEN_BLOCKER", stderr.getvalue())

    def test_issue_and_pr_cli_use_shared_collector_contract_without_secret_output(self):
        for argv in (
            ["issue", "--repository", "example/repo", "--number", "10"],
            ["pr", "--repository", "example/repo", "--number", "50", "--merge-method", "rebase"],
        ):
            with self.subTest(argv=argv), patch.dict(os.environ, {"GH_TOKEN": "super-secret-token"}, clear=False):
                stdout, stderr = StringIO(), StringIO()
                code = run(argv, stdout=stdout, stderr=stderr, collector_factory=FakeCollector)
                self.assertEqual(code, 0)
                self.assertNotIn("super-secret-token", stdout.getvalue() + stderr.getvalue())

    def test_shared_gh_credential_reaches_collector_without_secret_output(self):
        secret = "credential-from-mocked-gh"
        stdout, stderr = StringIO(), StringIO()
        with patch("blocker_gate.cli.resolve_github_token", return_value=secret):
            code = run(
                ["issue", "--repository", "example/repo", "--number", "10"],
                stdout=stdout,
                stderr=stderr,
                collector_factory=FakeCollector,
            )
        self.assertEqual(code, 0)
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())

    def test_anonymous_api_failure_remains_fail_closed(self):
        class AnonymousFailureCollector(FakeCollector):
            def __init__(self, token=None):
                self.asserted_token = token
                if token is not None:
                    raise AssertionError("credential failure must use anonymous read")

            def collect_issue(self, repository, number):
                return load("api_failure.json")

        stdout, stderr = StringIO(), StringIO()
        with patch("blocker_gate.cli.resolve_github_token", return_value=None):
            code = run(
                ["issue", "--repository", "example/repo", "--number", "10"],
                stdout=stdout,
                stderr=stderr,
                collector_factory=AnonymousFailureCollector,
            )
        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 20)
        self.assertEqual((result["result"], result["primary_reason"]), ("ERROR", "API_UNAVAILABLE"))
        self.assertFalse(result["permit_issued"])


if __name__ == "__main__":
    unittest.main()
