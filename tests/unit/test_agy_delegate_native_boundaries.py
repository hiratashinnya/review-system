"""論理template/native file-onlyの差と、入力projectionの境界。"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agy_delegate.native_paths import digest_value, native_executable_path, native_workspace_path
from agy_delegate.native_paths import os_binding, text_sha256, wsl_user_binding
from agy_delegate.native_policy import expected_file_only_rules
from agy_delegate.permission_rules import expected_path_rules
from agy_delegate.permissions import expected_rules


class NativeBoundaryTests(unittest.TestCase):
    def test_file_only_is_stricter_than_logical_listing_template(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"WSL_DISTRO_NAME": "Synthetic"}):
            root = Path(directory)
            native = native_workspace_path(root)
            actual = expected_file_only_rules(root)
            logical_native = expected_path_rules(native)
            self.assertEqual(actual["allow"], logical_native["allow"][:2])
            self.assertEqual(actual["deny"], logical_native["deny"] + ["command(regex:.*)"])
            self.assertEqual(len(expected_rules(root)["allow"]), 3)
            self.assertEqual(len(actual["allow"]), 2)
            self.assertNotEqual(expected_rules(root), actual)

    def test_projection_is_not_os_cwd_and_rejects_unknown_distribution(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"WSL_DISTRO_NAME": "Synthetic"}):
            self.assertEqual(native_workspace_path(Path(directory)), "//wsl.localhost/Synthetic" + directory)
        with patch.dict("os.environ", {"WSL_DISTRO_NAME": "../untrusted"}), self.assertRaises(ValueError):
            native_workspace_path(Path("/tmp"))
        with self.assertRaises(ValueError):
            native_executable_path(Path("relative"))
        self.assertEqual(native_executable_path(Path("/mnt/c/Users/synthetic/agy.exe")),
                         "C:\\Users\\synthetic\\agy.exe")

    def test_hashes_are_stable_but_identity_and_os_inputs_are_bound(self):
        self.assertEqual(digest_value({"a": 1, "b": 2}), digest_value({"b": 2, "a": 1}))
        self.assertNotEqual(text_sha256("a"), digest_value("a"))
        before = wsl_user_binding("a" * 64)
        with patch.dict("os.environ", {"HOME": "/untrusted", "XDG_STATE_HOME": "/untrusted"}):
            self.assertEqual(wsl_user_binding("a" * 64), before)
        self.assertNotEqual(wsl_user_binding("b" * 64), before)
        self.assertNotEqual(os_binding("a" * 64), os_binding("b" * 64))

    def test_unknown_native_rule_path_is_not_quoted_into_permission_command(self):
        for value in ("/tmp/'injection", "/tmp/$(command)", "/tmp/x\nnext", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                expected_path_rules(value)
