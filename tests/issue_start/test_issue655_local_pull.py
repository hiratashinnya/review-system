"""Issue #822: real local git pull with source-delete and source-update residues."""
import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from codex_worktree_exec.source_snapshot import verify_untracked_sources
from tests.unit.codex_worktree_exec_support import GIT_ENV, git

REPO = Path(__file__).resolve().parents[2]


class GitPullRecoveryIntegrationTests(unittest.TestCase):
    def test_pull_delete_orphan_then_pull_update_stale_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bare = root / "remote.git"
            bare.mkdir()
            git(bare, "init", "--bare", "-q")
            producer = root / "producer"
            producer.mkdir()
            git(producer, "init", "-q")
            source = producer / "module.py"
            source.write_text("VALUE = 1\n")
            git(producer, "add", "module.py")
            git(producer, "commit", "-qm", "initial dummy source")
            git(producer, "branch", "-M", "main")
            git(producer, "remote", "add", "origin", str(bare))
            git(producer, "push", "-q", "-u", "origin", "main")
            consumer = root / "consumer"
            subprocess.run(["git", "clone", "-q", "--branch", "main",
                            str(bare), str(consumer)], env=GIT_ENV, check=True)
            cache = Path(py_compile.compile(str(consumer / "module.py"), doraise=True))
            self.assertTrue(cache.exists())
            verify_untracked_sources(consumer)

            source.unlink()
            git(producer, "add", "-u")
            git(producer, "commit", "-qm", "delete source")
            git(producer, "push", "-q", "origin", "main")
            git(consumer, "pull", "--ff-only", "origin", "main")
            self.assertTrue(cache.exists())
            self.assertFalse((consumer / "module.py").exists())
            verify_untracked_sources(consumer)  # Verified inert orphan cache after a real pull

            source.write_text("VALUE = 123456\n")
            git(producer, "add", "module.py")
            git(producer, "commit", "-qm", "restore with different bytes")
            git(producer, "push", "-q", "origin", "main")
            git(consumer, "pull", "--ff-only", "origin", "main")
            with self.assertRaisesRegex(ValueError, "stale_cache"):
                verify_untracked_sources(consumer)
            preserve = root / "preserved"
            preserve.mkdir()
            result = subprocess.run(
                [sys.executable, "-B", "-m", "codex_worktree_exec.untracked_recovery",
                 "--worktree", str(consumer), "--quarantine-parent", str(preserve),
                 "--apply"],
                cwd=REPO, text=True, capture_output=True, check=True)
            self.assertIn("mode=apply", result.stdout)
            verify_untracked_sources(consumer)
            self.assertFalse(cache.exists())
            copies = list(preserve.glob("review-system-quarantine-*/__pycache__/*.pyc"))
            self.assertEqual(len(copies), 1)
            self.assertTrue(copies[0].is_file())
