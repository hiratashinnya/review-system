"""停止理由名の接尾辞を変えても受入ガードが赤であることを検査。"""

import unittest
from unittest.mock import patch

from agy_delegate.settings_layer_types import SettingsResolution
from tests.unit import test_agy_delegate_merge_guard as guard_module


class MergeGuardContractTests(unittest.TestCase):
    def test_stop_reason_without_unverified_suffix_remains_red(self):
        guard = guard_module.RuntimeMergeGuardTests("test_production_runtime_has_no_unverified_stop_reasons")
        with patch("tests.unit.test_agy_delegate_merge_guard.verify_runtime",
                   return_value=["settings_layer_inventory_incomplete"]):
            with self.assertRaisesRegex(AssertionError, "Issue #628"):
                guard.test_production_runtime_has_no_unverified_stop_reasons()

    def test_runtime_without_fixed_reasons_still_fails_inventory(self):
        from pathlib import Path
        from agy_delegate.settings_layers import inspect_layer_resolution
        reasons = inspect_layer_resolution(SettingsResolution(), Path("/synthetic"))
        self.assertIn("settings_layer_inventory_incomplete", reasons)
        guard = guard_module.RuntimeMergeGuardTests("test_production_runtime_has_no_unverified_stop_reasons")
        with patch("tests.unit.test_agy_delegate_merge_guard.verify_runtime", return_value=reasons):
            with self.assertRaisesRegex(AssertionError, "Issue #628"):
                guard.test_production_runtime_has_no_unverified_stop_reasons()
