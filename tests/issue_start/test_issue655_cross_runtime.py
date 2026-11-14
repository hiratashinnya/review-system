"""Issue #655: a real second CPython produces foreign cache; no mock/rename."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from codex_worktree_exec.cache_prune import main as prune
from codex_worktree_exec.source_snapshot import verify_untracked_sources
from tests.unit.codex_worktree_exec_support import git, make_repository


class CrossPythonCacheTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("ISSUE655_PREVIOUS_PYTHON"),
                         "one-shot CI acceptance: a second installed Python required")
    def test_two_real_python_versions_detect_and_quarantine_foreign_cache(self):
        other = os.environ["ISSUE655_PREVIOUS_PYTHON"]
        other_tag = subprocess.check_output(
            [other, "-B", "-c", "import sys;print(sys.implementation.cache_tag)"],
            text=True).strip()
        self.assertNotEqual(other_tag, sys.implementation.cache_tag)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, root = make_repository(base)
            source = root / "module.py"
            source.write_text("answer = 42\n")
            git(root, "add", "module.py")
            git(root, "commit", "-qm", "dummy committed source")
            subprocess.run([other, "-c",
                            "import sys,unittest;sys.path.insert(0,sys.argv[1]);"
                            "import module;unittest.TestCase().assertEqual(module.answer,42)",
                            str(root)], check=True)
            cache = list((root / "__pycache__").glob("*.pyc"))
            self.assertEqual(len(cache), 1)
            self.assertIn(other_tag, cache[0].name)
            original = cache[0].read_bytes()
            with self.assertRaisesRegex(ValueError, "foreign_cache count=1"):
                verify_untracked_sources(root)
            safe = base / "saved"
            safe.mkdir()
            self.assertEqual(prune(["--worktree", str(root),
                                    "--quarantine-parent", str(safe), "--apply"]), 0)
            verify_untracked_sources(root)
            found = list(safe.glob("review-system-cache-*/__pycache__/*.pyc"))
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].read_bytes(), original)
