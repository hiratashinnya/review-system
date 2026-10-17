"""CLI 全体：検査を通ったときだけ codex を起動し、拒否は識別子付きで exit 2 にする。"""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from codex_worktree_exec.cli import EXIT_REFUSED, EXIT_TIMEOUT, main
from tests.unit.codex_worktree_exec_support import (
    clean_environ,
    make_fake_codex,
    make_repository,
    write_trust,
)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.main, self.worktree = make_repository(self.directory)
        self.home = self.directory / "codex-home"
        write_trust(self.home, self.main)
        self.codex = make_fake_codex(self.directory)
        self.log = self.directory / "call"
        (self.worktree / "tmp").mkdir()
        (self.worktree / "tmp" / "p.md").write_text("README を直す\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def run_main(self, role="issue-fixer", worktree=None, cwd=None, *, exit_code=0, sleep_seconds=0, **extra):
        argv = [
            "--role", role, "-C", str(worktree or self.worktree),
            "--prompt-file", "tmp/p.md", "--output-file", "tmp/o.md",
            "--model", "gpt-6-sol", "--reasoning-effort", "high", "--timeout-seconds", "5",
        ]
        self.codex = make_fake_codex(self.directory, exit_code=exit_code, sleep_seconds=sleep_seconds)
        environ = clean_environ(CODEX_HOME=str(self.home), **extra)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(argv, environ=environ, cwd=cwd or self.worktree, codex=str(self.codex))
        return code, stderr.getvalue()

    def assert_refused_without_launch(self, error_id, **kwargs):
        code, stderr = self.run_main(**kwargs)
        self.assertEqual(code, EXIT_REFUSED, stderr)
        self.assertIn(f"codex_worktree_exec: {error_id}", stderr)
        self.assertFalse(Path(f"{self.log}.argv").exists(), "検査に通らないのに codex が起動された")

    def test_codex_runs_in_the_worktree_and_its_exit_code_is_returned(self):
        code, stderr = self.run_main(exit_code=3)
        self.assertEqual(code, 3, stderr)
        argv = Path(f"{self.log}.argv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(argv[:3], ["exec", "-C", str(self.worktree)])
        self.assertIn('default_permissions="issue-fixer"', argv)
        self.assertIn('shell_environment_policy.inherit="core"', argv)
        self.assertIn(str(self.worktree / "tmp" / "o.md"), argv)
        stdin = Path(f"{self.log}.stdin").read_text(encoding="utf-8")
        self.assertTrue(stdin.endswith("README を直す\n"))

    def test_each_failed_check_refuses_with_its_own_identifier(self):
        self.assert_refused_without_launch("CODEX_EXEC_ROLE_NOT_ALLOWED", role="unknown")
        self.assert_refused_without_launch("CODEX_EXEC_NESTED", CODEX_SANDBOX_NETWORK_DISABLED="1")
        self.assert_refused_without_launch("CODEX_EXEC_WORKTREE_UNREGISTERED", worktree=self.main, cwd=self.main)
        self.assert_refused_without_launch("CODEX_EXEC_WORKTREE_CWD_MISMATCH", worktree=self.main)

    def test_profile_drift_and_untrusted_project_refuse(self):
        write_trust(self.home, self.main, level="untrusted")
        self.assert_refused_without_launch("CODEX_EXEC_PROJECT_UNTRUSTED")
        config = self.worktree / ".codex" / "config.toml"
        config.write_text(config.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assert_refused_without_launch("CODEX_EXEC_PROFILE_DRIFT")

    def test_timeout_exits_124(self):
        code, stderr = self.run_main(sleep_seconds=30)
        self.assertEqual(code, EXIT_TIMEOUT)
        self.assertIn("codex_worktree_exec: CODEX_EXEC_TIMEOUT", stderr)


if __name__ == "__main__":
    unittest.main()
