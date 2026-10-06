"""Anonymous exports, replay denominators, human verdicts and retention."""
import json
import unittest
import test_runner
from jev_hooks.audit_export import counters, export, review
from jev_hooks.evaluator import MockEvaluator
from jev_hooks.runner import run_event


class AuditTests(unittest.TestCase):
    setUp = test_runner.RunnerTests.setUp

    def test_export_replay_review_and_stable_ids(self):
        self.event.update(event_id="sensitive-event", last_assistant_message="secret-content")
        run_event(self.event, self.config, test_runner.Evaluator())
        run_event(self.event, self.config, test_runner.Evaluator())
        fixture = export(self.tmp.name)
        self.assertEqual(len(fixture["records"]), 1)
        record = fixture["records"][0]
        self.assertEqual(export(self.tmp.name), fixture)
        self.assertNotIn("secret-content", json.dumps(fixture))
        self.assertNotIn(self.tmp.name, json.dumps(fixture))
        self.assertEqual(record["notice_delivery"], "not_connected")
        review(self.tmp.name, record["record_id"], "R1", "positive")
        review(self.tmp.name, record["record_id"], "R1", "false_positive")
        result = counters(export(self.tmp.name))["rules"]["R1"]
        self.assertEqual((result["evaluations"], result["reviewed"], result["false_positive"]), (1, 1, 1))
        with self.assertRaises(ValueError):
            review(self.tmp.name, "invalid", "R1", "positive")

    def test_unknown_notice_and_bounded_retention(self):
        self.config["audit_retention"] = 1
        for identifier in ("first", "second"):
            self.event["event_id"] = identifier
            run_event(self.event, self.config, MockEvaluator())
        fixture = export(self.tmp.name)
        self.assertEqual(len(fixture["records"]), 1)
        self.assertEqual(fixture["coverage"]["dropped_records"], 1)
        self.assertEqual(fixture["coverage"]["total_records"], 2)
        self.assertTrue(fixture["records"][0]["notices"])
        self.assertEqual(counters(fixture)["rules"]["R1"]["unknown"], 1)

    def test_failure_notice_contains_no_exception_text(self):
        run_event(self.event, self.config, test_runner.Evaluator(True))
        fixture = export(self.tmp.name)
        self.assertEqual(fixture["records"][0]["fault"], "evaluator_failure")
        self.assertNotIn("SDK credential", json.dumps(fixture))

    def test_key_change_cannot_replay_a_success_or_stale_fault(self):
        import os
        from unittest.mock import patch
        self.config.update(evaluator="jev", api_key_env="JEV_AUDIT_TEST_KEY")
        self.event.update(event_id="key-cycle", hook_event_name="PreToolUse", tool_name="Read", tool_use_id="read")
        with patch.dict(os.environ, {"JEV_AUDIT_TEST_KEY": "local-placeholder"}):
            self.assertEqual(run_event(self.event, self.config, MockEvaluator()), {})
        with patch.dict(os.environ, {}, clear=True):
            blocked = run_event(self.event, self.config, MockEvaluator())
            self.assertEqual(blocked["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertEqual(run_event(self.event, self.config, MockEvaluator()), blocked)
        with patch.dict(os.environ, {"JEV_AUDIT_TEST_KEY": "local-placeholder"}):
            self.assertEqual(run_event(self.event, self.config, MockEvaluator()), {})
        fixture = export(self.tmp.name)
        self.assertEqual(len(fixture["records"]), 2)
        self.assertNotIn("local-placeholder", json.dumps(fixture))
        self.assertTrue(fixture["records"][-1]["denied"])

    def test_repository_fixture_is_a_counter_consumer_input(self):
        from pathlib import Path
        fixture = json.loads(Path("examples/jev_hooks/audit-export.json").read_text())
        result = counters(fixture)
        self.assertEqual(result["unique_requests"], 2)
        self.assertEqual(result["rules"]["R1"]["false_positive"], 1)
        self.assertEqual(result["rules"]["R1"]["unknown"], 1)

    def test_same_request_id_in_distinct_sessions_has_distinct_denominators(self):
        self.event["event_id"] = "shared-id"
        for session in ("first-session", "second-session"):
            self.event["session_id"] = session
            run_event(self.event, self.config, MockEvaluator())
        fixture = export(self.tmp.name)
        self.assertEqual(counters(fixture)["unique_requests"], 2)
        self.assertEqual(len({r["session_id"] for r in fixture["records"]}), 2)
