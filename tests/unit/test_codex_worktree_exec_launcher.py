"""`codex exec` 起動部（終了コードの透過・stdin・timeout）。偽の codex で確かめる。"""

from pathlib import Path
import os
import signal
import subprocess
import tempfile
import time
import unittest
from unittest.mock import Mock, call, patch

from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.launcher import _terminate, run_codex
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

    def test_terminate_skips_sigkill_when_group_disappears_during_grace(self):
        process = Mock(pid=12345)
        with patch("codex_worktree_exec.launcher.time.monotonic", side_effect=[0, 1]):
            with patch("codex_worktree_exec.launcher.os.killpg", side_effect=[None, ProcessLookupError()]) as killpg:
                _terminate(process)
        self.assertEqual(killpg.call_args_list, [call(process.pid, signal.SIGTERM), call(process.pid, 0)])
        self.assertEqual(process.wait.call_args_list, [call(timeout=10), call()])

    def test_terminate_ignores_missing_group_on_sigkill_without_rechecking_after_grace(self):
        process = Mock(pid=12345)
        process.wait.side_effect = [subprocess.TimeoutExpired("codex", 10), None]
        with patch("codex_worktree_exec.launcher.time.monotonic", side_effect=[0, 10]):
            with patch("codex_worktree_exec.launcher.os.killpg", side_effect=[None, ProcessLookupError()]) as killpg:
                _terminate(process)
        self.assertEqual(killpg.call_args_list, [call(process.pid, signal.SIGTERM), call(process.pid, signal.SIGKILL)])
        self.assertEqual(process.wait.call_args_list, [call(timeout=10), call()])

    def test_timeout_kills_term_ignoring_child_after_leader_exits_normally(self):
        leader_pid = self.directory / "leader.pid"
        child_pid = self.directory / "child.pid"
        leader_exit = self.directory / "leader.exit"
        script = self.directory / "term-leader"
        script.write_text(
            "#!/bin/sh\necho $$ > \"$LEADER_PID\"\n"
            "trap 'echo normal > \"$LEADER_EXIT\"; exit 0' TERM\n"
            "sh -c 'trap \"\" TERM; echo $$ > \"$1\"; exec sleep 30' sh \"$CHILD_PID\" &\nwait\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        environ = clean_environ(LEADER_PID=str(leader_pid), CHILD_PID=str(child_pid), LEADER_EXIT=str(leader_exit))
        try:
            with patch("codex_worktree_exec.launcher.TERMINATE_GRACE_SECONDS", 0.1):
                with self.assertRaises(CodexExecError) as caught:
                    run_codex([str(script)], "", cwd=self.directory, timeout_seconds=1, environ=environ)
            self.assertEqual(caught.exception.error_id, "CODEX_EXEC_TIMEOUT")
            self.assertEqual(leader_exit.read_text(encoding="utf-8"), "normal\n")
            stat = Path(f"/proc/{int(child_pid.read_text())}/stat")
            for _ in range(100):
                try:
                    state = stat.read_text().rsplit(")", 1)[1].split()[0]
                except (FileNotFoundError, ProcessLookupError):
                    state = ""
                if state in ("", "Z"):
                    break
                time.sleep(0.01)
            self.assertIn(state, ("", "Z"), "timeout 応答後も子プロセスが動作できる")
        finally:
            if leader_pid.exists():
                try:
                    os.killpg(int(leader_pid.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    unittest.main()
