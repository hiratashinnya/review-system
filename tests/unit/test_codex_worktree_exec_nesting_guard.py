"""Codex 内の環境マーカーによる再帰起動の拒否。"""

import unittest

from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.nesting_guard import NESTING_MARKER, refuse_nested_launch


class NestingGuardTests(unittest.TestCase):
    def test_markers_of_running_inside_codex_are_refused(self):
        for name in (NESTING_MARKER, "CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED"):
            with self.subTest(name=name), self.assertRaises(CodexExecError) as caught:
                refuse_nested_launch({name: "1"})
            self.assertEqual(caught.exception.error_id, "CODEX_EXEC_NESTED")

    def test_plain_environment_passes(self):
        refuse_nested_launch({"PATH": "/usr/bin", "CODEX_SANDBOX": ""})


if __name__ == "__main__":
    unittest.main()
