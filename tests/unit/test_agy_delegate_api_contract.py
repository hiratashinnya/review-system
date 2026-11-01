"""api_contract の契約検査。"""

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


class ApiContractTests(unittest.TestCase):
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
