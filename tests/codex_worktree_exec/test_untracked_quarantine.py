"""Regression: harness/tool output is preserved outside the checkout."""
import tempfile
import unittest
from pathlib import Path
from codex_worktree_exec.source_snapshot import verify_untracked_sources
from codex_worktree_exec.untracked_recovery import candidates, main as recover
from tests.unit.codex_worktree_exec_support import make_repository


class UntrackedQuarantineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.parent = Path(temp.name)
        _, self.root = make_repository(self.parent)
        self.outside = self.parent / "quarantines"
        self.outside.mkdir()

    def put(self, relative, data="important owner data"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        return path

    def test_harness_coverage_serena_tmp_and_legacy_cache_recovered_in_one_run(self):
        files = [
            "tmp/_adr-notify/" + "a" * 64 + ".root",
            "tmp/pr-diffs/pr-818-" + "b" * 32 + ".diff",
            "tmp/_feedback/FBK-20261113-draft.toml",
            "tmp/manual.py", "tmp/shell.out",
            ".coverage", "htmlcov/index.html", ".serena/.gitignore",
            "pkg/__pycache__/unused.cpython-999.pyo",
        ]
        for index, name in enumerate(files):
            self.put(name, f"preserved content {index}")
        protected = self.put("tests/unapproved_test.py")
        with self.assertRaises(ValueError) as caught:
            verify_untracked_sources(self.root)
        for expected in ("unapproved_tmp count=5", "tool_state count=1",
                         "coverage_output count=2", "unsupported_cache_format count=1"):
            self.assertIn(expected, str(caught.exception))
        args = ["--worktree", str(self.root), "--quarantine-parent", str(self.outside)]
        self.assertEqual(len(candidates(self.root)), len(files))
        self.assertEqual(recover(args), 0)
        self.assertTrue(all((self.root / f).exists() for f in files))
        self.assertEqual(recover(args + ["--apply"]), 0)
        destinations = list(self.outside.iterdir())
        self.assertEqual(len(destinations), 1)
        for index, name in enumerate(files):
            self.assertFalse((self.root / name).exists(), name)
            self.assertEqual((destinations[0] / name).read_text(), f"preserved content {index}")
        self.assertTrue(protected.exists())
        with self.assertRaisesRegex(ValueError, "unapproved_source"):
            verify_untracked_sources(self.root)
        protected.unlink()
        verify_untracked_sources(self.root)

    def test_symlink_not_quarantined(self):
        outside = self.outside / "original"
        outside.write_text("protected")
        link = self.root / "tmp" / "link.out"
        link.parent.mkdir(exist_ok=True)
        link.symlink_to(outside)
        self.assertEqual(candidates(self.root), [])
        self.assertEqual(recover(["--worktree", str(self.root), "--apply",
                                  "--quarantine-parent", str(self.outside)]), 0)
        self.assertTrue(link.is_symlink())
        self.assertEqual(outside.read_text(), "protected")

    def test_in_tree_quarantine_parent_refused(self):
        with self.assertRaisesRegex(ValueError, "outside worktree"):
            recover(["--worktree", str(self.root),
                     "--quarantine-parent", str(self.root / "tmp")])
