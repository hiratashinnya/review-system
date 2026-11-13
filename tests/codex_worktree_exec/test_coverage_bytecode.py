"""Coverage smoke and failure-state checks for bytecode isolation."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from codex_worktree_exec.coverage_parity import validate


class CoverageBytecodeTests(unittest.TestCase):
    def test_matching_failures_still_reject_done(self):
        error = subprocess.CompletedProcess([], 1, "", "FAIL: example.test\n")
        with self.assertRaisesRegex(ValueError, "matching_failures="):
            validate(error, error)

    @unittest.skipUnless(shutil.which("uv"), "coverage parity requires uv")
    def test_bytecode_disabled_coverage_matches_plain_unittest(self):
        root = Path(__file__).resolve().parents[2]
        suite = ["-m", "unittest", "discover", "-s", "tests/codex_worktree_exec",
                 "-p", "test_untracked_recovery.py"]
        before = {p.relative_to(root) for p in root.rglob("__pycache__/*.pyc")}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            plain_env = os.environ.copy()
            plain_env.pop("PYTHONDONTWRITEBYTECODE", None)
            plain_env["PYTHONPYCACHEPREFIX"] = str(output / "plain-pycache")
            plain = subprocess.run([sys.executable, *suite], cwd=root, env=plain_env,
                                   text=True, capture_output=True)
            covered_env = dict(plain_env, PYTHONDONTWRITEBYTECODE="1",
                               COVERAGE_FILE=str(output / ".coverage"))
            covered_env.pop("PYTHONPYCACHEPREFIX", None)
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
        after = {p.relative_to(root) for p in root.rglob("__pycache__/*.pyc")}
        self.assertEqual(before, after)
