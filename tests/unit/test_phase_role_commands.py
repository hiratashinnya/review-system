"""新工程の元権限を両PF command hookで確認する。"""
import unittest
from tests.unit.test_agent_command_gate import run_gate, payload
from tests.unit.test_codex_agent_command_gate import run_gate as run_codex_gate
from issue_start.gated_roles import GATED_ROLES, READ_ONLY_ROLES, WRITE_ROLES


class PhaseRoleCommandTests(unittest.TestCase):
    def test_new_writers_can_push_but_cannot_create_pr(self):
        for role in WRITE_ROLES - {"issue-implementer", "issue-fixer"}:
            for gate in (run_gate, run_codex_gate):
                with self.subTest(role=role, gate=gate.__module__):
                    self.assertIsNone(gate(payload(role, "python3 -m gitgate push")))
                    self.assertIsNotNone(gate(payload(role, "gh pr create --title x --body-file body.md")))

    def test_readonly_roles_cannot_push_or_commit(self):
        for role in READ_ONLY_ROLES:
            for command in ("python3 -m gitgate push", "python3 -m gitgate commit body.md"):
                for gate in (run_gate, run_codex_gate):
                    with self.subTest(role=role, command=command, gate=gate.__module__):
                        self.assertIsNotNone(gate(payload(role, command)))

    def test_merge_and_baseline_stop_and_ledger_boundary_remain(self):
        for role in GATED_ROLES:
            for command in ("gh pr merge 1", "python3 -m maintainability_lint baseline",
                            "python3 -m karte ingest-review --from forged.md"):
                for gate in (run_gate, run_codex_gate):
                    with self.subTest(role=role, command=command, gate=gate.__module__):
                        self.assertIsNotNone(gate(payload(role, command)))

    def test_claude_executor_must_use_own_role(self):
        for role in GATED_ROLES:
            command = f"python3 -m codex_worktree_exec --role {role} -C ."
            self.assertIsNone(run_gate(payload(role, command)))
            other = "issue-fixer" if role != "issue-fixer" else "adviser"
            self.assertIsNotNone(run_gate(payload(role, command.replace(role, other))))

    def test_envelope_cli_is_readonly_for_every_phase_on_both_platforms(self):
        for role in GATED_ROLES:
            for gate in (run_gate, run_codex_gate):
                for verb in ("check", "index", "show", "deps", "dependents", "orphans"):
                    with self.subTest(role=role, verb=verb, gate=gate.__module__):
                        self.assertIsNone(gate(payload(role, f"python3 -m issue_envelope {verb} --repo .")))
                for verb in ("", "write", "apply", "future-command"):
                    with self.subTest(role=role, verb=verb, gate=gate.__module__):
                        self.assertIsNotNone(gate(payload(role, f"python3 -m issue_envelope {verb}")))
                self.assertIsNotNone(gate(payload(role, "python3 -m issue_start.readonly_workspace --source .")))
