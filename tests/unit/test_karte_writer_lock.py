"""karte.paths.writer_lock が unsafe な lock ファイルを拒否することの検証（Issue #538 F-538-01）。"""

import os
from pathlib import Path
import tempfile
import unittest

from karte import paths


class KarteWriterLockTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.lock = paths.karte_dir(self.root, create=True) / ".writer.lock"
        self.decoy = self.lock.with_name("issue-1.md")
        self.decoy.write_text("decoy\n", encoding="utf-8")

    def test_regular_single_link_lock_is_created_and_reused(self):
        for _ in range(2):
            with paths.writer_lock(self.root):
                self.assertTrue(self.lock.is_file())
        self.assertFalse(self.lock.is_symlink())
        self.assertEqual(self.lock.stat().st_nlink, 1)

    def test_symlink_lock_is_rejected_without_following_it(self):
        self.lock.symlink_to(self.decoy)
        with self.assertRaises(OSError):
            with paths.writer_lock(self.root):
                self.fail("symlink の lock を受け入れた")
        self.assertEqual(self.decoy.read_text(encoding="utf-8"), "decoy\n")

    def test_dangling_symlink_lock_is_rejected_without_creating_its_target(self):
        target = self.lock.with_name("absent")
        self.lock.symlink_to(target)
        with self.assertRaises(OSError):
            with paths.writer_lock(self.root):
                self.fail("宙吊り symlink の lock を受け入れた")
        self.assertFalse(target.exists())

    def test_hardlinked_lock_is_rejected(self):
        os.link(self.decoy, self.lock)
        with self.assertRaises(paths.KartePathError):
            with paths.writer_lock(self.root):
                self.fail("hardlink の lock を受け入れた")


if __name__ == "__main__":
    unittest.main()
