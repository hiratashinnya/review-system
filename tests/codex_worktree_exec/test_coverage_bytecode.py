"""Compare coverage and plain unittest using the same Python interpreter."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CoverageBytecodeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("uv"), "coverage parity requires uv")
    def test_bytecode_disabled_coverage_matches_plain_unittest(self):
        root = Path(__file__).resolve().parents[2]
        suite = ["-m", "unittest", "discover", "-s", "tests/codex_worktree_exec",
                 "-p", "test_untracked_recovery.py"]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            plain_env = os.environ.copy()
            plain_env.pop("PYTHONDONTWRITEBYTECODE", None)
            plain = subprocess.run([sys.executable, *suite], cwd=root, env=plain_env,
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
