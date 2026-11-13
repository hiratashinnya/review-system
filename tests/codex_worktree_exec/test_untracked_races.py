"""Race fixtures: quarantine must not silently remove replaced owner content."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from codex_worktree_exec.untracked_recovery import candidates, main as recover
from tests.unit.codex_worktree_exec_support import make_repository


class UntrackedRecoveryRaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)
        _, self.root = make_repository(self.parent)
        self.external = self.parent / "quarantine"
        self.external.mkdir()

    def invoke(self):
        return recover(["--worktree", str(self.root), "--apply",
                        "--quarantine-parent", str(self.external)])

    def test_regular_file_replaced_immediately_before_rename_is_restored(self):
        file = self.root / "tmp/replaced.out"
        file.parent.mkdir()
        file.write_text("original")
        rename = os.rename

        def intervene(source, dest, **kwargs):
            if source == file.name:
                file.write_text("new owner content")
            return rename(source, dest, **kwargs)

        with patch("codex_worktree_exec.safe_quarantine.os.rename", side_effect=intervene):
            with self.assertRaisesRegex(ValueError, "changed during move"):
                self.invoke()
        self.assertEqual(file.read_text(), "new owner content")

    def test_symlink_substitution_does_not_move_target_or_leave_redirect(self):
        file = self.root / "tmp/replaced.out"
        file.parent.mkdir()
        file.write_text("original")
        target = self.external / "protected"
        target.write_text("protected data")
        rename = os.rename

        def intervene(source, dest, **kwargs):
            if source == file.name:
                file.unlink()
                file.symlink_to(target)
            return rename(source, dest, **kwargs)

        with patch("codex_worktree_exec.safe_quarantine.os.rename", side_effect=intervene):
            with self.assertRaisesRegex(ValueError, "changed during move"):
                self.invoke()
        self.assertTrue(file.is_symlink())
        self.assertEqual(target.read_text(), "protected data")

    def test_parent_directory_substitution_is_detected_and_rolled_back(self):
        directory = self.root / "tmp/generated"
        directory.mkdir(parents=True)
        file = directory / "event.out"
        file.write_text("original")
        alternative = self.root / "tmp/moved-parent"
        foreign = self.external / "foreign"
        foreign.mkdir()
        (foreign / file.name).write_text("foreign data")
        rename = os.rename

        def intervene(source, dest, **kwargs):
            if source == file.name:
                directory.rename(alternative)
                directory.symlink_to(foreign, target_is_directory=True)
            return rename(source, dest, **kwargs)

        with patch("codex_worktree_exec.safe_quarantine.os.rename", side_effect=intervene):
            with self.assertRaisesRegex(ValueError, "changed during move"):
                self.invoke()
        self.assertEqual((alternative / file.name).read_text(), "original")
        self.assertEqual((foreign / file.name).read_text(), "foreign data")

    def test_replaced_after_listing_is_not_quarantined(self):
        file = self.root / "tmp/replaced.out"
        file.parent.mkdir()
        file.write_text("old")
        original = candidates

        def replace_after_listing(root):
            entries = original(root)
            file.write_text("new owner content, different size")
            return entries

        with patch("codex_worktree_exec.untracked_recovery.candidates",
                   side_effect=replace_after_listing):
            with self.assertRaisesRegex(ValueError, "changed since listing"):
                self.invoke()
        self.assertEqual(file.read_text(), "new owner content, different size")
