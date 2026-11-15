"""Issue #655: readonly errors use an IssueStartError code."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from issue_start.gate_support import IssueStartError
from issue_start.readonly_workspace import prepare_readonly_workspace


class ReadonlySourceErrorsTests(unittest.TestCase):
    def test_preparation_has_structured_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("issue_start.readonly_workspace.bind_worktree",
                       side_effect=ValueError("unsafe checkout")):
                with self.assertRaises(IssueStartError) as caught:
                    prepare_readonly_workspace(root, root, "pr-reviewer", {}, "tmp/prompt.md")
            self.assertEqual(caught.exception.reason,
                             "ISSUE_START_READONLY_WORKSPACE_INVALID")
            self.assertIn("unsafe checkout", caught.exception.detail)
