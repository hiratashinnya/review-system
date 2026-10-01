"""CLI behavior for the read-only Codex hook trust check."""

from pathlib import Path
import tempfile
import unittest

from codex_hook_trust.repository import resolve_main_checkout
from tests.unit.codex_hook_trust_support import ROOT, make_fake_codex, run_check


class CodexHookTrustCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.codex = make_fake_codex(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_all_trusted_exits_zero_without_output(self):
        result = run_check(self.codex)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_zero_discovered_hooks_reports_project_trust_problem(self):
        result = run_check(self.codex, "zero-hooks")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("定義 6 件に対し発見 0 件", result.stdout)
        expected_repo = resolve_main_checkout(ROOT)
        self.assertIn(f'[projects."{expected_repo}"]', result.stdout)
        self.assertIn('trust_level = "trusted"', result.stdout)
        self.assertIn(".codex/hooks/README.md", result.stdout)

    def test_fewer_discovered_hooks_than_defined_exits_one(self):
        result = run_check(self.codex, "fewer-hooks")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("定義 6 件に対し発見 5 件", result.stdout)

    def test_standard_json_rpc_response_is_accepted(self):
        result = run_check(self.codex, "standard")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mixed_trust_reports_untrusted_key_and_hash(self):
        result = run_check(self.codex, "mixed")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("stop:0:0", result.stdout)
        self.assertIn("sha256:current", result.stdout)
        self.assertNotIn("pre_tool_use:0:0", result.stdout)

    def test_missing_codex_exits_two(self):
        result = run_check(self.codex.with_name("missing-codex"))
        self.assertEqual(result.returncode, 2)

    def test_timeout_exits_two(self):
        result = run_check(self.codex, "timeout", "--timeout", "0.1")
        self.assertEqual(result.returncode, 2)

    def test_malformed_json_rpc_exits_two(self):
        result = run_check(self.codex, "malformed")
        self.assertEqual(result.returncode, 2)

    def test_app_server_request_exits_two(self):
        result = run_check(self.codex, "server-request")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unexpected app-server request", result.stderr)

    def test_missing_hooks_json_is_undetermined_not_anomaly(self):
        result = run_check(self.codex, repo=Path(self.temp.name))
        self.assertEqual(result.returncode, 2)
        self.assertIn("判定不能", result.stderr)
        self.assertIn("hooks.json を読み込めません", result.stderr)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
