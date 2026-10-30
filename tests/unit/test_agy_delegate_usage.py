"""検証済み5整数usageだけを結果と記録へ保存する。"""

import json
import unittest

from agy_delegate.output_contract import TOKENS, validated_usage
from agy_delegate.results import normalize
from tests.unit.agy_delegate_fixtures import FakeWorkspace, run_synthetic, synthetic_success


class UsageTests(unittest.TestCase):
    def test_valid_usage_is_copied_and_saved_without_raw_output(self):
        fake = FakeWorkspace()
        self.addCleanup(fake.close)
        output = synthetic_success()
        output["usage"] = dict.fromkeys(TOKENS, 4)
        result = run_synthetic(fake.request(output))
        self.assertEqual(result.usage, output["usage"])
        path = fake.workspace / "tmp/agy" / result.run_id / "result.json"
        self.assertEqual(json.loads(path.read_text())["usage"], output["usage"])
        copied = validated_usage(output["usage"])
        output["usage"]["total_tokens"] = 9
        self.assertEqual(copied["total_tokens"], 4)

    def test_missing_unknown_bool_negative_and_noninteger_are_not_retained(self):
        valid = dict.fromkeys(TOKENS, 0)
        variants = [None, {}, valid | {"private-marker": 0}]
        variants += [valid | {"input_tokens": value} for value in [False, -1, 1.5, "secret", None]]
        for value in variants:
            with self.subTest(value=value):
                result = normalize("run", json.dumps(synthetic_success() | {"usage": value}), "", 0)
                self.assertIsNone(result.usage)
                self.assertIn("field_invalid:usage", result.reasons)

    def test_error_terminal_can_retain_valid_usage_without_becoming_success(self):
        result = normalize("run", json.dumps(synthetic_success() | {"status": "ERROR"}), "", 1)
        self.assertEqual(result.usage, dict.fromkeys(TOKENS, 0))
        self.assertEqual(result.classification, "failed")
