"""Regression: prune never deletes competing data, even after quarantine move."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from codex_worktree_exec.cache_prune import main as prune
from tests.unit.codex_worktree_exec_support import make_repository


class CachePruneRaceTests(unittest.TestCase):
    def test_changed_regular_cache_is_restored(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            _, root = make_repository(directory)
            cache = root / "pkg/__pycache__/changed.cpython-313.pyc"
            cache.parent.mkdir(parents=True)
            cache.write_bytes(b"initial cache content")
            original = os.rename
            replacement = b"new contents from competing writer"

            def change_before_move(source, destination, **kwargs):
                if source == cache.name:
                    cache.write_bytes(replacement)
                return original(source, destination, **kwargs)

            with patch("codex_worktree_exec.safe_quarantine.os.rename",
                       side_effect=change_before_move):
                with self.assertRaisesRegex(ValueError, "changed during move"):
                    prune(["--worktree", str(root), "--apply",
                           "--quarantine-parent", temporary])
            self.assertEqual(cache.read_bytes(), replacement)

    def test_replacement_after_move_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            _, root = make_repository(directory)
            cache = root / "pkg/__pycache__/changed.cpython-313.pyc"
            cache.parent.mkdir(parents=True)
            cache.write_bytes(b"original")
            original = os.rename
            replacement = b"new owner data"

            def change_after_move(source, destination, **kwargs):
                result = original(source, destination, **kwargs)
                if source == cache.name:
                    Path(destination).write_bytes(replacement)
                return result

            with patch("codex_worktree_exec.safe_quarantine.os.rename",
                       side_effect=change_after_move):
                with self.assertRaisesRegex(ValueError, "changed during move"):
                    prune(["--worktree", str(root), "--apply",
                           "--quarantine-parent", temporary])
            self.assertEqual(cache.read_bytes(), replacement)
