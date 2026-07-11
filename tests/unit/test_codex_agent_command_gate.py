import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".codex" / "hooks" / "agent-command-gate.sh"


def run_gate(payload, *, env=None):
    result = subprocess.run(
        [str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **(env or {})},
    )
    if not result.stdout:
        return None
    return json.loads(result.stdout)


def payload(agent_type, command, *, tool_name="Bash"):
    # Codex PreToolUse 入力スキーマ準拠：agent_type / tool_name / tool_input.command。
    body = {"tool_name": tool_name, "tool_input": {"command": command}}
    if agent_type is not None:
        body["agent_type"] = agent_type
    return body


class CodexAgentCommandGateTests(unittest.TestCase):
    def assert_denied(self, hook_output):
        self.assertIsNotNone(hook_output)
        self.assertEqual(
            hook_output["hookSpecificOutput"]["hookEventName"],
            "PreToolUse",
        )
        self.assertEqual(
            hook_output["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )
        # Codex は deny に非空の permissionDecisionReason を要求する
        # （codex-rs/hooks/src/engine/output_parser.rs）。
        self.assertTrue(
            hook_output["hookSpecificOutput"]["permissionDecisionReason"].strip()
        )

    def assert_allowed(self, hook_output):
        self.assertIsNone(hook_output)

    def test_issue_implementer_denies_direct_merge_forms(self):
        commands = [
            "git merge feature",
            "rtk git merge feature",
            "GIT_PAGER=cat git merge feature",
            "echo hi\ngit merge feature",
            "(git merge feature)",
            "echo $(git merge feature)",
            "echo `git merge feature`",
            "eval 'git merge feature'",
            "bash -c 'git merge feature'",
            "python3 -c \"import os; os.system('git merge feature')\"",
            "gh pr merge 123",
            "gh --repo hiratashinnya/review-system pr merge 123",
            "gh -R hiratashinnya/review-system pr merge 123",
            "rtk gh --repo hiratashinnya/review-system pr merge 123",
            "rtk gh pr merge 123",
            "git -c alias.m=merge m feature",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(run_gate(payload("issue-implementer", command)))

    def test_issue_implementer_allows_non_merge_git_commands(self):
        commands = [
            "git merge-base main HEAD",
            "git merge-tree HEAD main feature",
            "git merge --abort",
            "git merge --quit",
            "git push origin HEAD",
            "gh pr create --fill",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assert_allowed(run_gate(payload("issue-implementer", command)))

    def test_pr_reviewer_denies_push_but_allows_merge(self):
        self.assert_denied(run_gate(payload("pr-reviewer", "git push origin HEAD")))
        self.assert_denied(run_gate(payload("pr-reviewer", "rtk git push origin HEAD")))
        self.assert_allowed(run_gate(payload("pr-reviewer", "gh pr merge 123")))

    def test_missing_or_unrecognized_agent_is_out_of_scope(self):
        # Claude 版と同じオーナー判断：agent_type が issue-implementer/pr-reviewer のいずれでも
        # ない場合（欠如を含む・main context 自身がこれに該当）は対象外＝常に許可。
        self.assert_allowed(run_gate(payload(None, "git merge feature")))
        self.assert_allowed(run_gate(payload(None, "git push origin HEAD")))
        self.assert_allowed(run_gate(payload(None, "git status")))
        self.assert_allowed(run_gate(payload("general-purpose", "git merge feature")))
        self.assert_allowed(run_gate(payload("general-purpose", "git push origin HEAD")))

    def test_non_shell_tool_is_out_of_scope(self):
        # git/gh は Bash ツール経由でのみ走る。非シェルツール（apply_patch 等）は対象外。
        self.assert_allowed(
            run_gate(payload("issue-implementer", "git merge feature", tool_name="apply_patch"))
        )
        self.assert_allowed(
            run_gate(payload("pr-reviewer", "git push origin HEAD", tool_name="Write"))
        )

    def test_shell_tool_aliases_are_inspected(self):
        # canonical 名 "Bash" 以外の代表的シェル系エイリアスでも検査する（将来の改名への保険）。
        for tool_name in ("shell", "local_shell", "unified_exec", "exec_command"):
            with self.subTest(tool_name=tool_name):
                self.assert_denied(
                    run_gate(payload("issue-implementer", "git merge feature", tool_name=tool_name))
                )

    def test_missing_command_denies_because_command_cannot_be_inspected(self):
        self.assert_denied(
            run_gate({"agent_type": "issue-implementer", "tool_name": "Bash", "tool_input": {}})
        )
        self.assert_denied(run_gate({"agent_type": "issue-implementer", "tool_name": "Bash"}))

    def test_invalid_json_denies(self):
        result = subprocess.run(
            [str(HOOK)],
            input="not-json",
            text=True,
            capture_output=True,
            check=True,
        )
        output = json.loads(result.stdout)
        self.assertEqual(
            output["hookSpecificOutput"]["permissionDecision"], "deny"
        )

    def test_subagent_type_fallback_is_supported(self):
        self.assert_denied(
            run_gate(
                {
                    "subagent_type": "issue-implementer",
                    "tool_name": "Bash",
                    "tool_input": {"command": "git merge feature"},
                }
            )
        )

    def test_debug_payload_redacts_sensitive_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "payload.log"
            output = run_gate(
                {
                    "agent_type": "issue-implementer",
                    "tool_name": "Bash",
                    "tool_input": {"command": "git merge feature"},
                    "api_token": "secret-value",
                },
                env={"AGENT_COMMAND_GATE_DEBUG_PAYLOAD": str(log_path)},
            )
            self.assert_denied(output)
            record = json.loads(log_path.read_text().strip())
            self.assertEqual(record["payload"]["api_token"], "<redacted>")
            self.assertEqual(record["decision"], "deny")


if __name__ == "__main__":
    unittest.main()
