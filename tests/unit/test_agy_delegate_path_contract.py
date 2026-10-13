"""path_contract の契約検査。"""

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


class PathContractTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def args(self):
        return ["run", "--workspace", str(self.fake.workspace), "--settings", str(self.fake.settings),
                "--executable", str(self.fake.executable), "--prompt", "text", "--print-timeout", "1"]

    def test_path_allowlist_rejects_unicode_quotes_tabs_and_shell_characters(self):
        from agy_delegate.permissions import expected_rules
        for character in ('"', "\t", "\u2019", "\u2018", "\u201c", "\u201d", "(", ")", "%", "\\"):
            with self.subTest(character=character), self.assertRaises(ValueError):
                expected_rules(self.fake.workspace / ("bad" + character + "path"))
        self.assertTrue(expected_rules(self.fake.workspace)["allow"])
