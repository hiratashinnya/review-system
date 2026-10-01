"""Fail-open SessionStart wrapper behavior for Codex hook trust checks."""

import json
from pathlib import Path
import tempfile
import unittest

from tests.unit.codex_hook_trust_repo_support import make_repository_pair, read_trace, write_hooks
from tests.unit.codex_hook_trust_support import make_fake_codex, run_hook


class CodexHookTrustHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.codex = make_fake_codex(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_trusted_state_is_silent(self):
        result = run_hook(self.codex)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_untrusted_state_emits_only_a_warning(self):
        result = run_hook(self.codex, "mixed")
        self.assertEqual(result.returncode, 0)
        self.assertIn("stop:0:0", result.stdout)
        self.assertIn("機械ゲートが動作していない可能性", result.stdout)
        self.assertIn(".codex/hooks/README.md", result.stdout)
        self.assertNotIn("payload-must-be-discarded", result.stdout)

    def test_missing_project_trust_emits_warning(self):
        result = run_hook(self.codex, "zero-hooks")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("定義 6 件に対し発見 0 件", context)
        self.assertIn('trust_level = "trusted"', context)
        self.assertIn("機械ゲートが動作していない可能性", context)
        self.assertIn(".codex/hooks/README.md", context)
        self.assertNotIn("payload-must-be-discarded", context)

    def test_undetermined_state_is_silent(self):
        result = run_hook(self.codex.with_name("missing-codex"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_worktree_session_start_uses_main_checkout_path(self):
        main, worktree = make_repository_pair(Path(self.temp.name), 2)
        write_hooks(worktree, 5)
        trace = Path(self.temp.name) / "hook-app-server.jsonl"

        result = run_hook(
            self.codex, "zero-hooks", repo=worktree,
            extra_env={"FAKE_CODEX_TRACE": str(trace)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("定義 2 件に対し発見 0 件", context)
        self.assertIn('[projects."' + str(main) + '"]', context)
        self.assertNotIn(str(worktree), context)
        self.assertEqual(read_trace(trace), {
            "cwd": str(main),
            "cwds": [str(main)],
            "config_path": str(main / ".codex" / "hooks.json"),
        })


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
