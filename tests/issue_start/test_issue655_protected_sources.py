"""Issue #655 AC: gitignore/exclude must not allow normal source, TC or symlinks."""
import tempfile
import unittest
from pathlib import Path

from codex_worktree_exec.source_snapshot import verify_untracked_sources
from codex_worktree_exec.untracked_recovery import main as recover
from tests.unit.codex_worktree_exec_support import make_repository


class ProtectedSourceTests(unittest.TestCase):
    def test_git_exclude_does_not_authorize_source_test_or_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            _, root = make_repository(home)
            exclude = root / ".git" / "info" / "exclude"
            # Linked worktrees have a .git file: edit the main checkout's .git/info/exclude.
            main_git = home / "main" / ".git" / "info" / "exclude"
            main_git.write_text("*.py\n*.toml\n")
            files = ["tools/surprise.py", "tests/tool/test_injected.py",
                     "config/unsafe.toml"]
            for name in files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("dummy")
            outside = home / "external-file"
            outside.write_text("preserve owner data")
            link = root / "tmp" / "outsider.out"
            link.parent.mkdir()
            link.symlink_to(outside)
            with self.assertRaises(ValueError) as caught:
                verify_untracked_sources(root)
            self.assertIn("unapproved_source count=3", str(caught.exception))
            self.assertIn("unsafe_path count=1", str(caught.exception))
            preserve = home / "preserved"
            preserve.mkdir()
            self.assertEqual(recover(["--worktree", str(root), "--apply",
                                      "--quarantine-parent", str(preserve)]), 0)
            for name in files:
                self.assertTrue((root / name).is_file())
            self.assertTrue(link.is_symlink())
            self.assertEqual(outside.read_text(), "preserve owner data")
            with self.assertRaisesRegex(ValueError, "unapproved_source"):
                verify_untracked_sources(root)
