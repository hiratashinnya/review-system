"""pr-reviewer の Write を handoff ファイルに限る PreToolUse 判定（Issue #375）。"""

import os
import shutil
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


if __name__ == "__main__":
    unittest.main()
