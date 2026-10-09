from copy import deepcopy
import json
from io import StringIO
import unittest

from blocker_gate.model import POLICY_VERSION
from pr_merge_gate.cli import run
from pr_merge_gate.gate import PrMergeGateError, evaluate_owner_report


def snapshot(head="a" * 40, *, blocked=False, number=50):
    nodes = {}
    closing = []
    if blocked:
        closing = ["example/repo#10"]
        nodes = {
            "example/repo#10": {"node_id": "I10", "state": "OPEN", "blocked_by": ["example/repo#9"], "parent": None, "children": []},
            "example/repo#9": {"node_id": "I9", "state": "OPEN", "blocked_by": [], "parent": None, "children": []},
        }
    return {
        "schema": "blocker-gate-snapshot/v1", "policy_version": POLICY_VERSION,
        "mode": "pr-merge", "repository": "example/repo",
        "subject": {"type": "pull_request", "number": number}, "roots": closing,
        "virtual_closed": closing, "nodes": nodes, "pages_complete": True,
        "errors": [], "fetched_at": "2026-08-10T00:00:00Z",
        "graphql_closing_set": closing, "delivered_message_closing_set": [],
        "binding": {"head_oid": head, "expected_commit_count": 1,
                    "base_ref_name": "main", "default_branch": "main",
                    "merge_method": "rebase", "intercepted_commit_title_fingerprint": None,
                    "intercepted_commit_message_fingerprint": None,
                    "message_source_fingerprint": "sha256:" + "2" * 64,
                    "delivered_message_fingerprint": "sha256:" + "3" * 64,
                    "repository_merge_settings_fingerprint": None,
                    "operation_fingerprint": "sha256:" + "1" * 64,
                    "snapshot_fingerprint": None, "attempt": 1,
                    "pr_state": "OPEN", "pr_is_draft": False},
    }


class FakeCollector:
    def __init__(self, templates):
        self.templates, self.calls = list(templates), []

    def collect_pull_request(self, repository, number, method, **kwargs):
        self.calls.append((repository, number, method, kwargs))
        value = deepcopy(self.templates.pop(0))
        value["binding"]["attempt"] = kwargs["attempt"]
        return value


class OwnerReportTests(unittest.TestCase):
    def evaluate(self, templates):
        collector = FakeCollector(templates)
        report = evaluate_owner_report(
            "example/repo", 50, "rebase", collector_factory=lambda token: collector
        )
        return report, collector

    def test_allow_report_is_fresh_and_never_authorizes_execution(self):
        report, collector = self.evaluate([snapshot(), snapshot()])
        self.assertEqual(report["verdict"], "ALLOW")
        self.assertEqual(len(collector.calls), 2)
        self.assertTrue(report["owner_action_required"])
        self.assertFalse(report["automatic_merge_authorized"])
        self.assertFalse(report["merge_api_called"])

    def test_block_report_stops_after_first_read(self):
        report, collector = self.evaluate([snapshot(blocked=True)])
        self.assertEqual((report["verdict"], report["reason"]), ("BLOCK", "OPEN_BLOCKER"))
        self.assertEqual(len(collector.calls), 1)
        self.assertFalse(report["automatic_merge_authorized"])

    def test_unstable_reads_fail_closed(self):
        reads = [item for _ in range(3) for item in (snapshot("a" * 40), snapshot("b" * 40))]
        report, collector = self.evaluate(reads)
        self.assertEqual((report["verdict"], report["reason"]), ("ERROR", "REEVALUATION_LIMIT"))
        self.assertEqual(len(collector.calls), 6)
        self.assertFalse(report["automatic_merge_authorized"])

    def test_invalid_request_and_identity_mismatch_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_owner_report("example/repo", True, "rebase")
        with self.assertRaises(PrMergeGateError) as caught:
            self.evaluate([snapshot(number=51)])
        self.assertEqual(caught.exception.reason, "IDENTITY_MISMATCH")

    def test_report_verb_returns_json_without_calling_merge_api(self):
        stdout, stderr = StringIO(), StringIO()
        code = run(
            ["report", "50", "--repository", "example/repo", "--merge-method", "rebase"],
            stdout=stdout, stderr=stderr,
            collector_factory=lambda token: FakeCollector([snapshot(), snapshot()]),
            token_resolver=lambda: "test-token",
        )
        report = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(report["verdict"], "ALLOW")
        self.assertFalse(report["merge_api_called"])
        self.assertIn("owner action required", stderr.getvalue())
