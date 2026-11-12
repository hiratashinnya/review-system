"""Regression: cache replaced between inspection and deletion is preserved."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from codex_worktree_exec.cache_prune import main as prune
from tests.unit.codex_worktree_exec_support import make_repository


class CachePruneRaceTests(unittest.TestCase):
    def test_cache_changed_during_prune_is_restored(self):
        with tempfile.TemporaryDirectory() as temp:
            _, root = make_repository(Path(temp))
            cache = root / "pkg/__pycache__/changed.cpython-313.pyc"
            cache.parent.mkdir(parents=True)
            cache.write_bytes(b"initial cache content")
            replacement = b"new contents from competing writer"
            original_replace = os.replace

            def competing_write(source, destination):
                if Path(source) == cache:
                    cache.write_bytes(replacement)
                return original_replace(source, destination)

            with patch("codex_worktree_exec.cache_prune.os.replace",
                       side_effect=competing_write):
                with self.assertRaisesRegex(ValueError, "changed during prune"):
                    prune(["--worktree", str(root), "--apply"])
            self.assertEqual(cache.read_bytes(), replacement)
            self.assertFalse(list(cache.parent.glob(".cache-prune-*")))
