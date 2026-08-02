"""Issue #296 dependency/closure resolver fixtures。"""

import json
from pathlib import Path
import unittest

from blocker_gate.resolver import evaluate_snapshot


FIXTURES = Path(__file__).parents[1] / "fixtures" / "blocker_gate"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ResolverFixtureTests(unittest.TestCase):
    def test_open_direct_blocker(self):
        result = evaluate_snapshot(load("open_direct.json"))
        self.assertEqual((result["result"], result["exit_code"]), ("BLOCK", 10))
        self.assertEqual(result["findings"][0]["path"], ["example/repo#10", "example/repo#9"])

    def test_closed_direct_blocker_allows(self):
        result = evaluate_snapshot(load("closed_direct.json"))
        self.assertEqual((result["result"], result["primary_reason"]), ("ALLOW", "NO_VIOLATION"))

    def test_transitive_returns_every_open_path(self):
        result = evaluate_snapshot(load("open_transitive.json"))
        paths = [item["path"] for item in result["findings"]]
        self.assertEqual(
            paths,
            [
                ["example/repo#10", "example/repo#9"],
                ["example/repo#10", "example/repo#9", "example/repo#8"],
            ],
        )

    def test_cycle_is_error_not_allow(self):
        result = evaluate_snapshot(load("cycle.json"))
        self.assertEqual((result["result"], result["exit_code"]), ("ERROR", 20))
        self.assertIn("GRAPH_CYCLE", result["reasons"])
        self.assertFalse(result["permit_issued"])

    def test_blocker_only_parent_cycle_is_error_not_allow(self):
        result = evaluate_snapshot(load("parent_cycle.json"))
        self.assertEqual((result["result"], result["exit_code"]), ("ERROR", 20))
        self.assertIn("GRAPH_CYCLE", result["reasons"])
        self.assertFalse(result["permit_issued"])

    def test_collection_failures_fail_close(self):
        cases = {
            "pagination_incomplete.json": "PAGINATION_INCOMPLETE",
            "partial_response.json": "API_PARTIAL_RESPONSE",
            "api_failure.json": "API_UNAVAILABLE",
            "permission_denied.json": "API_PERMISSION",
        }
        for name, reason in cases.items():
            with self.subTest(name=name):
                result = evaluate_snapshot(load(name))
                self.assertEqual(result["result"], "ERROR")
                self.assertEqual(result["exit_code"], 20)
                self.assertIn(reason, result["reasons"])
                self.assertFalse(result["pages_complete"])
                self.assertFalse(result["permit_issued"])

    def test_error_has_priority_over_block(self):
        snapshot = load("open_direct.json")
        snapshot["errors"] = ["API_PARTIAL_RESPONSE"]
        snapshot["pages_complete"] = False
        result = evaluate_snapshot(snapshot)
        self.assertEqual(result["result"], "ERROR")
        self.assertIn("OPEN_BLOCKER", result["reasons"])
        self.assertEqual(result["primary_reason"], "API_PARTIAL_RESPONSE")

    def test_graph_273_lists_all_unresolved_paths(self):
        result = evaluate_snapshot(load("graph_273_anonymized.json"))
        actual = [(item["code"], item["path"]) for item in result["findings"]]
        self.assertEqual(
            actual,
            [
                ("CLOSURE_OPEN_DESCENDANT", ["example/repo#293", "example/repo#273"]),
                ("CLOSURE_OPEN_DESCENDANT", ["example/repo#293", "example/repo#294"]),
                ("CLOSURE_OPEN_DESCENDANT", ["example/repo#293", "example/repo#295"]),
                ("OPEN_BLOCKER", ["example/repo#273", "example/repo#294"]),
                ("OPEN_BLOCKER", ["example/repo#273", "example/repo#294", "example/repo#295"]),
            ],
        )


class ClosureInvariantTests(unittest.TestCase):
    def test_parent_and_child_same_pr_allow(self):
        result = evaluate_snapshot(load("pr_same_parent_child.json"))
        self.assertEqual(result["result"], "ALLOW")

    def test_parent_only_same_pr_blocks_open_child(self):
        result = evaluate_snapshot(load("pr_parent_only.json"))
        self.assertEqual(result["result"], "BLOCK")
        self.assertEqual(result["primary_reason"], "CLOSURE_OPEN_DESCENDANT")

    def test_same_pr_blocker_virtual_close_allows(self):
        result = evaluate_snapshot(load("pr_same_blocker.json"))
        self.assertEqual(result["result"], "ALLOW")

    def test_manual_parent_early_close_blocks(self):
        result = evaluate_snapshot(load("manual_parent_early_close.json"))
        self.assertEqual(result["result"], "BLOCK")
        self.assertEqual(result["findings"][0]["path"], ["example/repo#1", "example/repo#2"])


if __name__ == "__main__":
    unittest.main()
