"""stderr_contract の契約検査。"""

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


class StderrContractTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def args(self):
        return ["run", "--workspace", str(self.fake.workspace), "--settings", str(self.fake.settings),
                "--executable", str(self.fake.executable), "--prompt", "text", "--print-timeout", "1"]

    def test_unknown_stderr_stops_without_unmeasured_d0_classification(self):
        for text in ("authentication", "unauthorized", "security denied", "private warning"):
            result = normalize("run", json.dumps(synthetic_success()), text, 0)
            self.assertEqual(result.classification, "failed")
            self.assertEqual(result.reasons, ["stderr_unrecognized"])
            self.assertEqual(result.stderr_length, len(text))
