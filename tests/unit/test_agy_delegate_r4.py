"""r4 是正契約の独立した否定・待機・秘匿検証。"""

import inspect
import io
import json
import os
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import fields, replace
from unittest.mock import patch

from agy_delegate.cli import main
from agy_delegate.process import execute
from agy_delegate.records import execution_lock, save_record, state_root
from agy_delegate.results import normalize
from agy_delegate.runner import run, run_parallel
from agy_delegate.types import Request, Result
from tests.unit.agy_delegate_fixtures import FakeWorkspace, run_synthetic, synthetic_success


class R4ContractTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def args(self):
        return ["run", "--workspace", str(self.fake.workspace), "--settings", str(self.fake.settings),
                "--executable", str(self.fake.executable), "--prompt", "text", "--print-timeout", "1"]

    def test_caller_missing_stopped_invalid_and_ready(self):
        for state, reason in ((None, "caller_state_unverified"), ("stopped", "caller_stopped"),
                              ("unknown", "caller_state_unverified")):
            result = run_synthetic(replace(self.fake.request(), caller_state=state))
            self.assertIn(reason, result.reasons)
        self.assertFalse((self.fake.workspace / "launched.json").exists())
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            main(self.args())
        self.assertIn("--caller-state", stderr.getvalue())
        self.assertEqual(run_synthetic(self.fake.request()).exit_code, 0)

    def test_production_api_has_no_verifier_injection_or_inert_fields(self):
        self.assertEqual(list(inspect.signature(run).parameters), ["request"])
        self.assertEqual(list(inspect.signature(run_parallel).parameters), ["requests", "max_concurrency"])
        with self.assertRaises(TypeError):
            run(self.fake.request(), runtime_verifier=lambda _: [])
        self.assertNotIn("writes", {field.name for field in fields(Request)})
        self.assertNotIn("completed", {field.name for field in fields(Result)})

    def test_cli_parallel_reaches_api_and_reports_each_failure(self):
        outcomes = [Result("one", classification="success_candidate"), Result("two", reasons=["failure"])]
        stdout = io.StringIO()
        with patch("agy_delegate.cli.run_parallel", return_value=outcomes) as child, redirect_stdout(stdout):
            code = main(self.args() + ["--caller-state", "ready", "--prompt", "other",
                                       "--max-concurrency", "2"])
        self.assertEqual(code, 1)
        self.assertEqual([json.loads(line)["run_id"] for line in stdout.getvalue().splitlines()],
                         ["one", "two"])
        self.assertEqual([r.prompt for r in child.call_args.args[0]], ["text", "other"])
        self.assertEqual(child.call_args.kwargs, {"max_concurrency": 2})

    def test_workspace_lock_waits_until_release(self):
        root = state_root(self.fake.workspace)
        started, acquired = threading.Event(), threading.Event()
        errors = []
        def contender():
            started.set()
            try:
                with execution_lock(root):
                    acquired.set()
            except Exception as error:
                errors.append(error)
        with execution_lock(root):
            thread = threading.Thread(target=contender)
            thread.start()
            self.assertTrue(started.wait(1))
            self.assertFalse(acquired.wait(0.1))
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertTrue(acquired.is_set())
        self.assertEqual(errors, [])

    def test_unknown_stderr_stops_without_unmeasured_d0_classification(self):
        for text in ("authentication", "unauthorized", "security denied", "private warning"):
            result = normalize("run", json.dumps(synthetic_success()), text, 0)
            self.assertEqual(result.classification, "failed")
            self.assertEqual(result.reasons, ["stderr_unrecognized"])
            self.assertEqual(result.stderr_length, len(text))

    def test_version_mismatch_prevents_prompt_and_verified_version_is_recorded(self):
        executable = self.fake.executable
        executable.write_text(executable.read_text().replace("print('1.3.3')", "print('9.9.9')"))
        result = execute(self.fake.request(), "run")
        self.assertIn("agy_version_unverified_or_mismatch", result.reasons)
        self.assertFalse((self.fake.workspace / "launched.json").exists())
        executable.write_text(executable.read_text().replace("print('9.9.9')", "print('1.3.3')"))
        result = run_synthetic(self.fake.request())
        self.assertEqual(result.agy_version, "1.3.3")
        record = self.fake.workspace / "tmp/agy" / result.run_id / "result.json"
        self.assertEqual(json.loads(record.read_text())["agy_version"], "1.3.3")

    def test_path_allowlist_rejects_unicode_quotes_tabs_and_shell_characters(self):
        from agy_delegate.permissions import expected_rules
        for character in ('"', "\t", "\u2019", "\u2018", "\u201c", "\u201d", "(", ")", "%", "\\"):
            with self.subTest(character=character), self.assertRaises(ValueError):
                expected_rules(self.fake.workspace / ("bad" + character + "path"))
        self.assertTrue(expected_rules(self.fake.workspace)["allow"])

    def test_records_are_private_from_creation_and_no_double_response(self):
        root = state_root(self.fake.workspace)
        result = Result("private", classification="success_candidate", response="private response",
                        agy_exit_code=0, status="SUCCESS", conversation_id="conversation-private")
        (root / result.run_id).mkdir()
        real_open = os.open
        observations = []
        def observe(path, flags, mode):
            descriptor = real_open(path, flags, mode)
            observations.append((mode, os.fstat(descriptor).st_mode & 0o777))
            return descriptor
        previous_umask = os.umask(0)
        try:
            with patch("agy_delegate.records.os.open", side_effect=observe):
                save_record(root, self.fake.request(), result)
        finally:
            os.umask(previous_umask)
        self.assertEqual(observations, [(0o600, 0o600), (0o600, 0o600)])
        summary = json.loads((root / "conversation-conversation-private.json").read_text())
        self.assertNotIn("response", summary)
        self.assertNotIn("error", summary)
        self.assertEqual(json.loads((root / "private/result.json").read_text())["response"],
                         "private response")

