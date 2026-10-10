"""CLI behavior for the read-only Codex hook trust check."""

from pathlib import Path
import unittest

from tests.unit.codex_hook_trust_support import (
    CodexHookTrustTestMixin, hook_count_report, one_missing_hook_report,
)


class CodexHookTrustCliTests(CodexHookTrustTestMixin, unittest.TestCase):
    def test_all_trusted_exits_zero_without_output(self):
        result = self._run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_zero_discovered_hooks_reports_project_trust_problem(self):
        result = self._run_check("zero-hooks")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(hook_count_report(self.repo, 0), result.stdout)
        expected_repo = self.repo.resolve()
        self.assertIn(f'[projects."{expected_repo}"]', result.stdout)
        self.assertIn('trust_level = "trusted"', result.stdout)
        self.assertIn(".codex/hooks/README.md", result.stdout)

    def test_fewer_discovered_hooks_than_defined_exits_one(self):
        result = self._run_check("fewer-hooks")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(one_missing_hook_report(self.repo), result.stdout)

    def test_user_hook_does_not_hide_missing_project_hook(self):
        result = self._run_check("project-one-short-user-one")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(one_missing_hook_report(self.repo), result.stdout)

    def test_user_hooks_do_not_hide_missing_project_hooks(self):
        result = self._run_check("user-only-six")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(hook_count_report(self.repo, 0), result.stdout)

    def test_untrusted_user_hook_does_not_fail_trusted_project_hooks(self):
        result = self._run_check("project-user-untrusted")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_standard_json_rpc_response_is_accepted(self):
        result = self._run_check("standard")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mixed_trust_reports_untrusted_key_and_hash(self):
        result = self._run_check("mixed")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("pre_tool_use:2:0", result.stdout)
        self.assertIn("sha256:current", result.stdout)
        self.assertNotIn("pre_tool_use:0:0", result.stdout)

    def test_missing_codex_exits_two(self):
        result = self._run_check(executable=self.codex.with_name("missing-codex"))
        self.assertEqual(result.returncode, 2)

    def test_timeout_exits_two(self):
        result = self._run_check("timeout", "--timeout", "0.1")
        self.assertEqual(result.returncode, 2)

    def test_malformed_json_rpc_exits_two(self):
        result = self._run_check("malformed")
        self.assertEqual(result.returncode, 2)

    def test_app_server_request_exits_two(self):
        result = self._run_check("server-request")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unexpected app-server request", result.stderr)

    def test_missing_hooks_json_is_undetermined_not_anomaly(self):
        result = self._run_check(repo=Path(self.temp.name))
        self.assertEqual(result.returncode, 2)
        self.assertIn("判定不能", result.stderr)
        self.assertIn("hooks.json を読み込めません", result.stderr)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
