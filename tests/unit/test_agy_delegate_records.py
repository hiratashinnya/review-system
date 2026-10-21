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
        sync_fault_hits = 0

        def fail_success_commit_sync(directory):
            nonlocal sync_fault_hits
            _sync_parent_directory(directory)
            if (directory == self.record.parent
                    and json.loads(self.record.read_text())["classification"] == "success_candidate"):
                sync_fault_hits += 1
                raise OSError("synthetic success commit sync failure")

        with patch("agy_delegate.atomic_record_write._sync_parent_directory", fail_success_commit_sync):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(sync_fault_hits, 1)
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

    def test_success_commit_sync_failure_does_not_attempt_compensating_writes_and_stays_fail_closed(self):
        """第2故障点は本番経路に存在せず、到達しないことを検証する。"""
        from pathlib import Path
        from agy_delegate.atomic_record_write import _sync_parent_directory
        real_open = os.open
        real_unlink = Path.unlink
        marker = self.record.with_suffix(".pending")
        sync_fault_hits = 0
        second_creation_fault_hits = 0
        marker_unlink_hits = 0

        def fail_success_sync(directory):
            nonlocal sync_fault_hits
            _sync_parent_directory(directory)
            if (directory == self.record.parent
                    and json.loads(self.record.read_text())["classification"] == "success_candidate"):
                sync_fault_hits += 1
                raise OSError("synthetic success commit sync failure")

        def fail_later_creation(path, flags, *args, **kwargs):
            nonlocal second_creation_fault_hits
            if sync_fault_hits and flags & os.O_EXCL:
                second_creation_fault_hits += 1
                raise OSError("synthetic temporary creation failure")
            return real_open(path, flags, *args, **kwargs)

        def track_marker_unlink(path, *args, **kwargs):
            nonlocal marker_unlink_hits
            if path == marker:
                marker_unlink_hits += 1
            return real_unlink(path, *args, **kwargs)

        with patch("agy_delegate.atomic_record_write._sync_parent_directory", fail_success_sync), \
                patch("agy_delegate.atomic_record_write.os.open", fail_later_creation), \
                patch("agy_delegate.atomic_record_write.Path.unlink", track_marker_unlink):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(sync_fault_hits, 1)
        self.assertEqual(second_creation_fault_hits, 0)
        self.assertEqual(marker_unlink_hits, 0)
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

    def test_production_success_commit_sync_and_temporary_cleanup_failures_stay_fail_closed(self):
        """本番の確定同期失敗から finally の一時ファイル削除失敗へ連続して到達する。"""
        from pathlib import Path
        from agy_delegate.atomic_record_write import _sync_parent_directory
        real_unlink = Path.unlink
        marker = self.record.with_suffix(".pending")
        sync_fault_hits = 0
        cleanup_fault_hits = 0
        marker_unlink_hits = 0

        def fail_success_sync(directory):
            nonlocal sync_fault_hits
            _sync_parent_directory(directory)
            if (directory == self.record.parent
                    and json.loads(self.record.read_text())["classification"] == "success_candidate"):
                sync_fault_hits += 1
                raise OSError("synthetic success commit sync failure")

        def fail_temporary_cleanup(path, *args, **kwargs):
            nonlocal cleanup_fault_hits, marker_unlink_hits
            if path == marker:
                marker_unlink_hits += 1
            if (sync_fault_hits and path.parent == self.record.parent
                    and path.name.startswith(self.record.name + ".") and path.suffix == ".tmp"):
                cleanup_fault_hits += 1
                raise OSError("synthetic temporary cleanup failure")
            return real_unlink(path, *args, **kwargs)

        with patch("agy_delegate.atomic_record_write._sync_parent_directory", fail_success_sync), \
                patch("agy_delegate.atomic_record_write.Path.unlink", fail_temporary_cleanup):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(sync_fault_hits, 1)
        self.assertEqual(cleanup_fault_hits, 1)
        self.assertEqual(marker_unlink_hits, 0)
        self.assertNotEqual(failed.exit_code, 0)
        self.assertEqual(failed.classification, "failed")
        self.assertIn("execution_io_error", failed.reasons)
        self.assertEqual(json.loads(self.record.read_text())["classification"], "success_candidate")
        self.assertTrue(marker.is_file())
        self.assertEqual(list(self.record.parent.glob("*.tmp")), [])
        launches = (self.fake.workspace / "launch-count.txt").read_text()
        self.assertNotEqual(launches, self.launches)
        blocked = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(blocked.exit_code, 0)
        self.assertIn("conversation_record_unconfirmed", blocked.reasons)
        self.assertEqual((self.fake.workspace / "launch-count.txt").read_text(), launches)

    def test_production_marker_commit_sync_failure_does_not_attempt_summary_write(self):
        """印の置換後に同期が失敗すると成功記録の書込みと印削除には到達しない。"""
        from agy_delegate import records
        from agy_delegate.atomic_record_write import _sync_parent_directory
        marker = self.record.with_suffix(".pending")
        real_write = records._private_write
        real_remove_marker = records.remove_marker
        marker_sync_fault_hits = 0
        summary_write_fault_hits = 0
        marker_unlink_hits = 0

        def fail_marker_commit_sync(directory):
            nonlocal marker_sync_fault_hits
            _sync_parent_directory(directory)
            if directory == self.record.parent and marker.is_file():
                marker_sync_fault_hits += 1
                raise OSError("synthetic marker commit sync failure")

        def fail_summary_write(path, encoded):
            nonlocal summary_write_fault_hits
            if path == self.record:
                summary_write_fault_hits += 1
                raise OSError("synthetic summary write failure")
            return real_write(path, encoded)

        def track_marker_removal(path):
            nonlocal marker_unlink_hits
            marker_unlink_hits += 1
            return real_remove_marker(path)

        with patch("agy_delegate.atomic_record_write._sync_parent_directory", fail_marker_commit_sync), \
                patch("agy_delegate.records._private_write", fail_summary_write), \
                patch("agy_delegate.records.remove_marker", track_marker_removal):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(marker_sync_fault_hits, 1)
        self.assertEqual(summary_write_fault_hits, 0)
        self.assertEqual(marker_unlink_hits, 0)
        self.assertNotEqual(failed.exit_code, 0)
        self.assertEqual(failed.classification, "failed")
        self.assertIn("execution_io_error", failed.reasons)
        marked = json.loads(self.record.read_text())
        self.assertEqual(marked["classification"], "failed")
        self.assertIn("conversation_continuation_in_progress", marked["reasons"])
        self.assertTrue(marker.is_file())
        self.assertEqual(list(self.record.parent.glob("*.tmp")), [])
        launches = (self.fake.workspace / "launch-count.txt").read_text()
        self.assertNotEqual(launches, self.launches)
        blocked = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(blocked.exit_code, 0)
        self.assertIn("conversation_record_unconfirmed", blocked.reasons)
        self.assertEqual((self.fake.workspace / "launch-count.txt").read_text(), launches)

    def test_harness_pending_marker_creation_failure_keeps_failed_record(self):
        """保存直前に印のパスをディレクトリにする補助ハーネスで作成失敗を再現する。"""
        from agy_delegate import records
        marker = self.record.with_suffix(".pending")
        real_write = records._private_write
        marker_write_hits = 0
        summary_write_hits = 0

        def track_writes(path, encoded):
            nonlocal marker_write_hits, summary_write_hits
            if path == marker:
                marker_write_hits += 1
            elif path == self.record:
                summary_write_hits += 1
            return real_write(path, encoded)

        def save_with_marker_directory(root, request, result):
            marker.mkdir()
            return records.save_record(root, request, result)

        with patch("agy_delegate.runner.save_record", save_with_marker_directory), \
                patch("agy_delegate.records._private_write", track_writes):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(marker_write_hits, 1)
        self.assertEqual(summary_write_hits, 0)
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
        from pathlib import Path
        from agy_delegate.atomic_record_write import _sync_parent_directory
        marker = self.record.with_suffix(".pending")
        real_unlink = Path.unlink
        removal_sync_failures = []
        removal_sync_fault_hits = 0
        marker_unlink_hits = 0

        def track_marker_unlink(path, *args, **kwargs):
            nonlocal marker_unlink_hits
            if path == marker:
                marker_unlink_hits += 1
            return real_unlink(path, *args, **kwargs)

        def fail_sync_after_marker_removal(directory):
            nonlocal removal_sync_fault_hits
            if (directory == self.record.parent and not os.path.lexists(marker)
                    and json.loads(self.record.read_text())["classification"] == "success_candidate"):
                removal_sync_fault_hits += 1
                removal_sync_failures.append(directory)
                raise OSError("synthetic marker removal sync failure")
            return _sync_parent_directory(directory)

        with patch("agy_delegate.atomic_record_write._sync_parent_directory", fail_sync_after_marker_removal), \
                patch("agy_delegate.atomic_record_write.Path.unlink", track_marker_unlink):
            succeeded = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(marker_unlink_hits, 1)
        self.assertEqual(removal_sync_fault_hits, 1)
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
        from agy_delegate.atomic_record_write import _sync_parent_directory
        marker = self.record.with_suffix(".pending")
        real_unlink = Path.unlink
        unlink_fault_hits = 0
        result_unlink_hits = 0
        result_markers = []
        removal_sync_fault_hits = 0

        def fail_marker_unlink(path, *args, **kwargs):
            nonlocal unlink_fault_hits, result_unlink_hits
            if path.name == "result.pending":
                result_unlink_hits += 1
                result_markers.append(path)
            if path == marker:
                self.assertEqual(result_unlink_hits, 1)
                self.assertFalse(os.path.lexists(result_markers[0]))
                unlink_fault_hits += 1
                raise OSError("synthetic marker unlink failure")
            return real_unlink(path, *args, **kwargs)

        def fail_sync_after_unlink(directory):
            nonlocal removal_sync_fault_hits
            if directory == self.record.parent and unlink_fault_hits:
                removal_sync_fault_hits += 1
                raise OSError("synthetic marker removal sync failure")
            return _sync_parent_directory(directory)

        with patch("agy_delegate.atomic_record_write.Path.unlink", fail_marker_unlink), \
                patch("agy_delegate.atomic_record_write._sync_parent_directory", fail_sync_after_unlink):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(unlink_fault_hits, 1)
        self.assertEqual(result_unlink_hits, 1)
        self.assertEqual(removal_sync_fault_hits, 0)
        self.assertNotEqual(failed.exit_code, 0)
        self.assertEqual(failed.classification, "failed")
        self.assertIn("execution_io_error", failed.reasons)
        self.assertTrue(marker.is_file())
        self.assertEqual(json.loads(self.record.read_text())["classification"], "success_candidate")
        result_path = self.record.parent / failed.run_id / "result.json"
        self.assertEqual(json.loads(result_path.read_text())["classification"], "success_candidate")
        self.assertFalse(os.path.lexists(result_path.with_suffix(".pending")))
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

    def assert_unconfirmed_result_blocks_continuation(self, failed):
        self.assertNotEqual(failed.exit_code, 0)
        self.assertEqual(failed.classification, "failed")
        self.assertIn("execution_io_error", failed.reasons)
        new_results = [path for path in self.record.parent.glob("*/result.json")
                       if path.parent.name != self.data["run_id"]]
        self.assertEqual(len(new_results), 1)
        self.assertEqual(new_results[0].parent.name, failed.run_id)
        data = json.loads(new_results[0].read_text())
        self.assertEqual(data["classification"], "failed")
        self.assertIn("result_unconfirmed", data["reasons"])
        self.assertNotIn("result_unconfirmed", failed.reasons)
        self.assertTrue(self.record.with_suffix(".pending").is_file())
        self.assert_pending_blocks_continuation()

    def assert_pending_blocks_continuation(self):
        launches = (self.fake.workspace / "launch-count.txt").read_text()
        self.assertNotEqual(launches, self.launches)
        blocked = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertNotEqual(blocked.exit_code, 0)
        self.assertIn("conversation_record_unconfirmed", blocked.reasons)
        self.assertEqual((self.fake.workspace / "launch-count.txt").read_text(), launches)

    def assert_saved_success_is_unconfirmed(self, failed):
        self.assertNotEqual(failed.exit_code, 0)
        self.assertEqual(failed.classification, "failed")
        self.assertIn("execution_io_error", failed.reasons)
        result_path = self.record.parent / failed.run_id / "result.json"
        self.assertEqual(json.loads(result_path.read_text())["classification"], "success_candidate")
        self.assertEqual(json.loads(self.record.read_text())["classification"], "success_candidate")
        self.assertTrue(result_path.with_suffix(".pending").is_file())
        self.assertTrue(self.record.with_suffix(".pending").is_file())
        self.assert_pending_blocks_continuation()

    @unittest.skipIf(os.geteuid() == 0, "root は権限検査を回避するため")
    def test_lock_release_permission_failure_keeps_records_unconfirmed(self):
        """全書込み後に親を 0o500 にし、保存を妨げず実 rmdir を失敗させる。"""
        from agy_delegate.records import save_record
        lock = self.record.parent / "workspace.lock"
        self.addCleanup(lambda: lock.rmdir() if lock.exists() else None)
        self.addCleanup(self.record.parent.chmod, 0o700)
        hits = 0

        def restrict_parent_after_save(root, request, result):
            nonlocal hits
            markers = save_record(root, request, result)
            hits += 1
            self.record.parent.chmod(0o500)
            return markers

        with patch("agy_delegate.runner.save_record", restrict_parent_after_save), \
                patch("agy_delegate.runner.confirm_record") as confirm:
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.record.parent.chmod(0o700)
        self.assertEqual(hits, 1)
        self.assertEqual(confirm.call_count, 0)
        self.assertTrue(lock.is_dir())
        lock.rmdir()
        self.assert_saved_success_is_unconfirmed(failed)

    def test_lock_release_injected_failure_keeps_records_unconfirmed(self):
        from pathlib import Path
        real_rmdir = Path.rmdir
        lock = self.record.parent / "workspace.lock"
        self.addCleanup(lambda: lock.rmdir() if lock.exists() else None)
        hits = 0

        def fail_lock_rmdir(path):
            nonlocal hits
            if path == lock:
                hits += 1
                raise OSError("synthetic lock release failure")
            return real_rmdir(path)

        with patch("agy_delegate.records.Path.rmdir", fail_lock_rmdir), \
                patch("agy_delegate.runner.confirm_record") as confirm:
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(hits, 1)
        self.assertEqual(confirm.call_count, 0)
        self.assertTrue(lock.is_dir())
        lock.rmdir()
        self.assert_saved_success_is_unconfirmed(failed)

    def test_record_confirmation_follows_successful_lock_release(self):
        from pathlib import Path
        from agy_delegate import records
        real_rmdir, real_remove = Path.rmdir, records.remove_marker
        real_confirm = records.confirm_record
        lock = self.record.parent / "workspace.lock"
        events = []

        def track_lock_release(path):
            real_rmdir(path)
            if path == lock:
                events.append("rmdir")

        def track_confirmation(markers):
            events.append("confirm_record")
            self.assertFalse(lock.exists())
            return real_confirm(markers)

        def track_removal(marker):
            events.append(marker)
            return real_remove(marker)

        with patch("agy_delegate.records.Path.rmdir", track_lock_release), \
                patch("agy_delegate.runner.confirm_record", track_confirmation), \
                patch("agy_delegate.records.remove_marker", track_removal):
            result = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(result.exit_code, 0)
        result_marker = self.record.parent / result.run_id / "result.pending"
        conversation_marker = self.record.with_suffix(".pending")
        self.assertEqual(events, ["rmdir", "confirm_record", result_marker, conversation_marker])
        self.assertFalse(os.path.lexists(result_marker))
        self.assertFalse(os.path.lexists(conversation_marker))

    def test_confirmation_failure_keeps_remaining_markers(self):
        from agy_delegate import records
        markers = [self.record.parent / name for name in
                   ("result.pending", "conversation-first.pending", "conversation-second.pending")]
        for marker in markers:
            marker.touch(mode=0o600)
        real_remove = records.remove_marker
        removals = []
        fault_hits = 0

        def fail_second_removal(marker):
            nonlocal fault_hits
            removals.append(marker)
            if marker == markers[1]:
                fault_hits += 1
                raise OSError("synthetic confirmation failure")
            return real_remove(marker)

        with patch("agy_delegate.records.remove_marker", fail_second_removal):
            with self.assertRaisesRegex(OSError, "synthetic confirmation failure"):
                records.confirm_record(markers)
        self.assertEqual(fault_hits, 1)
        self.assertEqual(removals, markers[:2])
        self.assertFalse(os.path.lexists(markers[0]))
        self.assertTrue(markers[1].is_file())
        self.assertTrue(markers[2].is_file())

    @unittest.skipIf(os.geteuid() == 0, "root は権限検査を回避するため")
    def test_result_stays_unconfirmed_when_conversation_parent_sync_fails(self):
        from agy_delegate.records import save_record
        self.addCleanup(self.record.parent.chmod, 0o700)

        def save_without_parent_read_permission(root, request, result):
            self.record.parent.chmod(0o300)
            return save_record(root, request, result)

        with patch("agy_delegate.runner.save_record", save_without_parent_read_permission):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.record.parent.chmod(0o700)
        self.assert_unconfirmed_result_blocks_continuation(failed)

    def test_result_stays_unconfirmed_when_conversation_write_fails(self):
        from agy_delegate import records
        real_write = records._private_write
        hits = 0

        def fail_conversation_write(path, encoded):
            nonlocal hits
            if path == self.record:
                hits += 1
                raise OSError("synthetic conversation write failure")
            return real_write(path, encoded)

        with patch("agy_delegate.records._private_write", fail_conversation_write):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(hits, 1)
        self.assert_unconfirmed_result_blocks_continuation(failed)

    def test_result_stays_unconfirmed_when_final_result_write_fails(self):
        from agy_delegate import records
        real_write = records._private_write
        hits = 0

        def fail_final_result_write(path, encoded):
            nonlocal hits
            if path.name == "result.json" and json.loads(encoded)["classification"] == "success_candidate":
                hits += 1
                raise OSError("synthetic final result write failure")
            return real_write(path, encoded)

        with patch("agy_delegate.records._private_write", fail_final_result_write):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(hits, 1)
        self.assert_unconfirmed_result_blocks_continuation(failed)

    def test_success_confirms_result_before_removing_marker(self):
        from agy_delegate import records
        real_write = records._private_write
        writes = []

        def track_write(path, encoded):
            writes.append((path, encoded))
            if path.name == "result.json" and json.loads(encoded)["classification"] == "success_candidate":
                self.assertTrue(path.with_suffix(".pending").is_file())
                self.assertTrue(self.record.with_suffix(".pending").is_file())
                self.assertEqual(json.loads(self.record.read_text())["classification"], "success_candidate")
            return real_write(path, encoded)

        with patch("agy_delegate.records._private_write", track_write):
            succeeded = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(succeeded.exit_code, 0)
        result_path = self.record.parent / succeeded.run_id / "result.json"
        self.assertEqual([path for path, _ in writes],
                         [result_path, self.record.with_suffix(".pending"), self.record,
                          result_path.with_suffix(".pending"), result_path])
        final = json.loads(result_path.read_text())
        self.assertEqual(final["classification"], "success_candidate")
        self.assertNotIn("result_unconfirmed", final["reasons"])
        self.assertEqual(json.loads(writes[0][1]),
                         final | {"classification": "failed", "reasons": final["reasons"] + ["result_unconfirmed"]})
        self.assertFalse(os.path.lexists(self.record.with_suffix(".pending")))
        self.assertFalse(os.path.lexists(result_path.with_suffix(".pending")))
        self.assertEqual(json.loads(self.record.read_text())["classification"], "success_candidate")

    def test_final_result_sync_failure_keeps_marker_and_blocks_continuation(self):
        from pathlib import Path
        from agy_delegate.atomic_record_write import _sync_parent_directory
        real_unlink = Path.unlink
        hits = 0
        unlink_hits = 0

        def track_marker_unlink(path, *args, **kwargs):
            nonlocal unlink_hits
            if path.suffix == ".pending":
                unlink_hits += 1
            return real_unlink(path, *args, **kwargs)

        def fail_final_result_sync(directory):
            nonlocal hits
            _sync_parent_directory(directory)
            if directory.parent == self.record.parent:
                data = json.loads((directory / "result.json").read_text())
                if data["classification"] == "success_candidate":
                    hits += 1
                    raise OSError("synthetic final result sync failure")

        with patch("agy_delegate.atomic_record_write._sync_parent_directory", fail_final_result_sync), \
                patch("agy_delegate.atomic_record_write.Path.unlink", track_marker_unlink):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(hits, 1)
        self.assertEqual(unlink_hits, 0)
        self.assertNotEqual(failed.exit_code, 0)
        self.assertEqual(failed.classification, "failed")
        self.assertIn("execution_io_error", failed.reasons)
        data = json.loads((self.record.parent / failed.run_id / "result.json").read_text())
        self.assertEqual(data["classification"], "success_candidate")
        self.assertTrue((self.record.parent / failed.run_id / "result.pending").is_file())
        self.assertTrue(self.record.with_suffix(".pending").is_file())
        self.assert_pending_blocks_continuation()

    def test_all_conversations_are_written_before_any_marker_is_removed(self):
        from agy_delegate import records
        from agy_delegate.types import Result
        result = Result("multiple-records", classification="success_candidate", conversation_id="other")
        result_path = self.record.parent / result.run_id / "result.json"
        result_path.parent.mkdir(mode=0o700)
        summaries = [self.record, self.record.parent / "conversation-other.json"]
        real_remove = records.remove_marker
        removals = []

        def check_before_removal(marker):
            self.assertEqual(json.loads(result_path.read_text())["classification"], "success_candidate")
            for path in summaries:
                self.assertEqual(json.loads(path.read_text())["classification"], "success_candidate")
                if not removals:
                    self.assertTrue(path.with_suffix(".pending").is_file())
            removals.append(marker)
            return real_remove(marker)

        with patch("agy_delegate.records.remove_marker", check_before_removal):
            markers = records.save_record(self.record.parent, self.fake.request(conversation="conversation-1"), result)
            self.assertEqual(removals, [])
            self.assertIsInstance(markers, list)
            self.assertEqual(markers[0], result_path.with_suffix(".pending"))
            self.assertCountEqual(markers, [result_path.with_suffix(".pending")]
                                  + [path.with_suffix(".pending") for path in summaries])
            self.assertTrue(all(path.is_file() for path in markers))
            records.confirm_record(markers)
        self.assertEqual(removals[0], result_path.with_suffix(".pending"))
        self.assertCountEqual(removals, [result_path.with_suffix(".pending")]
                              + [path.with_suffix(".pending") for path in summaries])
        self.assertTrue(all(not os.path.lexists(path) for path in removals))

    def test_result_marker_unlink_failure_keeps_both_markers_and_blocks_continuation(self):
        from pathlib import Path
        real_unlink = Path.unlink
        result_unlink_hits = 0
        conversation_unlink_hits = 0

        def fail_result_marker_unlink(path, *args, **kwargs):
            nonlocal result_unlink_hits, conversation_unlink_hits
            if path.name == "result.pending":
                result_unlink_hits += 1
                self.assertTrue(self.record.with_suffix(".pending").is_file())
                raise OSError("synthetic result marker unlink failure")
            if path == self.record.with_suffix(".pending"):
                conversation_unlink_hits += 1
            return real_unlink(path, *args, **kwargs)

        with patch("agy_delegate.atomic_record_write.Path.unlink", fail_result_marker_unlink):
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(result_unlink_hits, 1)
        self.assertEqual(conversation_unlink_hits, 0)
        self.assertNotEqual(failed.exit_code, 0)
        self.assertEqual(failed.classification, "failed")
        self.assertIn("execution_io_error", failed.reasons)
        result_path = self.record.parent / failed.run_id / "result.json"
        self.assertEqual(json.loads(result_path.read_text())["classification"], "success_candidate")
        self.assertTrue(result_path.with_suffix(".pending").is_file())
        self.assertTrue(self.record.with_suffix(".pending").is_file())
        self.assert_pending_blocks_continuation()

    def test_result_marker_creation_failure_keeps_result_unconfirmed(self):
        from agy_delegate import records
        real_write = records._private_write
        hits = 0
        final_write_hits = 0

        def obstruct_result_marker(path, encoded):
            nonlocal hits, final_write_hits
            if path.name == "result.pending":
                hits += 1
                path.mkdir()
            if path.name == "result.json" and json.loads(encoded)["classification"] == "success_candidate":
                final_write_hits += 1
            return real_write(path, encoded)

        with patch("agy_delegate.records._private_write", obstruct_result_marker), \
                patch("agy_delegate.records.remove_marker", wraps=records.remove_marker) as remove:
            failed = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertEqual(hits, 1)
        self.assertEqual(final_write_hits, 0)
        remove.assert_not_called()
        self.assertTrue((self.record.parent / failed.run_id / "result.pending").is_dir())
        self.assert_unconfirmed_result_blocks_continuation(failed)

    @unittest.skipIf(os.geteuid() == 0, "root は権限検査を回避するため")
    def test_result_parent_permission_failure_keeps_markers_and_blocks_continuation(self):
        from agy_delegate import records
        real_write = records._private_write
        for stage in ("result_marker", "final_result"):
            with self.subTest(stage=stage):
                hits = 0

                def restrict_result_parent(path, encoded):
                    nonlocal hits
                    if ((stage == "result_marker" and path.name == "result.pending")
                            or (stage == "final_result" and path.name == "result.json"
                                and json.loads(encoded)["classification"] == "success_candidate")):
                        hits += 1
                        self.addCleanup(path.parent.chmod, 0o700)
                        path.parent.chmod(0o300)
                    return real_write(path, encoded)

                with patch("agy_delegate.records._private_write", restrict_result_parent), \
                        patch("agy_delegate.records.remove_marker", wraps=records.remove_marker) as remove:
                    failed = self.execute(self.fake.request(conversation="conversation-1"))
                run_dir = self.record.parent / failed.run_id
                run_dir.chmod(0o700)
                self.assertEqual(hits, 1)
                remove.assert_not_called()
                self.assertNotEqual(failed.exit_code, 0)
                self.assertEqual(failed.classification, "failed")
                self.assertIn("execution_io_error", failed.reasons)
                data = json.loads((run_dir / "result.json").read_text())
                self.assertEqual(data["classification"], "failed" if stage == "result_marker"
                                 else "success_candidate")
                self.assertEqual("result_unconfirmed" in data["reasons"], stage == "result_marker")
                self.assertTrue((run_dir / "result.pending").is_file())
                self.assertTrue(self.record.with_suffix(".pending").is_file())
                self.assertEqual(list(run_dir.glob("*.tmp")), [])
                self.assert_pending_blocks_continuation()
                self.record.with_suffix(".pending").unlink()

    def test_non_success_result_is_written_once_without_markers(self):
        from agy_delegate import records
        from agy_delegate.types import Result
        for classification in ("failed", "denied", "preflight_failed"):
            with self.subTest(classification=classification):
                result = Result(classification, classification=classification, conversation_id="conversation-1")
                result_path = self.record.parent / result.run_id / "result.json"
                result_path.parent.mkdir(mode=0o700)
                with patch("agy_delegate.records._private_write", wraps=records._private_write) as write, \
                        patch("agy_delegate.records.remove_marker") as remove:
                    markers = records.save_record(self.record.parent, self.fake.request(), result)
                    self.assertEqual(markers, [])
                    records.confirm_record(markers)
                self.assertEqual([call.args[0] for call in write.call_args_list], [result_path, self.record])
                remove.assert_not_called()
                self.assertFalse(os.path.lexists(self.record.with_suffix(".pending")))
                self.assertFalse(os.path.lexists(result_path.with_suffix(".pending")))
                self.assertEqual(json.loads(result_path.read_text())["classification"], classification)
                self.assertNotIn("result_unconfirmed", json.loads(result_path.read_text())["reasons"])


if __name__ == "__main__":
    unittest.main()
