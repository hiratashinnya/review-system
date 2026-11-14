"""Issue #655: disposable git fixtures and source recovery policy."""
import py_compile
import subprocess
import tempfile
import unittest
from pathlib import Path
from codex_worktree_exec.cache_prune import candidates, main as prune
from codex_worktree_exec.source_snapshot import verify_untracked_sources
from tests.unit.codex_worktree_exec_support import git, make_repository

class UntrackedRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        _, self.root = make_repository(Path(temporary.name))

    def place(self, name, content="x"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_exact_locks_and_symlink_rejection(self):
        from codex_worktree_exec.untracked_policy import LOCKS
        for name in LOCKS:
            self.place(name)
        verify_untracked_sources(self.root)
        extra = self.place(".claude/scheduled_tasks.lock2")
        with self.assertRaisesRegex(ValueError, "unapproved_source"):
            verify_untracked_sources(self.root)
        extra.unlink()
        lock = self.root / ".claude/scheduled_tasks.lock"
        lock.unlink()
        lock.symlink_to(self.root / "tmp")
        with self.assertRaisesRegex(ValueError, "unsafe_path"):
            verify_untracked_sources(self.root)

    def test_orphan_cache_and_head_source_guard(self):
        source = self.place("deleted.py", "value = 1\n")
        cache = Path(py_compile.compile(str(source), doraise=True))
        source.unlink()
        self.assertTrue(cache.exists())
        verify_untracked_sources(self.root)
        probe = subprocess.run(["python3", "-c",
            "import importlib.util,sys;sys.path.insert(0,sys.argv[1]);"
            "assert importlib.util.find_spec('deleted') is None", str(self.root)],
            capture_output=True, text=True)
        self.assertEqual(probe.returncode, 0, probe.stderr)
        self.place("deleted.py", "value = 1\n")
        git(self.root, "add", "deleted.py")
        git(self.root, "commit", "-qm", "source")
        source.unlink()
        with self.assertRaisesRegex(ValueError, "unsafe_cache"):
            verify_untracked_sources(self.root)

    def test_aggregates_foreign_stale_and_source(self):
        source = self.place("ordinary.py", "value = 1\n")
        git(self.root, "add", "ordinary.py")
        git(self.root, "commit", "-qm", "source")
        valid = Path(py_compile.compile(str(source), doraise=True))
        valid.with_name("ordinary.unsupported.pyc").write_bytes(valid.read_bytes())
        source.write_text("value = 2\n")
        git(self.root, "add", "ordinary.py")
        git(self.root, "commit", "-qm", "new source")
        self.place("unapproved.py")
        with self.assertRaises(ValueError) as caught:
            verify_untracked_sources(self.root)
        for term in ("foreign_cache count=1", "stale_cache count=1",
                     "unapproved_source count=1", "cache_prune --apply"):
            self.assertIn(term, str(caught.exception))

    def test_ignore_does_not_approve_source_or_tmp_python(self):
        self.place(".gitignore", "*.py\n")
        source = self.place("unapproved.py")
        with self.assertRaisesRegex(ValueError, "unapproved_source"):
            verify_untracked_sources(self.root)
        source.unlink()
        self.place("tmp/injected.py")
        with self.assertRaisesRegex(ValueError, "unapproved_tmp"):
            verify_untracked_sources(self.root)

    def test_prune_requires_apply_and_keeps_other_files(self):
        cache = self.place("pkg/__pycache__/orphan.cpython-313.pyc")
        other = self.place("pkg/other.pyc")
        legacy = self.place("pkg/__pycache__/orphan.cpython-313.pyo")
        self.assertEqual(candidates(self.root), [cache])
        self.assertEqual(prune(["--worktree", str(self.root)]), 0)
        quarantine = self.root.parents[3] / "cache-preserved"
        quarantine.mkdir(exist_ok=True)
        self.assertTrue(cache.exists())  # Dry-run keeps its input.
        self.assertEqual(prune(["--worktree", str(self.root), "--apply",
                                "--quarantine-parent", str(quarantine)]), 0)
        self.assertFalse(cache.exists())
        saved = list(quarantine.glob("review-system-cache-*/pkg/__pycache__/*.pyc"))
        self.assertEqual([p.read_bytes() for p in saved], [b"x"])
        self.assertTrue(other.exists())
        self.assertTrue(legacy.exists())
        with self.assertRaisesRegex(ValueError, "unsupported_cache_format count=1") as caught:
            verify_untracked_sources(self.root)
        self.assertIn("untracked_recovery --apply (quarantine .pyo)", str(caught.exception))
