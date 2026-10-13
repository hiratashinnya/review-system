"""拒否の上書き、非標準 JSON、許可設定の曖昧性を拒否する。"""

import json
import unittest
from dataclasses import replace

from agy_delegate.results import normalize
from agy_delegate.runner import run
from tests.unit.agy_delegate_fixtures import FakeWorkspace, run_synthetic, synthetic_runtime, synthetic_success


class JsonContractTests(unittest.TestCase):
    def test_duplicate_denial_cannot_be_hidden_by_empty_value(self):
        payload = json.dumps(synthetic_success())
        payload = payload.replace('"denied_actions": []',
                                  '"denied_actions": ["denied"], "denied_actions": []')
        result = normalize("run", payload, "", 0)
        self.assertEqual(result.classification, "failed")
        self.assertIn("json_invalid", result.reasons)
        self.assertNotEqual(result.exit_code, 0)

    def test_nested_duplicates_and_nonstandard_numbers_fail(self):
        for value in ('[{"action": "deny", "action": "allow"}]', '[NaN]', '[Infinity]'):
            payload = json.dumps(synthetic_success()).replace('"denied_actions": []',
                                                               '"denied_actions": ' + value)
            with self.subTest(value=value):
                self.assertIn("json_invalid", normalize("run", payload, "", 0).reasons)

    def test_duplicate_permission_layers_or_groups_never_launch(self):
        fake = FakeWorkspace()
        self.addCleanup(fake.close)
        settings = fake.settings.read_text()
        for malformed in (settings[:-1] + ', "permissions": ' + settings[16:-1] + '}',
                          settings.replace('"ask": []', '"ask": ["unsafe"], "ask": []')):
            fake.settings.write_text(malformed)
            result = run_synthetic(fake.request())
            self.assertIn("settings_unreadable_or_invalid", result.reasons)
            self.assertFalse((fake.workspace / "launched.json").exists())

    def test_duplicate_output_from_fake_process_is_failed(self):
        fake = FakeWorkspace()
        self.addCleanup(fake.close)
        output = json.dumps(synthetic_success()).replace('"status": "SUCCESS"',
                                                       '"status": "ERROR", "status": "SUCCESS"')
        request = replace(fake.request(), prompt=json.dumps({"stdout": output}))
        result = run_synthetic(request)
        self.assertIn("json_invalid", result.reasons)
        self.assertNotEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
