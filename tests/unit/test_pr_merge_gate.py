from copy import deepcopy
import unittest

from pr_merge_gate.classifier import MergeOperation
from pr_merge_gate.gate import evaluate_merge_operation, fail_closed


FP1 = "sha256:" + "1" * 64
FP2 = "sha256:" + "2" * 64
FP3 = "sha256:" + "3" * 64


def operation():
    return MergeOperation("example/repo", 50, "rebase", "cli-direct", None, None, None, FP1)


def snapshot(*, head="a" * 40, closing=(), nodes=None, state="OPEN", draft=False):
    refs = list(closing)
    return {
        "schema": "blocker-gate-snapshot/v1",
        "policy_version": "1.0",
        "mode": "pr-merge",
        "repository": "example/repo",
        "subject": {"type": "pull_request", "number": 50},
        "roots": refs,
        "virtual_closed": refs,
        "nodes": nodes or {},
        "pages_complete": True,
        "errors": [],
        "fetched_at": "2026-08-10T00:00:00Z",
        "graphql_closing_set": refs,
        "delivered_message_closing_set": [],
        "binding": {
            "head_oid": head,
            "base_ref_name": "main",
            "default_branch": "main",
            "merge_method": "rebase",
            "intercepted_commit_title_fingerprint": None,
            "intercepted_commit_message_fingerprint": None,
            "message_source_fingerprint": FP2,
            "delivered_message_fingerprint": FP3,
            "repository_merge_settings_fingerprint": None,
            "operation_fingerprint": FP1,
            "snapshot_fingerprint": None,
            "attempt": 1,
            "pr_state": state,
            "pr_is_draft": draft,
        },
    }


class FakeCollector:
    def __init__(self, templates):
        self.templates = list(templates)
        self.calls = []

    def collect_pull_request(self, repository, number, merge_method, **kwargs):
        self.calls.append((repository, number, merge_method, kwargs))
        value = deepcopy(self.templates.pop(0))
        value["binding"]["attempt"] = kwargs["attempt"]
        return value


def factory_for(templates, holder):
    def factory(token):
        holder.append(FakeCollector(templates))
        return holder[0]
    return factory


class MergeGateTests(unittest.TestCase):
    def test_allow_requires_two_identical_fresh_reads(self):
        holders = []
        evidence = evaluate_merge_operation(
            operation(), collector_factory=factory_for([snapshot(), snapshot()], holders)
        )
        self.assertEqual((evidence["result"], evidence["next_action"]), ("ALLOW", "CONTINUE_ORIGINAL_ONCE"))
        self.assertTrue(evidence["permit_issued"])
        self.assertFalse(evidence["merge_api_called"])
        self.assertEqual(len(holders[0].calls), 2)

    def test_block_returns_without_second_read_and_never_calls_merge(self):
        nodes = {
            "example/repo#10": {
                "node_id": "I10", "state": "OPEN", "blocked_by": ["example/repo#9"],
                "parent": None, "children": [],
            },
            "example/repo#9": {
                "node_id": "I9", "state": "OPEN", "blocked_by": [],
                "parent": None, "children": [],
            },
        }
        holders = []
        evidence = evaluate_merge_operation(
            operation(),
            collector_factory=factory_for(
                [snapshot(closing=("example/repo#10",), nodes=nodes)], holders
            ),
        )
        self.assertEqual((evidence["result"], evidence["reason"]), ("BLOCK", "OPEN_BLOCKER"))
        self.assertEqual(len(holders[0].calls), 1)
        self.assertFalse(evidence["merge_api_called"])

    def test_pr_state_and_draft_are_policy_block_reasons(self):
        for state, draft, reason in (
            ("CLOSED", False, "PR_NOT_OPEN"),
            ("OPEN", True, "PR_DRAFT"),
        ):
            with self.subTest(reason=reason):
                evidence = evaluate_merge_operation(
                    operation(), collector_factory=lambda token: FakeCollector(
                        [snapshot(state=state, draft=draft)]
                    )
                )
                self.assertEqual((evidence["result"], evidence["reason"]), ("BLOCK", reason))

    def test_changed_snapshot_retries_and_three_unstable_attempts_error(self):
        templates = []
        for _ in range(3):
            templates.extend([snapshot(head="a" * 40), snapshot(head="b" * 40)])
        evidence = evaluate_merge_operation(
            operation(), collector_factory=lambda token: FakeCollector(templates)
        )
        self.assertEqual(
            (evidence["result"], evidence["reason"], evidence["permit_issued"]),
            ("ERROR", "REEVALUATION_LIMIT", False),
        )

    def test_classifier_failure_helper_never_issues_permit(self):
        evidence = fail_closed(FP1, "AUTO_MERGE_DENIED")
        self.assertEqual((evidence["result"], evidence["exit_code"]), ("BLOCK", 10))
        self.assertFalse(evidence["permit_issued"])
        self.assertFalse(evidence["merge_api_called"])


if __name__ == "__main__":
    unittest.main()
