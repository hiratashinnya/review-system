"""通常 CLI の検査省略/任意フラグが無く、run は未確認時停止する。"""

import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

from agy_delegate.cli import main
from agy_delegate.records import save_record, state_root
from agy_delegate.types import Result
from tests.unit.agy_delegate_fixtures import FakeWorkspace


class CliTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def test_inspect_static_only_and_run_blocked(self):
        args = ["--workspace", str(self.fake.workspace), "--settings", str(self.fake.settings)]
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(["inspect"] + args), 0)
        self.assertFalse(json.loads(stdout.getvalue())["effective_settings_verified"])
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["run"] + args + ["--executable", str(self.fake.executable),
                                         "--prompt", "text; $(not-executed)", "--print-timeout", "1", "--caller-state", "ready"])
        self.assertNotEqual(code, 0)
        self.assertIn("settings_permission_merge_unverified", json.loads(stdout.getvalue())["reasons"])
        self.assertFalse((self.fake.workspace / "launched.json").exists())

    def test_no_opaque_or_bypass_flags(self):
        for flag in ("--skip-inspection", "--dangerously-skip-permissions", "--sandbox", "--agy-flag"):
            stderr = io.StringIO()
            args = ["run", "--workspace", str(self.fake.workspace), "--settings", str(self.fake.settings),
                    "--executable", str(self.fake.executable), "--prompt", "text",
                    "--print-timeout", "1", "--caller-state", "ready", flag]
            with redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
                main(args)
            self.assertEqual(error.exception.code, 2)
            self.assertIn("unrecognized arguments: " + flag, stderr.getvalue())

    def test_public_diagnostics_redact_secrets_and_local_record_retains_them(self):
        result = Result("run-secret", classification="denied", agy_exit_code=3,
                        status="ERROR", reasons=["agy_error_present", "d0_denied_actions"],
                        error="private-error-token", response="private-response-token",
                        denied_actions=[{"action": "command", "display_name": "private-denial-token"}],
                        artifacts=["/private-user/private-artifact.png"])
        request = self.fake.request()
        root = state_root(self.fake.workspace)
        (root / result.run_id).mkdir(mode=0o700)
        save_record(root, request, result)
        stdout = io.StringIO()
        args = ["run", "--workspace", str(self.fake.workspace), "--settings", str(self.fake.settings),
                "--executable", str(self.fake.executable), "--prompt", "text", "--print-timeout", "1", "--caller-state", "ready"]
        with patch("agy_delegate.cli.run", return_value=result) as child, redirect_stdout(stdout):
            code = main(args)
        child.assert_called_once()
        public = json.loads(stdout.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(public["agy_exit_code"], 3)
        self.assertEqual(public["status"], "ERROR")
        self.assertEqual(public["reasons"], result.reasons)
        self.assertEqual(public["classification"], "denied")
        for secret in (result.error, result.response, "private-denial-token", result.artifacts[0]):
            self.assertNotIn(secret, stdout.getvalue())
        for name in ("error", "response"):
            self.assertEqual(public[name], "[redacted: local result.json]")
        path = root / result.run_id / "result.json"
        local = json.loads(path.read_text())
        self.assertEqual(local["error"], result.error)
        self.assertEqual(local["response"], result.response)
        self.assertEqual(local["denied_actions"], result.denied_actions)
        self.assertEqual(local["artifacts"], result.artifacts)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_public_status_and_identifier_expose_only_known_or_valid_values(self):
        args = ["run", "--workspace", str(self.fake.workspace), "--settings", str(self.fake.settings),
                "--executable", str(self.fake.executable), "--prompt", "text", "--print-timeout", "1", "--caller-state", "ready"]
        cases = (("SUCCESS", "conversation-1", "SUCCESS", "conversation-1"),
                 ("ERROR", None, "ERROR", None),
                 ("private-status-token", "private/id token", "[redacted: unrecognized status]",
                  "[redacted: invalid id]"))
        for status, identity, expected_status, expected_identity in cases:
            with self.subTest(status=status):
                result = Result("run-public", classification="failed", status=status,
                                conversation_id=identity, reasons=["status_not_success"])
                stdout = io.StringIO()
                with patch("agy_delegate.cli.run", return_value=result), redirect_stdout(stdout):
                    main(args)
                public = json.loads(stdout.getvalue())
                self.assertEqual(public["status"], expected_status)
                self.assertEqual(public["conversation_id"], expected_identity)
                for raw in ("private-status-token", "private/id token"):
                    self.assertNotIn(raw, stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
