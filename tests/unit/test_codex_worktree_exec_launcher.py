"""`codex exec` 起動部（終了コードの透過・stdin・timeout）。偽の codex で確かめる。"""

from pathlib import Path
import tempfile
import time
import unittest

from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.launcher import run_codex
from codex_worktree_exec.nesting_guard import NESTING_MARKER
from tests.unit.codex_worktree_exec_support import clean_environ, make_fake_codex


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.codex = make_fake_codex(self.directory)
        self.log = self.directory / "call"

    def tearDown(self):
        self.temp.cleanup()

    def run_fake(self, timeout_seconds=30, **extra):
        environ = clean_environ(FAKE_CODEX_LOG=str(self.log), **extra)
        return run_codex(
            [str(self.codex), "exec", "-"], "依頼本文",
            cwd=self.directory, timeout_seconds=timeout_seconds, environ=environ,
        )

    def test_exit_code_is_passed_through(self):
        for code in ("0", "1", "7"):
            with self.subTest(code=code):
                self.assertEqual(self.run_fake(FAKE_CODEX_EXIT=code), int(code))

    def test_prompt_goes_to_stdin_and_the_nesting_marker_to_the_child(self):
        self.run_fake()
        self.assertEqual(Path(f"{self.log}.stdin").read_text(encoding="utf-8"), "依頼本文")
        self.assertIn(f"{NESTING_MARKER}=1", Path(f"{self.log}.env").read_text(encoding="utf-8"))

    def test_timeout_stops_the_process_and_is_reported(self):
        started = time.monotonic()
        with self.assertRaises(CodexExecError) as caught:
            self.run_fake(timeout_seconds=1, FAKE_CODEX_SLEEP="30")
        self.assertEqual(caught.exception.error_id, "CODEX_EXEC_TIMEOUT")
        self.assertLess(time.monotonic() - started, 15)

    def test_missing_executable_is_a_launch_failure(self):
        with self.assertRaises(CodexExecError) as caught:
            run_codex(
                [str(self.directory / "no-codex"), "exec", "-"], "x",
                cwd=self.directory, timeout_seconds=5, environ=clean_environ(),
            )
        self.assertEqual(caught.exception.error_id, "CODEX_EXEC_LAUNCH_FAILED")


if __name__ == "__main__":
    unittest.main()
