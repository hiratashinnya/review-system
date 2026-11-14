"""Issue #655 AC: content-only git pull must reject and recover stale bytecode."""
import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from codex_worktree_exec.source_snapshot import verify_untracked_sources
from tests.unit.codex_worktree_exec_support import GIT_ENV, git

REPO = Path(__file__).resolve().parents[2]


class ContentOnlyPullTests(unittest.TestCase):
    def test_content_only_pull_stale_cache_to_single_recovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bare, producer, consumer = (root / n for n in ("remote.git", "author", "consumer"))
            bare.mkdir()
            git(bare, "init", "--bare", "-q")
            producer.mkdir()
            git(producer, "init", "-q")
            original = producer / "module.py"
            original.write_text("VALUE = 1\n")
            git(producer, "add", ".")
            git(producer, "commit", "-qm", "initial")
            git(producer, "branch", "-M", "main")
            git(producer, "remote", "add", "origin", str(bare))
            git(producer, "push", "-q", "-u", "origin", "main")
            subprocess.run(["git", "clone", "-q", "--branch", "main",
                            str(bare), str(consumer)], check=True, env=GIT_ENV)
            cache = Path(py_compile.compile(str(consumer / "module.py"), doraise=True))
            saved = cache.read_bytes()
            verify_untracked_sources(consumer)
            original.write_text("VALUE = 123456789\n")
            git(producer, "add", "module.py")
            git(producer, "commit", "-qm", "content change without deletion")
            git(producer, "push", "-q", "origin", "main")
            git(consumer, "pull", "--ff-only", "origin", "main")
            self.assertTrue(cache.exists())
            with self.assertRaisesRegex(ValueError, "stale_cache count=1"):
                verify_untracked_sources(consumer)
            output = root / "preserved"
            output.mkdir()
            run = subprocess.run([sys.executable, "-B", "-m",
                                  "codex_worktree_exec.untracked_recovery",
                                  "--worktree", str(consumer), "--quarantine-parent",
                                  str(output), "--apply"], cwd=REPO, capture_output=True,
                                 text=True, check=True)
            self.assertIn("mode=apply", run.stdout)
            verify_untracked_sources(consumer)
            preserved = list(output.glob("review-system-quarantine-*/__pycache__/*.pyc"))
            self.assertEqual(len(preserved), 1)
            self.assertEqual(preserved[0].read_bytes(), saved)
