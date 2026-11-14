"""Rollback cannot overwrite a new owner's file between check and restore."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from codex_worktree_exec.untracked_recovery import main as recover
from tests.unit.codex_worktree_exec_support import make_repository


class QuarantineRollbackRaceTests(unittest.TestCase):
    def test_late_writer_wins_root_path_while_old_data_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            _, root = make_repository(parent)
            file = root / "tmp/event.out"
            file.parent.mkdir(exist_ok=True)
            file.write_text("old")
            real_rename, real_link = os.rename, os.link

            def modify_after_move(source, destination, **kwargs):
                result = real_rename(source, destination, **kwargs)
                if source == file.name:
                    Path(destination).write_text("old but modified")
                return result

            def new_writer_before_rollback(source, dest, **kwargs):
                if dest == file.name:
                    file.write_text("new owner data")
                return real_link(source, dest, **kwargs)

            with patch("codex_worktree_exec.safe_quarantine.os.rename",
                       side_effect=modify_after_move), \
                 patch("codex_worktree_exec.safe_quarantine.os.link",
                       side_effect=new_writer_before_rollback):
                with self.assertRaisesRegex(ValueError, "changed during move"):
                    recover(["--worktree", str(root), "--quarantine-parent", str(parent),
                             "--apply"])
            self.assertEqual(file.read_text(), "new owner data")
            quarantined = list(parent.glob("review-system-quarantine-*/tmp/event.out"))
            self.assertEqual(len(quarantined), 1)
            self.assertEqual(quarantined[0].read_text(), "old but modified")
