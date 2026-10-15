"""依頼文・応答先の通常ファイル検査と worktree/tmp の実パス境界。"""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.prompt_files import MAX_PROMPT_BYTES, read_prompt, resolve_output_target


class PromptFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.worktree = self.directory / "worktree"
        self.tmp = self.worktree / "tmp"
        self.tmp.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def assert_refused(self, call, error_id):
        with self.assertRaises(CodexExecError) as caught:
            call()
        self.assertEqual(caught.exception.error_id, error_id)

    def test_prompt_and_output_are_resolved_relative_to_cwd_within_tmp(self):
        (self.tmp / "p.md").write_text("依頼本文\n", encoding="utf-8")
        for cwd, prefix in ((self.worktree, Path("tmp")), (self.tmp, Path("."))):
            with self.subTest(cwd=cwd):
                self.assertEqual(read_prompt(prefix / "p.md", cwd, self.worktree), "依頼本文\n")
                self.assertEqual(resolve_output_target(prefix / "o.md", cwd, self.worktree), self.tmp / "o.md")

    def test_unusable_prompts_are_refused(self):
        bodies = {"empty.md": b"  \n", "binary.md": b"\xff\xfe", "large.md": b"x" * (MAX_PROMPT_BYTES + 1)}
        for name, data in bodies.items():
            (self.tmp / name).write_bytes(data)
        (self.tmp / "link.md").symlink_to(self.tmp / "large.md")
        for name in (*bodies, "link.md", "absent.md"):
            with self.subTest(name=name):
                self.assert_refused(lambda: read_prompt(Path(name), self.tmp, self.worktree), "CODEX_EXEC_PROMPT_UNREADABLE")

    def test_output_target_must_be_a_plain_path_in_an_existing_directory(self):
        (self.tmp / "dir").mkdir()
        (self.tmp / "link.md").symlink_to(self.tmp / "o.md")
        for name in ("dir", "link.md", "missing/o.md"):
            with self.subTest(name=name):
                self.assert_refused(lambda: resolve_output_target(Path(name), self.tmp, self.worktree), "CODEX_EXEC_OUTPUT_INVALID")

    def test_outside_absolute_parent_and_parent_symlink_paths_are_refused_before_read(self):
        (self.directory / "fixture.md").write_text("非秘密のfixture", encoding="utf-8")
        (self.tmp / "outside").symlink_to(self.directory, target_is_directory=True)
        paths = (self.directory / "fixture.md", Path("../fixture.md"), Path("tmp/outside/fixture.md"))
        for path in paths:
            with self.subTest(path=path), patch.object(Path, "read_bytes") as read:
                self.assert_refused(lambda: read_prompt(path, self.worktree, self.worktree), "CODEX_EXEC_PROMPT_UNREADABLE")
                read.assert_not_called()
                self.assert_refused(lambda: resolve_output_target(path, self.worktree, self.worktree), "CODEX_EXEC_OUTPUT_INVALID")

    def test_tmp_symlink_outside_the_worktree_is_refused_before_read(self):
        self.tmp.rmdir()
        self.tmp.symlink_to(self.directory, target_is_directory=True)
        (self.directory / "fixture.md").write_text("非秘密のfixture", encoding="utf-8")
        with patch.object(Path, "read_bytes") as read:
            self.assert_refused(lambda: read_prompt(Path("tmp/fixture.md"), self.worktree, self.worktree), "CODEX_EXEC_PROMPT_UNREADABLE")
            read.assert_not_called()
        self.assert_refused(lambda: resolve_output_target(Path("tmp/o.md"), self.worktree, self.worktree), "CODEX_EXEC_OUTPUT_INVALID")


if __name__ == "__main__":
    unittest.main()
