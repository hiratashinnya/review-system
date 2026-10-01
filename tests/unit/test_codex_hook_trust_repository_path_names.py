"""Repository paths ending in whitespace remain exact during trust checks."""

import json
import os
from pathlib import Path
import tempfile
import unittest

from codex_hook_trust.repository import resolve_main_checkout
from tests.unit.codex_hook_trust_fake_server import make_fake_codex
from tests.unit.codex_hook_trust_repo_support import (
    init_repository,
    make_repository_pair,
    read_trace,
    write_hooks,
)
from tests.unit.codex_hook_trust_support import run_check


class CodexHookTrustRepositoryPathNameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.codex = make_fake_codex(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_trailing_space_is_not_removed_or_replaced_by_decoy_repository(self):
        self._assert_exact_main_path("main ", "main", "trailing-space")

    def test_trailing_newline_is_not_removed_or_replaced_by_decoy_repository(self):
        if os.name == "nt":
            self.skipTest("Windows does not allow newline characters in path names")
        self._assert_exact_main_path("main\n", "main", "trailing-newline")

    def _assert_exact_main_path(self, main_name, decoy_name, case_name):
        main, worktree = make_repository_pair(
            self.directory, 2, main_name=main_name, worktree_name="linked",
        )
        decoy = self.directory / decoy_name
        init_repository(decoy, 3)
        write_hooks(worktree, 5)

        self.assertEqual(resolve_main_checkout(worktree), main)
        trace = self.directory / f"{case_name}-app-server.jsonl"
        result = run_check(
            self.codex, "zero-hooks", repo=worktree,
            extra_env={"FAKE_CODEX_TRACE": str(trace)},
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("定義 2 件に対し発見 0 件", result.stdout)
        self.assertIn(
            f'[projects.{json.dumps(str(main), ensure_ascii=False)}]', result.stdout,
        )
        self.assertNotIn(
            f'[projects.{json.dumps(str(decoy), ensure_ascii=False)}]', result.stdout,
        )
        self.assertEqual(read_trace(trace), {
            "cwd": str(main),
            "cwds": [str(main)],
            "config_path": str(main / ".codex" / "hooks.json"),
        })


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
