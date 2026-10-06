"""CLI exports JSON metadata and rejects nonexistent human review targets."""
import json
import subprocess
import sys
import unittest
import test_runner
from jev_hooks.runner import run_event


class AuditCliTests(unittest.TestCase):
    setUp = test_runner.RunnerTests.setUp

    def invoke(self, *arguments):
        return subprocess.run([sys.executable, "-m", "jev_hooks.audit_cli", "--state-dir", self.tmp.name,
                               *arguments], text=True, capture_output=True)

    def test_export_and_counter_stdout_have_one_json_document(self):
        run_event(self.event, self.config, test_runner.Evaluator())
        result = self.invoke("export")
        self.assertEqual(result.returncode, 0)
        fixture = json.loads(result.stdout)
        self.assertEqual(len(fixture["records"]), 1)
        result = self.invoke("counters")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["unique_requests"], 1)

    def test_invalid_review_id_has_no_success_json_or_raw_id(self):
        run_event(self.event, self.config, test_runner.Evaluator())
        result = self.invoke("review", "sensitive-invalid-id", "R1", "positive")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("sensitive-invalid-id", result.stderr)
