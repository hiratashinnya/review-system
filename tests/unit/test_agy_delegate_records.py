"""不正な会話記録は traceback を出さず、子プロセス起動前に停止する。"""

import json
import unittest
from unittest.mock import patch

from agy_delegate.conversation_continuation import mark_continuation_started
from agy_delegate.runner import run
from tests.unit.agy_delegate_fixtures import FakeWorkspace, run_synthetic, synthetic_runtime


class ConversationRecordTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)
        self.assertEqual(self.execute(self.fake.request()).exit_code, 0)
        self.record = self.fake.workspace / "tmp/agy/conversation-conversation-1.json"
        self.data = json.loads(self.record.read_text())
        self.launches = (self.fake.workspace / "launch-count.txt").read_text()

    def execute(self, request):
        return run_synthetic(request)

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
                      {"agy_exit_code": False}, {"truncated": 0}, {"agy_exit_code": "0"},
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

    def test_conversation_summary_has_no_response_or_error(self):
        self.assertNotIn("response", self.data)
        self.assertNotIn("error", self.data)

    def test_duplicate_record_key_cannot_hide_denial(self):
        payload = json.dumps(self.data).replace('"denied_actions": []',
                                                '"denied_actions": ["deny"], "denied_actions": []')
        self.assert_blocked(payload, "conversation_record_missing_or_invalid")

    def test_old_success_is_not_reaccepted_after_result_save_failure(self):
        launches = lambda: (self.fake.workspace / "launch-count.txt").read_text()
        with patch("agy_delegate.runner.save_record", side_effect=OSError("synthetic save failure")):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(failed.exit_code, 0)
        self.assertNotEqual(launches(), self.launches)
        marked = json.loads(self.record.read_text())
        self.assertEqual(marked["classification"], "failed")
        self.assertIn("conversation_continuation_in_progress", marked["reasons"])
        after_failure = launches()
        blocked = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertIn("conversation_previous_failure", blocked.reasons)
        self.assertNotEqual(blocked.exit_code, 0)
        self.assertEqual(launches(), after_failure)

    def test_continuation_is_not_launched_when_marking_old_record_fails(self):
        before = self.record.read_text()
        with patch("agy_delegate.runner.mark_continuation_started",
                   side_effect=OSError("synthetic mark failure")):
            result = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("execution_io_error", result.reasons)
        self.assertEqual((self.fake.workspace / "launch-count.txt").read_text(), self.launches)
        self.assertEqual(self.record.read_text(), before)

    def test_marking_replaces_record_atomically_without_leftovers(self):
        mark_continuation_started(self.record.parent, self.fake.request(conversation="conversation-1"))
        self.assertEqual(sorted(path.name for path in self.record.parent.glob("*.tmp")), [])
        self.assertEqual(self.record.stat().st_mode & 0o777, 0o600)
        with patch("agy_delegate.conversation_continuation.os.replace", side_effect=OSError("synthetic")):
            with self.assertRaises(OSError):
                mark_continuation_started(self.record.parent, self.fake.request(conversation="conversation-1"))
        self.assertEqual(sorted(path.name for path in self.record.parent.glob("*.tmp")), [])

    def test_successful_continuation_after_marking_is_recorded_as_success_again(self):
        self.assertEqual(self.execute(self.fake.request(conversation="conversation-1")).exit_code, 0)
        self.assertEqual(json.loads(self.record.read_text())["classification"], "success_candidate")


if __name__ == "__main__":
    unittest.main()
