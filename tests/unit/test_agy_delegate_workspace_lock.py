"""workspace_lock の契約検査。"""

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


class WorkspaceLockTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def args(self):
        return ["run", "--workspace", str(self.fake.workspace), "--settings", str(self.fake.settings),
                "--executable", str(self.fake.executable), "--prompt", "text", "--print-timeout", "1"]

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
