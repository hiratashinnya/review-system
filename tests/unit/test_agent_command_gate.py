import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "agent-command-gate.sh"


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


def payload(agent_type, command):
    return {"agent_type": agent_type, "tool_input": {"command": command}}


class AgentCommandGateTests(unittest.TestCase):
    def assert_denied(self, hook_output):
        self.assertIsNotNone(hook_output)
        self.assertEqual(
            hook_output["hookSpecificOutput"]["permissionDecision"],
            "deny",
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

    def test_missing_agent_denies_restricted_command_fail_closed(self):
        self.assert_denied(run_gate({"tool_input": {"command": "git merge feature"}}))
        self.assert_denied(run_gate({"tool_input": {"command": "git push origin HEAD"}}))
        self.assert_allowed(run_gate({"tool_input": {"command": "git status"}}))

    def test_missing_command_denies_because_command_cannot_be_inspected(self):
        self.assert_denied(run_gate({"agent_type": "issue-implementer", "tool_input": {}}))
        self.assert_denied(run_gate({"agent_type": "issue-implementer"}))

    def test_subagent_type_fallback_is_supported(self):
        self.assert_denied(
            run_gate({"subagent_type": "issue-implementer", "tool_input": {"command": "git merge feature"}})
        )

    def test_debug_payload_redacts_sensitive_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "payload.log"
            output = run_gate(
                {
                    "agent_type": "issue-implementer",
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
