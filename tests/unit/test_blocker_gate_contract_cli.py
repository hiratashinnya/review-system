"""runtime schema、semantic validator、CLI integration contract。"""

from io import StringIO
import json
import os
from pathlib import Path
from unittest.mock import patch
import unittest

from blocker_gate.cli import run
from blocker_gate.contract import ContractError, validate_result_semantics
from blocker_gate.model import ALLOW_REASONS, BLOCK_REASONS, ERROR_REASONS
from blocker_gate.resolver import evaluate_snapshot, resolve_issue, resolve_pull_request


ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "blocker_gate"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeCollector:
    def __init__(self, token=None):
        self.token = token

    def collect_issue(self, repository, number):
        return load("closed_direct.json")

    def collect_pull_request(self, repository, number, merge_method):
        return load("pr_same_parent_child.json")


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

        def lookup(finding):
            self.assertEqual(finding.fingerprint, target_fp)
            return {
                "waiver_id": "BW-20260801-001",
                "policy_blob_sha": "sha256:" + "1" * 64,
                "waiver_blob_sha": "sha256:" + "2" * 64,
                "approval_commit": "3" * 40,
                "expires_at": "2026-08-08T00:00:00Z",
            }

        allowed = evaluate_snapshot(snapshot, waiver_lookup=lookup)
        self.assertEqual((allowed["result"], allowed["primary_reason"]), ("ALLOW", "WAIVER_APPLIED"))
        self.assertEqual(allowed["findings"][0]["waiver_evidence"]["approval_commit"], "3" * 40)


class ContractTests(unittest.TestCase):
    def test_runtime_schema_reason_enums_and_policy_doc_are_in_sync(self):
        schema = json.loads(
            (ROOT / "blocker_gate" / "schemas" / "blocker-gate-result-v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(schema["$defs"]["allowReason"]["enum"]), ALLOW_REASONS)
        self.assertEqual(set(schema["$defs"]["blockReason"]["enum"]), BLOCK_REASONS)
        self.assertEqual(set(schema["$defs"]["errorReason"]["enum"]), ERROR_REASONS)
        policy = (ROOT / "docs" / "methods" / "blocker-gate-pre-use-policy.md").read_text(encoding="utf-8")
        self.assertIn('"schema": "blocker-gate-result/v1"', policy)
        self.assertIn('"waiver_evidence": {', policy)

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

    def test_ambiguous_snapshot_never_becomes_allow(self):
        malformed = load("closed_direct.json")
        malformed["mode"] = "unknown"
        result = evaluate_snapshot(malformed)
        self.assertEqual((result["result"], result["exit_code"]), ("ERROR", 20))
        self.assertFalse(result["permit_issued"])


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


if __name__ == "__main__":
    unittest.main()
