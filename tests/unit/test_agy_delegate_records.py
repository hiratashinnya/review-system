"""不正な会話記録は traceback を出さず、子プロセス起動前に停止する。"""

import json
import os
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

    def test_pending_success_blocks_continuation(self):
        self.record.with_suffix(".pending").touch()
        self.assert_blocked(json.dumps(self.data), "conversation_record_unconfirmed")

    def test_legacy_pending_success_is_invalid(self):
        self.assert_blocked(json.dumps(self.data | {"classification": "success_pending_sync"}),
                            "conversation_record_missing_or_invalid")

    def test_pending_directory_and_symlinks_block_before_reading_record(self):
        marker = self.record.with_suffix(".pending")
        for kind in ("directory", "symlink", "broken_symlink"):
            with self.subTest(kind=kind):
                if kind == "directory":
                    marker.mkdir()
                else:
                    marker.symlink_to(self.record if kind == "symlink" else self.record.parent / "missing")
                try:
                    self.assert_blocked("invalid JSON", "conversation_record_unconfirmed")
                finally:
                    if kind == "directory":
                        marker.rmdir()
                    else:
                        marker.unlink()

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

    @unittest.skipIf(os.geteuid() == 0, "root は権限検査を回避するため")
    def test_parent_sync_failure_blocks_continuation_and_keeps_failed_marker(self):
        self.addCleanup(self.record.parent.chmod, 0o700)
        self.record.parent.chmod(0o300)
        result = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual((self.fake.workspace / "launch-count.txt").read_text(), self.launches)
        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(result.classification, "failed")
        self.assertIn("execution_io_error", result.reasons)
        self.record.parent.chmod(0o700)
        marked = json.loads(self.record.read_text())
        self.assertEqual(marked["classification"], "failed")
        self.assertIn("conversation_continuation_in_progress", marked["reasons"])
        self.assertEqual(list(self.record.parent.glob("*.tmp")), [])

    @unittest.skipIf(os.geteuid() == 0, "root は権限検査を回避するため")
    def test_save_parent_sync_failure_does_not_leave_continuable_success(self):
        from agy_delegate.records import save_record
        self.addCleanup(self.record.parent.chmod, 0o700)

        def save_without_parent_read_permission(root, request, result):
            self.record.parent.chmod(0o300)
            return save_record(root, request, result)

        with patch("agy_delegate.runner.save_record", save_without_parent_read_permission):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(failed.exit_code, 0)
        self.assertEqual(failed.classification, "failed")
        self.assertIn("execution_io_error", failed.reasons)
        self.record.parent.chmod(0o700)
        self.assertNotEqual(json.loads(self.record.read_text())["classification"], "success_candidate")
        self.assertEqual(list(self.record.parent.glob("*.tmp")), [])
        launches = (self.fake.workspace / "launch-count.txt").read_text()
        self.assertNotEqual(launches, self.launches)
        blocked = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(blocked.exit_code, 0)
        self.assertIn("conversation_record_unconfirmed", blocked.reasons)
        self.assertEqual((self.fake.workspace / "launch-count.txt").read_text(), launches)

    def test_success_commit_sync_failure_keeps_marker_and_blocks_continuation(self):
        from agy_delegate.atomic_record_write import _sync_parent_directory

        def fail_success_commit_sync(directory):
            _sync_parent_directory(directory)
            if (directory == self.record.parent
                    and json.loads(self.record.read_text())["classification"] == "success_candidate"):
                raise OSError("synthetic success commit sync failure")

        with patch("agy_delegate.atomic_record_write._sync_parent_directory", fail_success_commit_sync):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(failed.exit_code, 0)
        self.assertEqual(failed.classification, "failed")
        self.assertIn("execution_io_error", failed.reasons)
        self.assertEqual(json.loads(self.record.read_text())["classification"], "success_candidate")
        self.assertTrue(self.record.with_suffix(".pending").is_file())
        self.assertEqual(list(self.record.parent.glob("*.tmp")), [])
        launches = (self.fake.workspace / "launch-count.txt").read_text()
        self.assertNotEqual(launches, self.launches)
        blocked = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(blocked.exit_code, 0)
        self.assertIn("conversation_record_unconfirmed", blocked.reasons)
        self.assertEqual((self.fake.workspace / "launch-count.txt").read_text(), launches)

    def test_success_sync_and_later_temporary_creation_fail_closed(self):
        from agy_delegate.atomic_record_write import _sync_parent_directory
        real_open = os.open
        sync_failed = False

        def fail_success_sync(directory):
            nonlocal sync_failed
            _sync_parent_directory(directory)
            if (directory == self.record.parent
                    and json.loads(self.record.read_text())["classification"] == "success_candidate"):
                sync_failed = True
                raise OSError("synthetic success commit sync failure")

        def fail_later_creation(path, flags, *args, **kwargs):
            if sync_failed and flags & os.O_EXCL:
                raise OSError("synthetic temporary creation failure")
            return real_open(path, flags, *args, **kwargs)

        with patch("agy_delegate.atomic_record_write._sync_parent_directory", fail_success_sync), \
                patch("agy_delegate.atomic_record_write.os.open", fail_later_creation):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertTrue(sync_failed)
        self.assertNotEqual(failed.exit_code, 0)
        self.assertEqual(failed.classification, "failed")
        self.assertIn("execution_io_error", failed.reasons)
        self.assertEqual(json.loads(self.record.read_text())["classification"], "success_candidate")
        launches = (self.fake.workspace / "launch-count.txt").read_text()
        self.assertNotEqual(launches, self.launches)
        blocked = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertIn("conversation_record_unconfirmed", blocked.reasons)
        self.assertNotEqual(blocked.exit_code, 0)
        self.assertEqual((self.fake.workspace / "launch-count.txt").read_text(), launches)
        self.assertTrue(self.record.with_suffix(".pending").is_file())
        self.assertEqual(list(self.record.parent.glob("*.tmp")), [])

    def test_pending_marker_creation_failure_keeps_failed_record(self):
        from agy_delegate.records import save_record
        marker = self.record.with_suffix(".pending")

        def save_with_marker_directory(root, request, result):
            marker.mkdir()
            return save_record(root, request, result)

        with patch("agy_delegate.runner.save_record", save_with_marker_directory):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(failed.exit_code, 0)
        self.assertEqual(failed.classification, "failed")
        self.assertIn("execution_io_error", failed.reasons)
        self.assertTrue(marker.is_dir())
        marked = json.loads(self.record.read_text())
        self.assertEqual(marked["classification"], "failed")
        self.assertIn("conversation_continuation_in_progress", marked["reasons"])
        launches = (self.fake.workspace / "launch-count.txt").read_text()
        self.assertNotEqual(launches, self.launches)
        blocked = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(blocked.exit_code, 0)
        self.assertIn("conversation_record_unconfirmed", blocked.reasons)
        self.assertEqual((self.fake.workspace / "launch-count.txt").read_text(), launches)
        self.assertEqual(list(self.record.parent.glob("*.tmp")), [])

    def test_marker_removal_sync_failure_keeps_success_continuable(self):
        from agy_delegate.atomic_record_write import _sync_parent_directory
        marker = self.record.with_suffix(".pending")
        removal_sync_failures = []

        def fail_sync_after_marker_removal(directory):
            if (directory == self.record.parent and not os.path.lexists(marker)
                    and json.loads(self.record.read_text())["classification"] == "success_candidate"):
                removal_sync_failures.append(directory)
                raise OSError("synthetic marker removal sync failure")
            return _sync_parent_directory(directory)

        with patch("agy_delegate.atomic_record_write._sync_parent_directory", fail_sync_after_marker_removal):
            succeeded = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(removal_sync_failures, [self.record.parent])
        self.assertEqual(succeeded.exit_code, 0)
        self.assertEqual(succeeded.classification, "success_candidate")
        self.assertFalse(os.path.lexists(marker))
        self.assertEqual(json.loads(self.record.read_text())["classification"], "success_candidate")
        launches = (self.fake.workspace / "launch-count.txt").read_text()
        self.assertNotEqual(launches, self.launches)
        continued = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(continued.exit_code, 0)
        self.assertNotEqual((self.fake.workspace / "launch-count.txt").read_text(), launches)

    def test_marker_unlink_failure_keeps_success_unconfirmed(self):
        from pathlib import Path
        marker = self.record.with_suffix(".pending")
        real_unlink = Path.unlink

        def fail_marker_unlink(path, *args, **kwargs):
            if path == marker:
                raise OSError("synthetic marker unlink failure")
            return real_unlink(path, *args, **kwargs)

        with patch("agy_delegate.atomic_record_write.Path.unlink", fail_marker_unlink):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(failed.exit_code, 0)
        self.assertEqual(failed.classification, "failed")
        self.assertIn("execution_io_error", failed.reasons)
        self.assertTrue(marker.is_file())
        self.assertEqual(json.loads(self.record.read_text())["classification"], "success_candidate")
        launches = (self.fake.workspace / "launch-count.txt").read_text()
        self.assertNotEqual(launches, self.launches)
        blocked = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(blocked.exit_code, 0)
        self.assertIn("conversation_record_unconfirmed", blocked.reasons)
        self.assertEqual((self.fake.workspace / "launch-count.txt").read_text(), launches)
        self.assertEqual(list(self.record.parent.glob("*.tmp")), [])

    def test_marking_replaces_record_atomically_without_leftovers(self):
        mark_continuation_started(self.record.parent, self.fake.request(conversation="conversation-1"))
        self.assertEqual(sorted(path.name for path in self.record.parent.glob("*.tmp")), [])
        self.assertEqual(self.record.stat().st_mode & 0o777, 0o600)
        with patch("agy_delegate.conversation_continuation.os.replace", side_effect=OSError("synthetic")):
            with self.assertRaises(OSError):
                mark_continuation_started(self.record.parent, self.fake.request(conversation="conversation-1"))
        self.assertEqual(sorted(path.name for path in self.record.parent.glob("*.tmp")), [])

    def test_save_failure_at_real_file_write_boundary_keeps_old_success_unacceptable(self):
        """記録保存関数は差し替えず、会話記録への実書込だけを OSError にして実ディスクの状態を確かめる。"""
        from agy_delegate import records
        real_write = records._private_write

        def fail_for_conversation_summary(path, encoded):
            if path.name.startswith("conversation-"):
                raise OSError("synthetic disk failure")
            return real_write(path, encoded)

        with patch("agy_delegate.records._private_write", fail_for_conversation_summary):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(failed.exit_code, 0)
        run_results = list((self.record.parent).glob("*/result.json"))
        self.assertEqual(len(run_results), 2)
        on_disk = json.loads(self.record.read_text())
        self.assertEqual(on_disk["classification"], "failed")
        self.assertIn("conversation_continuation_in_progress", on_disk["reasons"])
        self.assertEqual(sorted(path.name for path in self.record.parent.glob("*.tmp")), [])
        launches = (self.fake.workspace / "launch-count.txt").read_text()
        blocked = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertIn("conversation_previous_failure", blocked.reasons)
        self.assertEqual((self.fake.workspace / "launch-count.txt").read_text(), launches)

    def test_marking_forces_private_mode_and_keeps_record_when_write_fails(self):
        self.record.chmod(0o644)
        request = self.fake.request(conversation="conversation-1")
        before = self.record.read_text()
        with patch("agy_delegate.conversation_continuation.os.fsync", side_effect=OSError("synthetic")):
            with self.assertRaises(OSError):
                mark_continuation_started(self.record.parent, request)
        self.assertEqual(self.record.read_text(), before)
        self.assertEqual(self.record.stat().st_mode & 0o777, 0o644)
        self.assertEqual(sorted(path.name for path in self.record.parent.glob("*.tmp")), [])
        mark_continuation_started(self.record.parent, request)
        self.assertEqual(self.record.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(self.record.read_text())["classification"], "failed")

    def test_successful_continuation_after_marking_is_recorded_as_success_again(self):
        self.assertEqual(self.execute(self.fake.request(conversation="conversation-1")).exit_code, 0)
        self.assertFalse(os.path.lexists(self.record.with_suffix(".pending")))
        self.assertEqual(json.loads(self.record.read_text())["classification"], "success_candidate")


if __name__ == "__main__":
    unittest.main()
