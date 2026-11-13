"""Regression: untracked generated files cannot bypass Git/index/path checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from codex_worktree_exec.source_snapshot import verify_untracked_sources
from codex_worktree_exec.untracked_recovery import candidates, main as recover
from tests.unit.codex_worktree_exec_support import git, make_repository


class UntrackedQuarantineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)
        _, self.root = make_repository(self.parent)
        self.outside = self.parent / "quarantines"
        self.outside.mkdir()

    def put(self, relative, data="important owner data"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        return path

    def args(self):
        return ["--worktree", str(self.root), "--quarantine-parent", str(self.outside)]

    def test_harness_coverage_serena_tmp_and_legacy_cache_recovered_in_one_run(self):
        files = ["tmp/_adr-notify/" + "a" * 64 + ".root",
                 "tmp/pr-diffs/pr-818-" + "b" * 32 + ".diff",
                 "tmp/_feedback/FBK-20261113-draft.toml",
                 "tmp/manual.py", "tmp/shell.out", ".coverage", "htmlcov/index.html",
                 ".serena/.gitignore", "pkg/__pycache__/unused.cpython-999.pyo"]
        for index, name in enumerate(files):
            self.put(name, f"preserved content {index}")
        protected = self.put("tests/unapproved_test.py")
        with self.assertRaises(ValueError) as caught:
            verify_untracked_sources(self.root)
        for term in ("unapproved_tmp count=5", "tool_state count=1",
                     "coverage_output count=2", "unsupported_cache_format count=1"):
            self.assertIn(term, str(caught.exception))
        self.assertEqual(len(candidates(self.root)), len(files))
        self.assertEqual(recover(self.args()), 0)
        self.assertEqual(recover(self.args() + ["--apply"]), 0)
        destination = next(self.outside.iterdir())
        for index, name in enumerate(files):
            self.assertFalse((self.root / name).exists())
            self.assertEqual((destination / name).read_text(), f"preserved content {index}")
        self.assertTrue(protected.exists())
        with self.assertRaisesRegex(ValueError, "unapproved_source"):
            verify_untracked_sources(self.root)
        protected.unlink()
        verify_untracked_sources(self.root)

    def test_candidate_git_added_after_listing_is_not_moved(self):
        path = self.put("tmp/owner.out")
        original = candidates

        def stale_candidates(root):
            entries = original(root)
            git(self.root, "add", "tmp/owner.out")
            return entries

        with patch("codex_worktree_exec.untracked_recovery.candidates",
                   side_effect=stale_candidates):
            with self.assertRaisesRegex(ValueError, "no longer approved"):
                recover(self.args() + ["--apply"])
        self.assertTrue(path.exists())
        self.assertEqual(git(self.root, "ls-files", "--cached", "--", "tmp/owner.out"),
                         "tmp/owner.out")

    def test_symlink_not_quarantined(self):
        outside = self.outside / "original"
        outside.write_text("protected")
        link = self.root / "tmp" / "link.out"
        link.parent.mkdir(exist_ok=True)
        link.symlink_to(outside)
        self.assertEqual(candidates(self.root), [])
        self.assertEqual(recover(self.args() + ["--apply"]), 0)
        self.assertTrue(link.is_symlink())
        self.assertEqual(outside.read_text(), "protected")

    def test_in_tree_destination_refused(self):
        with self.assertRaisesRegex(ValueError, "outside worktree"):
            recover(["--worktree", str(self.root),
                     "--quarantine-parent", str(self.root / "tmp")])
