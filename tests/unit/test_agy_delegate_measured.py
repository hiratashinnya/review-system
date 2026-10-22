"""実測 JSON の判別と、そこから確定した型境界を固定する。"""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from agy_delegate.results import normalize
from agy_delegate.runner import run
from tests.unit.agy_delegate_fixtures import FakeWorkspace, synthetic_success

ROOT = Path(__file__).resolve().parents[1] / "fixtures/agy_delegate/1.3.3"


class MeasuredContractTests(unittest.TestCase):
    def test_measured_stdout_stderr_exit_are_classified(self):
        cases = {
            "success": ("success_candidate", set()),
            "denied": ("denied", {"no_output", "d0_denied_actions"}),
            "print_timeout": ("failed", {"print_timeout"}),
            "quota_error": ("failed", {"agy_error_present", "stderr_error",
                                        "nonzero_exit", "status_not_success"}),
        }
        for name, (classification, reasons) in cases.items():
            with self.subTest(name=name):
                sample = json.loads((ROOT / f"{name}.json").read_text())
                result = normalize(name, sample["stdout"], sample["stderr"], sample["exit_code"])
                data = json.loads(sample["stdout"])
                self.assertEqual(result.classification, classification)
                self.assertEqual(set(result.reasons), reasons)
                self.assertEqual(result.response, data["response"])
                self.assertEqual(result.conversation_id, data["conversation_id"])
                self.assertEqual(result.error, data.get("error"))
                self.assertEqual(result.truncated, name == "print_timeout")
                self.assertEqual(result.exit_code, 0 if name == "success" else 1)
                self.assertEqual(result.classification != "success_candidate", result.exit_code != 0)

    def test_optional_denials_and_error_do_not_make_measured_success_incomplete(self):
        sample = json.loads((ROOT / "success.json").read_text())
        data = json.loads(sample["stdout"])
        self.assertNotIn("denied_actions", data)
        self.assertNotIn("error", data)
        self.assertEqual(normalize("r", sample["stdout"], "", 0).exit_code, 0)
        data["error"] = "diagnostic"
        self.assertIn("agy_error_present", normalize("r", json.dumps(data), "", 0).reasons)

    def test_missing_required_fields_and_unknown_nested_keys_fail(self):
        data = synthetic_success()
        for key in ("status", "conversation_id", "response", "duration_seconds", "num_turns", "usage"):
            changed = data.copy()
            del changed[key]
            with self.subTest(key=key):
                self.assertIn(f"field_invalid:{key}", normalize("r", json.dumps(changed), "", 0).reasons)
        for changed in (data | {"usage": data["usage"] | {"extra": 0}},
                        data | {"denied_actions": [{"action": "command"}]},
                        data | {"denied_actions": ["deny"]}, data | {"error": None}):
            self.assertNotEqual(normalize("r", json.dumps(changed), "", 0).exit_code, 0)

    def test_numeric_contract_excludes_bool_negative_fraction_and_overflow(self):
        data = synthetic_success()
        for value in (True, -1, "1", None, float("inf"), float("nan")):
            for key in ("duration_seconds", "num_turns"):
                self.assertNotEqual(normalize("r", json.dumps(data | {key: value}), "", 0).exit_code, 0)
        for value in (True, -1, 0.5, "0", None):
            usage = data["usage"] | {"input_tokens": value}
            self.assertIn("field_invalid:usage", normalize("r", json.dumps(data | {"usage": usage}), "", 0).reasons)
        overflow = json.dumps(data).replace('"duration_seconds": 1.0', '"duration_seconds": 1e400')
        self.assertNotEqual(normalize("r", overflow, "", 0).exit_code, 0)
        self.assertNotEqual(normalize("r", json.dumps(data | {"num_turns": 1.5}), "", 0).exit_code, 0)

    def test_usage_arithmetic_is_not_inferred_and_usage_command_is_only_synthetic(self):
        data = synthetic_success()
        data["usage"]["cache_read_tokens"] = 9481
        self.assertEqual(normalize("r", json.dumps(data), "", 0).exit_code, 0)
        data.update(conversation_id="", num_turns=0, command="usage")
        result = normalize("r", json.dumps(data), "", 0)
        self.assertIn("conversation_id_invalid", result.reasons)
        self.assertIn("unknown_output_fields", result.reasons)

    def test_output_gate_removed_but_unmeasured_runtime_always_prevents_launch(self):
        fake = FakeWorkspace()
        self.addCleanup(fake.close)
        with patch("agy_delegate.runner.execute") as child:
            result = run(fake.request())
        self.assertIn("settings_permission_merge_unverified", result.reasons)
        self.assertIn("launch_environment_unverified", result.reasons)
        self.assertNotIn("output_contract_unverified", result.reasons)
        child.assert_not_called()
