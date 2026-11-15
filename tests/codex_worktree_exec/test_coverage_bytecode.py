"""Coverage smoke and failure-state checks for bytecode isolation."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from codex_worktree_exec.coverage_parity import validate, require_head_test_source_inventory
from tests.unit.codex_worktree_exec_support import make_repository


class CoverageBytecodeTests(unittest.TestCase):
    def test_matching_failures_still_reject_done(self):
        error = subprocess.CompletedProcess([], 1, "", "FAIL: example.test\n")
        with self.assertRaisesRegex(ValueError, "matching_failures="):
            validate(error, error)


    def test_untracked_successful_test_must_refuse_parity(self):
        """A test that passes only on the coverage side cannot be silently ignored."""
        with tempfile.TemporaryDirectory() as directory:
            _, root = make_repository(Path(directory))
            tests = root / "tests"
            tests.mkdir()
            extra = tests / "test_only_coverage.py"
            extra.write_text(
                "import unittest\n"
                "class CoverageOnlyTests(unittest.TestCase):\n"
                "    def test_success(self): self.assertTrue(True)\n"
            )
            with self.assertRaisesRegex(ValueError, r"coverage input inventory differs from HEAD"):
                require_head_test_source_inventory(root)
            extra.unlink()
            require_head_test_source_inventory(root)

    def test_ignored_source_cannot_bypass_inventory_check(self):
        with tempfile.TemporaryDirectory() as directory:
            _, root = make_repository(Path(directory))
            (root / ".gitignore").write_text("injected.py\n")
            (root / "injected.py").write_text("VALUE = 42\n")
            with self.assertRaisesRegex(ValueError, r"injected.py"):
                require_head_test_source_inventory(root)

    def test_non_source_tmp_data_does_not_fail_inventory_check(self):
        with tempfile.TemporaryDirectory() as directory:
            _, root = make_repository(Path(directory))
            (root / "tmp").mkdir()
            (root / "tmp" / "progress.json").write_text("{}\n")
            require_head_test_source_inventory(root)

    @unittest.skipUnless(shutil.which("uv"), "coverage parity requires uv")
    def test_bytecode_disabled_coverage_matches_plain_unittest(self):
        root = Path(__file__).resolve().parents[2]
        suite = ["-m", "unittest", "discover", "-s", "tests/codex_worktree_exec",
                 "-p", "test_untracked_recovery.py"]
        before = {p.relative_to(root) for p in root.rglob("__pycache__/*.pyc")}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            plain_root = output / "plain-checkout"
            subprocess.run(["git", "-C", str(root), "worktree", "add",
                            "--detach", "-q", str(plain_root), "HEAD"], check=True)
            try:
                plain_env = os.environ.copy()
                plain_env.pop("PYTHONDONTWRITEBYTECODE", None)
                plain_env.pop("PYTHONPYCACHEPREFIX", None)
                plain = subprocess.run([sys.executable, *suite], cwd=plain_root, env=plain_env,
                                       text=True, capture_output=True)
                covered_env = dict(plain_env, PYTHONDONTWRITEBYTECODE="1",
                                   COVERAGE_FILE=str(output / ".coverage"))
                covered = subprocess.run(
                    ["uv", "run", "--no-project", "--python", sys.executable,
                     "--with", "coverage", "coverage", "run", *suite],
                    cwd=root, env=covered_env, text=True, capture_output=True)
                failures = lambda result: set(re.findall(
                    r"^(?:FAIL|ERROR): ([^\n]+)", result.stdout + result.stderr, re.MULTILINE))
                self.assertEqual(failures(plain), failures(covered), covered.stderr)
                self.assertEqual(plain.returncode, 0, plain.stderr)
                self.assertEqual(covered.returncode, 0, covered.stderr)
                self.assertTrue((output / ".coverage").is_file())
            finally:
                subprocess.run(["git", "-C", str(root), "worktree", "remove",
                                "--force", str(plain_root)], check=True)
        after = {p.relative_to(root) for p in root.rglob("__pycache__/*.pyc")}
        self.assertEqual(before, after)
