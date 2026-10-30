"""明示selector/argv境界と、親environmentを変更しない子限定設定。"""

import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from agy_delegate.launch_profile import child_environment, native_arguments
from agy_delegate.version import verified_version
from tests.unit.agy_delegate_fixtures import FakeWorkspace


class LaunchProfileTests(unittest.TestCase):
    def test_fixed_project_and_literal_prompt_remain_separate_arguments(self):
        executable = Path("/tmp/synthetic agy")
        prompt = "日本語; $(not-executed) 'literal'"
        self.assertEqual(native_arguments(executable, "-p", prompt),
                         [str(executable.resolve()), "--project", "default-cli-project", "-p", prompt])

    def test_child_environment_preserves_parent_and_other_interop_entries(self):
        parent = {"WSLENV": "SAFE_PATH/p:AGY_CLI_DISABLE_AUTO_UPDATE/u:OTHER/w",
                  "AGY_CLI_DISABLE_AUTO_UPDATE": "false", "SYNTHETIC_SETTING": "keep"}
        with patch.dict(os.environ, parent, clear=True):
            child = child_environment()
            self.assertEqual(dict(os.environ), parent)
        self.assertEqual(child["AGY_CLI_DISABLE_AUTO_UPDATE"], "true")
        self.assertEqual(child["WSLENV"], "SAFE_PATH/p:OTHER/w:AGY_CLI_DISABLE_AUTO_UPDATE/w")
        self.assertEqual(child["SYNTHETIC_SETTING"], "keep")

    def test_version_uses_same_selector_and_child_update_environment(self):
        fake = FakeWorkspace()
        self.addCleanup(fake.close)
        output = subprocess.CompletedProcess([], 0, "1.4.8\n", "")
        with patch("agy_delegate.version.subprocess.run", return_value=output) as child:
            self.assertEqual(verified_version(fake.request()), "1.4.8")
        args, options = child.call_args
        self.assertEqual(args[0], [str(fake.executable.resolve()), "--project",
                                   "default-cli-project", "--version"])
        self.assertEqual(options["env"]["AGY_CLI_DISABLE_AUTO_UPDATE"], "true")
        self.assertIn("AGY_CLI_DISABLE_AUTO_UPDATE/w", options["env"]["WSLENV"].split(":"))
