"""外側timeoutでもstderr拒否・全異常理由と部分応答を保持する。"""

import json
import subprocess
import unittest
from unittest.mock import patch

from agy_delegate.process import execute
from agy_delegate.runner import run
from tests.unit.agy_delegate_fixtures import FakeWorkspace, synthetic_success


class ProcessTimeoutTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def test_production_without_timeout_outcome_evidence_never_launches(self):
        with patch("agy_delegate.runner.execute") as child:
            result = run(self.fake.request())
        child.assert_not_called()
        self.assertIn("print_timeout_outcome_unverified", result.reasons)

    def test_duration_arguments_follow_measured_help_without_certifying_timeout_result(self):
        request = self.fake.request()
        completed = subprocess.CompletedProcess([], 0, json.dumps(synthetic_success()), "")
        with patch("agy_delegate.process.verified_version", return_value="1.4.8"), patch(
            "agy_delegate.process.subprocess.run", return_value=completed
        ) as child:
            result = execute(request, "run")
        arguments, options = child.call_args
        argv = arguments[0]
        self.assertEqual(argv[argv.index("--print-timeout") + 1], f"{request.print_timeout}s")
        self.assertEqual(options["timeout"], request.print_timeout + 10)
        self.assertEqual(options["cwd"], request.workspace.resolve())
        self.assertEqual(result.classification, "success_candidate")

    def timeout(self, stdout, stderr):
        timeout = subprocess.TimeoutExpired(["fake"], 1, output=stdout, stderr=stderr)
        with patch("agy_delegate.process.verified_version", return_value="1.4.8"), patch("agy_delegate.process.subprocess.run", side_effect=timeout) as child:
            result = execute(self.fake.request(), "run")
        child.assert_called_once()
        self.assertNotEqual(result.exit_code, 0)
        self.assertTrue(result.truncated)
        self.assertEqual(result.classification != "success_candidate", result.exit_code != 0)
        self.assertEqual(result.agy_exit_code, -1)
        self.assertIn("process_timeout", result.reasons)
        return result

    def test_timeout_keeps_all_json_and_stderr_failures_bytes_and_strings(self):
        stdout = json.dumps(synthetic_success(response="partial") |
                            {"status": "ERROR", "denied_actions": [{"action": "command", "display_name": "RunCommand"}]})
        reasons = {"d0_denied_actions", "status_not_success", "stderr_error", "no_output", "print_timeout", "nonzero_exit", "process_timeout"}
        for marker in ("authentication", "unauthorized", "security denied"):
            stderr = "error: no output produced " + marker
            for raw in (False, True):
                with self.subTest(marker=marker, raw=raw):
                    result = self.timeout(stdout.encode() if raw else stdout,
                                          stderr.encode() + b"\xff" if raw else stderr)
                    self.assertEqual(result.classification, "denied")
                    self.assertEqual(result.response, "partial")
                    self.assertEqual(result.conversation_id, "conversation-1")
                    self.assertEqual(result.denied_actions, [{"action": "command", "display_name": "RunCommand"}])
                    self.assertEqual(set(result.reasons), reasons)

    def test_timeout_keeps_json_contract_failures(self):
        cases = [("{", "json_invalid"),
                 (json.dumps(synthetic_success() | {"response": None}), "field_invalid:response"),
                 (json.dumps({"status": "SUCCESS"}), "field_invalid:usage"),
                 (json.dumps(synthetic_success() | {"extra": 1}), "unknown_output_fields")]
        for stdout, reason in cases:
            with self.subTest(reason=reason):
                self.assertIn(reason, self.timeout(stdout, "error:").reasons)

    def test_timeout_without_captured_output_remains_failed(self):
        result = self.timeout(None, None)
        self.assertEqual(result.classification, "failed")
        self.assertEqual(set(result.reasons), {"print_timeout", "nonzero_exit", "json_invalid",
                                              "process_timeout"})


if __name__ == "__main__":
    unittest.main()
