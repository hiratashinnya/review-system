"""pr-reviewer の Write を handoff ファイルに限る PreToolUse 判定（Issue #375）。"""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from issue_start.gated_roles import READ_ONLY_ROLES
from issue_start.phase_tool_gate import decision


class TestReviewerHandoffWrite(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="rv-write-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        (self.root / "tmp" / "_handoff").mkdir(parents=True)
        (self.root / ".git").mkdir()
        patcher = mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.root)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write(self, role, path, tool="Write"):
        return decision(dict(agent_type=role, tool_name=tool, cwd=str(self.root),
                             tool_input={"file_path": str(path)}))

    def _denied(self, result):
        return result is not None and result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_reviewer_may_write_its_handoff_file(self):
        self.assertIsNone(self._write("pr-reviewer", self.root / "tmp/_handoff/pr-reviewer--k1.md"))

    def test_reviewer_write_requires_exact_directory_and_filename(self):
        for target, reason in (
            ("docs/_handoff/pr-reviewer--k.md", "直下ではない"),
            ("tmp/x/_handoff/pr-reviewer--k.md", "直下ではない"),
            ("tmp/_handoff/pr-reviewer--a b.md", "ファイル名が"),
            ("tmp/_handoff/pr-reviewer--a;b.md", "ファイル名が"),
            ("tmp/_handoff/pr-reviewer--a$(b).md", "ファイル名が"),
            ("tmp/_handoff/pr-reviewer--日本.md", "ファイル名が"),
            ("tmp/_handoff/pr-reviewer---x.md", "ファイル名が"),
            ("tmp/_handoff/pr-reviewer--_x.md", "ファイル名が"),
            ("tmp/_handoff/pr-reviewer--.x.md", "ファイル名が"),
            ("tmp/_handoff/pr-reviewer--.md", "ファイル名が"),
        ):
            with self.subTest(target=target):
                result = self._write("pr-reviewer", self.root / target)
                self.assertTrue(self._denied(result))
                self.assertIn("パス不正", self._reason(result))
                self.assertIn(reason, self._reason(result))
        self.assertIsNone(self._write("pr-reviewer", self.root / "tmp/_handoff/pr-reviewer--A0._-z.md"))

    def test_reviewer_writes_elsewhere_are_denied(self):
        _ = self.root / "tmp" / "elsewhere.md"
        (self.root / "tmp" / "_karte").mkdir()
        (self.root / "tmp" / "_handoff" / "link.md").symlink_to(_)
        for target in (
            "tmp/_karte/issue-1.md", "tmp/_handoff/other.md", "tmp/_handoff/pr-reviewer--k.sh",
            "tmp/_handoff/../_karte/pr-reviewer--k.md", "tmp/_handoff/sub/pr-reviewer--k.md",
            "tmp/_handoff/pr-reviewer--k1.md.bak", "karte/cli.py", "/etc/passwd",
        ):
            with self.subTest(target=target):
                self.assertTrue(self._denied(self._write("pr-reviewer", self.root / target)))

    def test_symlinked_directory_component_is_denied(self):
        outside = Path(tempfile.mkdtemp(prefix="rv-out-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        shutil.rmtree(self.root / "tmp" / "_handoff")
        (self.root / "tmp" / "_handoff").symlink_to(outside)
        self.assertTrue(self._denied(self._write("pr-reviewer", self.root / "tmp/_handoff/pr-reviewer--k1.md")))

    def test_edit_tools_stay_denied_for_reviewer(self):
        target = self.root / "tmp/_handoff/pr-reviewer--k1.md"
        for tool in ("Edit", "NotebookEdit", "MultiEdit"):
            self.assertTrue(self._denied(self._write("pr-reviewer", target, tool)), tool)

    def test_other_readonly_roles_cannot_write_even_handoff_path(self):
        target = self.root / "tmp/_handoff/pr-reviewer--k1.md"
        for role in READ_ONLY_ROLES - {"pr-reviewer"}:
            self.assertTrue(self._denied(self._write(role, target)), role)

    def test_missing_tool_input_is_denied(self):
        self.assertTrue(self._denied(decision(dict(agent_type="pr-reviewer", tool_name="Write"))))

    def test_non_string_file_path_is_reported_as_invalid_input(self):
        for value in (None, 42, [], {}):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()) as err:
                result = decision(dict(agent_type="pr-reviewer", tool_name="Write",
                                       tool_input={"file_path": value}))
                self.assertIn("入力不正", self._reason(result))
                self.assertNotIn("ゲート自体の故障", self._reason(result))
                self.assertEqual("", err.getvalue())

    def _reason(self, result):
        return result["hookSpecificOutput"]["permissionDecisionReason"]

    def test_invalid_path_is_reported_as_a_path_problem_not_a_gate_failure(self):
        result = self._write("pr-reviewer", self.root / "tmp/_karte/issue-1.md")
        self.assertIn("パス不正", self._reason(result))
        self.assertNotIn("ゲート自体の故障", self._reason(result))

    def test_import_failure_is_reported_as_a_gate_failure_with_the_cause_on_stderr(self):
        broken = {"karte.handoff_path": None}  # None を入れると import が ImportError になる
        err = io.StringIO()
        with mock.patch.dict(sys.modules, broken), contextlib.redirect_stderr(err):
            result = self._write("pr-reviewer", self.root / "tmp/_handoff/pr-reviewer--k1.md")
        self.assertTrue(self._denied(result))
        self.assertIn("ゲート自体の故障", self._reason(result))
        self.assertNotIn("パス不正", self._reason(result))
        self.assertIn("ModuleNotFoundError", err.getvalue())  # ImportError の派生

    def test_unexpected_failure_while_resolving_the_root_is_a_gate_failure(self):
        err = io.StringIO()
        with mock.patch("karte.paths.main_worktree_root", side_effect=RuntimeError("git が壊れている")):
            with contextlib.redirect_stderr(err):
                result = self._write("pr-reviewer", self.root / "tmp/_handoff/pr-reviewer--k1.md")
        self.assertIn("ゲート自体の故障", self._reason(result))
        self.assertIn("RuntimeError", err.getvalue())


if __name__ == "__main__":
    unittest.main()
