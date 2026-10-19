"""CLI の tmp 境界検査が偽 Codex の起動前に失敗することを確認する。"""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from codex_worktree_exec.cli import EXIT_REFUSED, main
from tests.unit.codex_worktree_exec_support import clean_environ, make_fake_codex, make_repository, write_trust


class CliFileBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        primary, self.worktree = make_repository(self.directory)
        self.home = self.directory / "codex-home"
        write_trust(self.home, primary)
        self.codex = make_fake_codex(self.directory)
        self.log = self.directory / "call"
        self.tmp = self.worktree / "tmp"
        self.tmp.mkdir()
        (self.tmp / "p.md").write_text("非秘密の依頼", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def assert_refused_without_launch(self, option, path, error_id):
        files = {"--prompt-file": "tmp/p.md", "--output-file": "tmp/o.md", option: str(path)}
        argv = ["--role", "issue-fixer", "-C", str(self.worktree),
                "--model", "gpt-6-sol", "--reasoning-effort", "high"]
        for name, value in files.items():
            argv.extend((name, value))
        environ = clean_environ(CODEX_HOME=str(self.home))
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(argv, environ=environ, cwd=self.worktree, codex=str(self.codex))
        self.assertEqual(code, EXIT_REFUSED, stderr.getvalue())
        self.assertIn(f"codex_worktree_exec: {error_id}", stderr.getvalue())
        self.assertFalse(Path(f"{self.log}.argv").exists())

    def test_outside_absolute_parent_and_parent_symlink_paths_never_launch(self):
        fixture = self.directory / "fixture.md"
        fixture.write_text("非秘密のfixture", encoding="utf-8")
        outside = self.worktree / "fixture.md"
        outside.write_text("非秘密のfixture", encoding="utf-8")
        (self.tmp / "outside").symlink_to(self.directory, target_is_directory=True)
        paths = (fixture, Path("tmp/../fixture.md"), Path("tmp/outside/fixture.md"))
        for option, error_id in (("--prompt-file", "CODEX_EXEC_PROMPT_UNREADABLE"),
                                 ("--output-file", "CODEX_EXEC_OUTPUT_INVALID")):
            for path in paths:
                with self.subTest(option=option, path=path):
                    self.assert_refused_without_launch(option, path, error_id)

    def test_tmp_symlink_outside_the_worktree_never_launches(self):
        (self.tmp / "p.md").unlink()
        self.tmp.rmdir()
        self.tmp.symlink_to(self.directory, target_is_directory=True)
        (self.directory / "p.md").write_text("非秘密のfixture", encoding="utf-8")
        self.assert_refused_without_launch("--prompt-file", "tmp/p.md", "CODEX_EXEC_PROMPT_UNREADABLE")


if __name__ == "__main__":
    unittest.main()
