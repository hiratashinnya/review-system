"""異常信号と部分応答の保持。意味的完了を偽装しない。"""

import json
import unittest

from agy_delegate.results import normalize
from tests.unit.agy_delegate_fixtures import synthetic_success


class ResultTests(unittest.TestCase):
    def test_success_is_candidate_only(self):
        result = normalize("run", json.dumps(synthetic_success(response="これから調べます")), "", 0)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.classification != "success_candidate", result.exit_code != 0)

    def test_denial_wins_and_retains_all_reasons(self):
        output = synthetic_success(response="partial")
        output.update(status="ERROR", denied_actions=[{"action": "write_file", "display_name": "WriteFile"}])
        result = normalize("run", json.dumps(output), "error: print timeout no output produced", 3)
        self.assertEqual(result.classification, "denied")
        self.assertEqual(result.response, "partial")
        self.assertTrue(result.truncated)
        self.assertEqual(set(result.reasons), {"d0_denied_actions", "status_not_success",
                                              "stderr_error", "print_timeout", "no_output", "nonzero_exit"})

    def test_malformed_missing_wrong_types_unknown_format(self):
        for output in ("{", "[]", "{}", json.dumps(synthetic_success() | {"denied_actions": None}),
                       json.dumps(synthetic_success() | {"extra": "unknown"})):
            with self.subTest(output=output):
                self.assertNotEqual(normalize("run", output, "", 0).exit_code, 0)

    def test_path_identity_and_authentication(self):
        for identity in ("../outside", "/absolute", "", "a/b", "a\\b", "a\n"):
            self.assertNotEqual(normalize("run", json.dumps(synthetic_success(identity)), "", 0).exit_code, 0)
        result = normalize("run", json.dumps(synthetic_success()), "error: authentication denied", 0)
        self.assertEqual(result.classification, "failed")
        self.assertEqual(result.stderr_length, len("error: authentication denied"))

    def test_error_with_response_and_timeout_with_partial_fail(self):
        error = normalize("r", json.dumps(synthetic_success() | {"status": "ERROR"}), "", 0)
        timeout = normalize("r", json.dumps(synthetic_success()), "[agy] print timeout", 0)
        self.assertNotEqual(error.exit_code, 0)
        self.assertNotEqual(timeout.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
