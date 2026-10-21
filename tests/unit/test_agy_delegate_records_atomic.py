"""実ディスク上の旧記録・private mode・失敗時の一時ファイル除去。"""

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agy_delegate.records import _private_write


class AtomicRecordWriteTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.record = self.root / "record.json"
        self.record.write_text('{"old": true}')
        self.record.chmod(0o644)

    def assert_old_record_preserved(self):
        self.assertEqual(self.record.read_text(), '{"old": true}')
        self.assertEqual(self.record.stat().st_mode & 0o777, 0o644)
        self.assertEqual(list(self.root.iterdir()), [self.record])

    def test_fsync_or_replace_failure_preserves_old_record_and_removes_temporary(self):
        for operation in ("fsync", "replace"):
            with self.subTest(operation=operation):
                with patch(f"agy_delegate.atomic_record_write.os.{operation}",
                           side_effect=OSError("synthetic failure")):
                    with self.assertRaises(OSError):
                        _private_write(self.record, '{"new": true}')
                self.assert_old_record_preserved()

    def test_partial_write_failure_preserves_old_record_and_removes_temporary(self):
        real_fdopen = os.fdopen

        def interrupted_stream(descriptor, *args, **kwargs):
            stream = real_fdopen(descriptor, *args, **kwargs)
            real_write = stream.write

            def interrupted_write(encoded):
                real_write(encoded[:3])
                stream.flush()
                raise OSError("synthetic partial write")

            stream.write = interrupted_write
            return stream

        with patch("agy_delegate.atomic_record_write.os.fdopen", side_effect=interrupted_stream):
            with self.assertRaises(OSError):
                _private_write(self.record, '{"new": true}')
        self.assert_old_record_preserved()

    def test_success_syncs_complete_private_file_before_replacement(self):
        real_replace = os.replace
        real_fsync = os.fsync
        events = []

        def sync(descriptor):
            events.append("fsync")
            return real_fsync(descriptor)

        def replace(source, destination):
            self.assertEqual(events, ["fsync"])
            self.assertEqual(source.read_text(), '{"new": true}')
            self.assertEqual(source.stat().st_mode & 0o777, 0o600)
            self.assert_old_record_content()
            return real_replace(source, destination)

        with patch("agy_delegate.atomic_record_write.os.fsync", side_effect=sync), \
                patch("agy_delegate.atomic_record_write.os.replace", side_effect=replace):
            _private_write(self.record, '{"new": true}')
        self.assertEqual(self.record.read_text(), '{"new": true}')
        self.assertEqual(self.record.stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.root.iterdir()), [self.record])

    def assert_old_record_content(self):
        self.assertEqual(self.record.read_text(), '{"old": true}')

    def test_destination_symlink_is_rejected_without_changing_target(self):
        link = self.root / "linked.json"
        link.symlink_to(self.record)
        with self.assertRaises(OSError):
            _private_write(link, "replacement")
        self.assertTrue(link.is_symlink())
        self.assert_old_record_content()
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_parent_directory_is_synced_after_record_replacement(self):
        real_fsync = os.fsync
        synced_modes = []

        def sync(descriptor):
            synced_modes.append(os.fstat(descriptor).st_mode)
            return real_fsync(descriptor)

        with patch("agy_delegate.atomic_record_write.os.fsync", side_effect=sync):
            _private_write(self.record, "new")
        self.assertEqual([stat.S_IFMT(mode) for mode in synced_modes], [stat.S_IFREG, stat.S_IFDIR])
