"""PR base 取り込み verb のロール境界は呼び出し元 command gate が持つ（Issue #706）。

Issue-pipeline 内では issue-fixer だけに許可し、pipeline 外（主文脈・general-purpose 等）は
誤拒否しない。PR merge / auto-merge / raw git merge の全ロール拒否は従来どおり。
"""

import unittest

from issue_start.gated_roles import GATED_ROLES
from tests.unit.test_agent_command_gate import run_gate as claude_gate, payload
from tests.unit.test_codex_agent_command_gate import run_gate as codex_gate

VERBS = ("integrate-base", "integrate-base-continue", "integrate-base-abort")
FORMS = ("python3 -m gitgate", "python3 -B -m gitgate", "python3 -I -B -m gitgate",
         "python3 -W ignore -X dev -m gitgate", "python3 -BWignore -Xdev -m gitgate",
         "python3 -Bm gitgate", "python3 -Bmgitgate", "python3 -mgitgate",
         "python3 -Rmgitgate.__main__", "python3 --check-hash-based-pycs always -m gitgate",
         "env PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m gitgate",
         "true;python3 -B -m gitgate")
OUTSIDE_PIPELINE = (None, "missing", "general-purpose", "spec-author", "Explore")


def invocation(role, command):
    result = {**payload(role, command), "tool_name": "Bash"}
    if role == "missing":
        result.pop("agent_type")
    return result


class BaseIntegrationGateTests(unittest.TestCase):
    def test_pipeline_roles_other_than_fixer_are_denied(self):
        for gate in (claude_gate, codex_gate):
            for role in sorted(GATED_ROLES - {"issue-fixer"}):
                for form in FORMS:
                    for verb in VERBS:
                        with self.subTest(gate=gate.__module__, role=role, form=form, verb=verb):
                            decision = gate(invocation(role, f"{form} {verb}"))
                            output = decision["hookSpecificOutput"]
                            self.assertEqual(output["permissionDecision"], "deny")
                            self.assertIn("restricted to issue-fixer",
                                          output["permissionDecisionReason"])

    def test_fixer_and_callers_outside_pipeline_are_allowed(self):
        for gate in (claude_gate, codex_gate):
            for role in ("issue-fixer",) + OUTSIDE_PIPELINE:
                for verb in VERBS:
                    with self.subTest(gate=gate.__module__, role=role, verb=verb):
                        self.assertIsNone(gate(invocation(role, "python3 -m gitgate " + verb)))

    def test_read_only_mentions_are_not_integration_invocations(self):
        for gate in (claude_gate, codex_gate):
            self.assertIsNone(gate(invocation("issue-implementer",
                                              "git log --grep integrate-base")))

    def test_pr_merge_auto_merge_and_raw_merge_stay_denied_for_every_role(self):
        commands = ("git merge origin/main", "gh pr merge 9", "gh pr merge 9 --auto",
                    "rtk git merge origin/main",
                    "gh api repos/example/repo/pulls/9/merge -X PUT")
        for gate in (claude_gate, codex_gate):
            for role in ("issue-fixer", "issue-implementer", "pr-reviewer") + OUTSIDE_PIPELINE:
                for command in commands:
                    with self.subTest(gate=gate.__module__, role=role, command=command):
                        result = gate(invocation(role, command))
                        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"],
                                         "deny")


if __name__ == "__main__":
    unittest.main()
