"""version_contract の契約検査。"""

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


class VersionContractTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def args(self):
        return ["run", "--workspace", str(self.fake.workspace), "--settings", str(self.fake.settings),
                "--executable", str(self.fake.executable), "--prompt", "text", "--print-timeout", "1"]

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
