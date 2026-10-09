"""Fail-open SessionStart wrapper behavior for Codex hook trust checks."""

import json
from pathlib import Path
import unittest

from tests.unit.codex_hook_trust_repo_support import (
    init_repository,
    make_failing_git_path,
    make_repository_pair,
    read_trace,
    write_hooks,
)
from tests.unit.codex_hook_trust_support import (
    CodexHookTrustTestMixin, hook_count_report,
)


class CodexHookTrustHookTests(CodexHookTrustTestMixin, unittest.TestCase):
    def test_trusted_state_is_silent(self):
        result = self._run_hook()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_untrusted_state_emits_only_a_warning(self):
        result = self._run_hook("mixed")
        self.assertEqual(result.returncode, 0)
        self.assertIn("pre_tool_use:2:0", result.stdout)
        self.assertIn("登録件数が定義件数より少ないか、未信頼の Codex フックがあります", result.stdout)
        self.assertIn("機械ゲートが動作していない可能性", result.stdout)
        self.assertIn(".codex/hooks/README.md", result.stdout)
        self.assertNotIn("payload-must-be-discarded", result.stdout)

    def test_missing_project_trust_emits_warning(self):
        result = self._run_hook("zero-hooks")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn(hook_count_report(self.repo, 0), context)
        self.assertIn("登録件数が定義件数より少ないか、未信頼の Codex フックがあります", context)
        self.assertIn('trust_level = "trusted"', context)
        self.assertIn("機械ゲートが動作していない可能性", context)
        self.assertIn(".codex/hooks/README.md", context)
        self.assertNotIn("payload-must-be-discarded", context)

    def test_undetermined_state_is_silent(self):
        result = self._run_hook(executable=self.codex.with_name("missing-codex"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_worktree_session_start_uses_main_checkout_path(self):
        main, worktree = make_repository_pair(Path(self.temp.name), 2)
        write_hooks(worktree, 5)
        trace = Path(self.temp.name) / "hook-app-server.jsonl"

        result = self._run_hook(
            "zero-hooks", repo=worktree,
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

    def test_git_fallback_note_is_in_session_start_warning(self):
        repo = Path(self.temp.name) / "git-failure"
        init_repository(repo, 2)
        git_failure_path = make_failing_git_path(Path(self.temp.name))

        result = self._run_hook(
            "zero-hooks", repo=repo,
            extra_env={"PATH": git_failure_path},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn(f"渡されたパス（{repo}）で検査しました", context)
        self.assertIn("信頼記録の実キーはメインのパスのため、確認先が異なる場合があります。", context)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
