"""不正な会話記録は traceback を出さず、子プロセス起動前に停止する。"""

import json
import unittest

from agy_delegate.runner import run
from tests.unit.agy_delegate_fixtures import FakeWorkspace, synthetic_runtime


class ConversationRecordTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)
        self.assertEqual(self.execute(self.fake.request()).exit_code, 0)
        self.record = self.fake.workspace / "tmp/agy/conversation-conversation-1.json"
        self.data = json.loads(self.record.read_text())
        self.launches = (self.fake.workspace / "launch-count.txt").read_text()

    def execute(self, request):
        return run(request, runtime_verifier=synthetic_runtime)

    def assert_blocked(self, payload, reason):
        self.record.write_text(payload)
        result = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertIn(reason, result.reasons)
        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual((self.fake.workspace / "launch-count.txt").read_text(), self.launches)

    def test_nonobjects_missing_fields_and_wrong_types_fail_closed(self):
        values = [[], None, {"workspace": str(self.fake.workspace),
                            "classification": "success_candidate"}]
        values.extend(self.data | change for change in ({"reasons": None}, {"denied_actions": {}},
                      {"agy_exit_code": False}, {"completed": 0}, {"artifacts": [False]},
                      {"run_id": "../private"}, {"reasons": [None]}))
        for value in values:
            with self.subTest(value=value):
                self.assert_blocked(json.dumps(value), "conversation_record_missing_or_invalid")

    def test_success_classification_cannot_hide_failure(self):
        for change in ({"status": "ERROR"}, {"agy_exit_code": 1}, {"status": None},
                       {"denied_actions": ["deny"]}, {"reasons": ["failure"]}, {"truncated": True}):
            with self.subTest(change=change):
                self.assert_blocked(json.dumps(self.data | change), "conversation_previous_failure")

    def test_record_identity_must_match_requested_conversation(self):
        self.assert_blocked(json.dumps(self.data | {"conversation_id": "other"}),
                            "conversation_record_identity_mismatch")

    def test_success_candidate_requires_string_response(self):
        self.assert_blocked(json.dumps(self.data | {"response": None}),
                            "conversation_previous_failure")

    def test_duplicate_record_key_cannot_hide_denial(self):
        payload = json.dumps(self.data).replace('"denied_actions": []',
                                                '"denied_actions": ["deny"], "denied_actions": []')
        self.assert_blocked(payload, "conversation_record_missing_or_invalid")


if __name__ == "__main__":
    unittest.main()
