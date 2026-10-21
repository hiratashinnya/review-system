"""record_privacy の契約検査。"""

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


class RecordPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def args(self):
        return ["run", "--workspace", str(self.fake.workspace), "--settings", str(self.fake.settings),
                "--executable", str(self.fake.executable), "--prompt", "text", "--print-timeout", "1"]

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
        self.assertEqual(observations, [(0o600, 0o600)] * 3)
        summary = json.loads((root / "conversation-conversation-private.json").read_text())
        self.assertNotIn("response", summary)
        self.assertNotIn("error", summary)
        self.assertEqual(json.loads((root / "private/result.json").read_text())["response"],
                         "private response")
