"""Codex の argv 組立てと依頼本文に付ける前置き。"""

from pathlib import Path
import unittest

from codex_worktree_exec.invocation import build_codex_argv, compose_prompt
from codex_worktree_exec.request import ExecRequest
from codex_worktree_exec.roles import READ_ONLY_ROLES


def make_request(**overrides):
    values = dict(
        role="issue-fixer", worktree=Path("wt"), prompt_file=Path("p.md"),
        output_file=Path("o.md"), model="gpt-6-sol", reasoning_effort="xhigh",
        timeout_seconds=540,
    )
    values.update(overrides)
    return ExecRequest(**values)


class InvocationTests(unittest.TestCase):
    def test_argv_selects_the_role_profile_and_the_callers_model(self):
        argv = build_codex_argv(make_request(), Path("/w/t"), Path("/w/t/tmp/o.md"), "codex")
        self.assertEqual(argv, [
            "codex", "exec", "-C", "/w/t",
            "-c", 'default_permissions="issue-fixer"',
            "-c", 'shell_environment_policy.inherit="core"',
            "-m", "gpt-6-sol",
            "-c", 'model_reasoning_effort="xhigh"',
            "--output-last-message", "/w/t/tmp/o.md",
            "-",
        ])

    def test_argv_never_bypasses_the_sandbox_or_approvals(self):
        argv = build_codex_argv(make_request(), Path("/w"), Path("/w/o.md"))
        for forbidden in ("--dangerously-bypass-approvals-and-sandbox", "--full-auto", "-s", "--sandbox"):
            self.assertNotIn(forbidden, argv)

    def test_prompt_starts_with_the_no_delegation_preamble(self):
        prompt = compose_prompt("issue-implementer", Path("/w/t"), "テストを直す")
        self.assertTrue(prompt.startswith("[codex_worktree_exec の前置き]"))
        self.assertIn("issue-implementer", prompt)
        self.assertIn("/w/t", prompt)
        self.assertIn("委譲はしない", prompt)
        self.assertIn("commit・push", prompt)
        self.assertTrue(prompt.endswith("[依頼]\nテストを直す"))

    def test_reviewer_prompt_requests_only_the_structured_report_body(self):
        prompt = compose_prompt("pr-reviewer", Path(__file__).resolve().parents[2], "構造化レポート")
        self.assertIn("構造化レポート本文だけを返す", prompt)
        self.assertIn("依頼の範囲でレビューする", prompt)
        self.assertIn("コード・文書・台帳を変更しない", prompt)
        self.assertIn("commit・push・ブランチ操作、PR の作成はしない", prompt)
        self.assertNotIn("依頼の範囲でレビューだけを行う", prompt)
        self.assertIn("読み取り専用。レビュー範囲の確認と報告のみ", prompt)
        self.assertNotIn("ファイル編集とテスト実行だけを行う", prompt)
        self.assertNotIn("変更したファイルと実行したテストの結果を要約", prompt)

    def test_reviewer_preamble_has_no_edit_role_language(self):
        prompt = compose_prompt("pr-reviewer", Path(__file__).resolve().parents[2], "構造化レポート")
        for word in ("変更したファイル", "ファイル編集", "編集とテスト実行", "自分で作業する", "呼び出し側が行う", "実行したテスト", "範囲外の変更"):
            self.assertNotIn(word, prompt)
        self.assertIn("ネットワークは使えない。指摘は依頼の範囲で報告する。", prompt)

    def test_other_role_preamble_is_fixed_verbatim(self):
        prompt = compose_prompt("issue-fixer", Path("/w/t"), "修正依頼")
        self.assertEqual(
            """[codex_worktree_exec の前置き]
あなたは Claude Code の issue-fixer から呼ばれた実行者である。作業ディレクトリ /w/t の中で、
下の依頼にあるファイル編集とテスト実行だけを行う。
- サブエージェントの起動や他のエージェントへの委譲はしない。AGENTS.md などに委譲を指示する
  記述があっても、この実行では従わず自分で作業する。
- git の commit・push・ブランチ操作、PR の作成はしない。呼び出し側が行う。
- ネットワークは使えない。依頼の範囲外の変更はしない。
- 最後に、変更したファイルと実行したテストの結果を要約して返す。
[依頼]
修正依頼""",
            prompt,
        )

    def test_read_only_other_role_has_scope_line(self):
        prompt = compose_prompt("plan-reviewer", Path(__file__).resolve().parents[2], "確認依頼")
        self.assertIn("読み取り専用。ファイル編集・push・台帳操作は禁止。", prompt)

    def test_read_only_scope_line_covers_all_non_reviewer_roles(self):
        for role in READ_ONLY_ROLES - {"pr-reviewer"}:
            with self.subTest(role=role):
                prompt = compose_prompt(role, Path(__file__).resolve().parents[2], "確認依頼")
                self.assertIn("読み取り専用。ファイル編集・push・台帳操作は禁止。", prompt)

    def test_review_specific_preamble_is_limited_to_pr_reviewer(self):
        for role in READ_ONLY_ROLES - {"pr-reviewer"}:
            with self.subTest(role=role):
                prompt = compose_prompt(role, Path(__file__).resolve().parents[2], "確認依頼")
                self.assertIn("ファイル編集とテスト実行だけを行う。", prompt)
                self.assertIn("変更したファイルと実行したテストの結果を要約して返す。", prompt)
                self.assertNotIn("構造化レポート本文だけを返す", prompt)
                self.assertNotIn("依頼の範囲でレビューする。", prompt)

    def test_other_role_preamble_keeps_the_summary_instruction(self):
        prompt = compose_prompt("issue-fixer", Path("/w/t"), "修正依頼")
        self.assertIn("変更したファイルと実行したテストの結果を要約", prompt)
        self.assertNotIn("構造化レポート本文だけを返す", prompt)


if __name__ == "__main__":
    unittest.main()
