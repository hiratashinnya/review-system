"""申告 scope 原本の fsync 順序、失敗時の保存、壊れた原本の拒否。"""

import os
import stat
from unittest.mock import patch

from karte import scope_atomic, scope_directory, scope_records
from karte.model import KarteFormatError
from tests.unit.karte_support import RootedCase


class ScopeAtomicDurabilityTests(RootedCase):
    def setUp(self):
        super().setUp()
        self.path = scope_records.ledger_path(375, self.root, create=True)
        self.original = '{"round": 1, "id": "F-375-01", "scope": "in"}\n'
        self.path.write_text(self.original, encoding="utf-8")

    def test_replacement_syncs_file_then_replaces_then_syncs_directory(self):
        events = []
        real_fsync, real_replace = os.fsync, os.replace
        replacement = self.original.replace('"in"', '"out"')

        def sync(fd):
            info = os.fstat(fd)
            events.append(stat.S_IFMT(info.st_mode))
            if stat.S_ISREG(info.st_mode):
                self.assertEqual(len(replacement.encode("utf-8")), info.st_size)
            return real_fsync(fd)

        def replace(*args, **kwargs):
            events.append("replace")
            return real_replace(*args, **kwargs)

        with scope_directory.open_scope_directory(self.path) as directory:
            with patch("karte.scope_atomic.os.fsync", side_effect=sync), \
                    patch("karte.scope_atomic.os.replace", side_effect=replace):
                scope_atomic.write_scope_text(self.path, directory, replacement, expected=self.original)
        self.assertEqual([stat.S_IFREG, "replace", stat.S_IFDIR], events)
        self.assertEqual(replacement, self.path.read_text(encoding="utf-8"))

    def test_file_sync_failure_preserves_original_and_removes_temporary_file(self):
        failure = OSError("file fsync failed")
        with scope_directory.open_scope_directory(self.path) as directory:
            with patch("karte.scope_atomic.os.fsync", side_effect=failure), \
                    patch("karte.scope_atomic.os.replace") as replace:
                with self.assertRaises(OSError) as caught:
                    scope_atomic.write_scope_text(self.path, directory, "new", expected=self.original)
        self.assertIs(failure, caught.exception)
        replace.assert_not_called()
        self.assertEqual(self.original, self.path.read_text(encoding="utf-8"))
        self.assertEqual([self.path], list(self.path.parent.iterdir()))

    def test_backup_syncs_file_then_links_then_syncs_directory(self):
        events = []
        real_fsync, real_link = os.fsync, os.link

        def sync(fd):
            events.append(stat.S_IFMT(os.fstat(fd).st_mode))
            return real_fsync(fd)

        def link(*args, **kwargs):
            events.append("link")
            return real_link(*args, **kwargs)

        with scope_directory.open_scope_directory(self.path) as directory:
            with patch("karte.scope_atomic.os.fsync", side_effect=sync), \
                    patch("karte.scope_atomic.os.link", side_effect=link):
                scope_atomic.write_scope_backup(self.path, directory, self.original)
        self.assertEqual([stat.S_IFREG, "link", stat.S_IFDIR], events)
        self.assertEqual(self.original, self.path.with_suffix(".jsonl.bak").read_text(encoding="utf-8"))
        self.assertEqual(self.original, self.path.read_text(encoding="utf-8"))

    def test_directory_sync_failures_propagate(self):
        for write, options in ((scope_atomic.write_scope_text, {"expected": self.original}),
                               (scope_atomic.write_scope_backup, {})):
            with self.subTest(write=write.__name__):
                failure = OSError("directory fsync failed")
                with scope_directory.open_scope_directory(self.path) as directory:
                    with patch("karte.scope_atomic.os.fsync", side_effect=[None, failure]):
                        with self.assertRaises(OSError) as caught:
                            write(self.path, directory, self.original, **options)
                self.assertIs(failure, caught.exception)

    def test_zero_length_original_keeps_protection_enabled_and_has_no_records(self):
        self.path.write_text("", encoding="utf-8")
        self.assertTrue(scope_records.exists(375, self.root))
        self.assertEqual([], scope_records.read_records(375, self.root))

    def test_truncated_json_is_refused_without_changing_original(self):
        truncated = self.original + '{"round": 2, "id": "F-375-02"'
        self.path.write_text(truncated, encoding="utf-8")
        with self.assertRaises(KarteFormatError):
            scope_records.read_records(375, self.root)
        with self.assertRaises(KarteFormatError):
            scope_records.append_lines(375, self.root, [self.original.strip()])
        self.assertEqual(truncated, self.path.read_text(encoding="utf-8"))
        self.assertEqual([self.path], list(self.path.parent.iterdir()))
