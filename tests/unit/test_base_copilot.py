"""Real Git coverage of explicitly authorized Copilot base workflows (#629)."""

import unittest
import subprocess
from unittest import mock
from gitgate import base_cli
from gitgate.base_copilot import REGISTER
from gitgate.base_error import BaseIntegrationError
from tests.unit import test_base_integration as fixtures

git = fixtures.git
from tests.unit.test_agent_command_gate import run_gate as claude_gate, payload
from tests.unit.test_codex_agent_command_gate import run_gate as codex_gate


class CopilotIntegrationTests(unittest.TestCase):
    entry = fixtures.IntegrationTests.entry
    mutate = fixtures.IntegrationTests.mutate
    execute = fixtures.IntegrationTests.execute
    start = fixtures.IntegrationTests.start
    resolve = fixtures.IntegrationTests.resolve
    continue_ = fixtures.IntegrationTests.continue_

    def setUp(self):
        fixtures.IntegrationTests.setUp(self)
        # Normal PR-branch clone: no Claude hook or linked-worktree identity.
        clone = self.main.parent / "copilot"
        git(self.main, "clone", "--branch", "fix", str(self.remote), str(clone))
        git(clone, "remote", "set-url", "origin", "https://github.com/example/repo.git")
        git(clone, "config", "user.name", "Copilot acceptance")
        git(clone, "config", "user.email", "copilot@example.invalid")
        self.work = self.main = clone
        self.entry_id = self.execute(REGISTER, self.start_args)["session"]

    def test_conflict_continue_two_parents(self):
        fixtures.IntegrationTests.test_conflict_edit_tests_commit_two_parents(self)

    def test_nonconflicting_merge(self):
        # Create a nonconflicting exact base, then replace the terminal authorization.
        base_work = self.main.parent / "base"
        git(self.main, "clone", "--branch", "main", str(self.remote), str(base_work))
        git(base_work, "config", "user.name", "Base acceptance")
        git(base_work, "config", "user.email", "base@example.invalid")
        git(base_work, "reset", "--hard", "HEAD~1")
        (base_work / "added.txt").write_text("base addition\n")
        git(base_work, "add", "added.txt")
        git(base_work, "commit", "-m", "nonconflicting base")
        self.base = git(base_work, "rev-parse", "HEAD")
        git(base_work, "push", "--force", "origin", "main")
        self.api.pull["base"]["sha"] = self.start_args[-1] = self.base
        old = self.entry_id
        self.entry_id = self.execute(REGISTER, self.start_args)["session"]
        self.assertNotEqual(old, self.entry_id)
        self.assertEqual(self.start()["status"], "ready")
        self.assertEqual(self.continue_()["parents"], [self.head, self.base])

    def test_abort_preserves_edits_without_api(self):
        fixtures.IntegrationTests.test_abort_saves_resolution_unrelated_and_untracked_without_api(self)

    def test_pending_publish_and_reregistration_denied(self):
        self.start()
        for verb in ("commit", "push"):
            with self.assertRaisesRegex(BaseIntegrationError, "COMMIT_PUSH_DENIED"):
                base_cli.refuse_pending_publish(self.work)
        with self.assertRaises(BaseIntegrationError):
            self.execute(REGISTER, self.start_args)
        self.assertEqual(self.entry()["status"], "running")

    def test_request_and_branch_drift_denied(self):
        for index, value in ((1, "different/repo"), (3, "10"), (5, "a" * 40), (7, "b" * 40)):
            args = self.start_args.copy()
            args[index] = value
            with self.assertRaisesRegex(BaseIntegrationError, "REQUEST_MISMATCH"):
                self.execute("integrate-base", args)
        git(self.work, "switch", "-c", "different")
        with self.assertRaisesRegex(BaseIntegrationError, "BINDING_MISMATCH"):
            self.start()

    def test_authorization_cannot_switch_pending_session(self):
        self.start()
        self.resolve()
        self.mutate(lambda entry: entry.update(agent_id="different"))
        with self.assertRaisesRegex(BaseIntegrationError, "BINDING_MISMATCH"):
            self.continue_()
        with self.assertRaisesRegex(BaseIntegrationError, "BINDING_MISMATCH"):
            self.execute("integrate-base-abort")

    def test_authorization_request_cannot_change_pending_operation(self):
        self.start()
        self.mutate(lambda entry: entry["base_authorization"]["request"].update(pr=10))
        with self.assertRaisesRegex(BaseIntegrationError, "REQUEST_MISMATCH"):
            self.execute("integrate-base-abort")

    def test_worktree_fake_state_and_self_platform_are_denied(self):
        self.mutate(lambda entry: entry.pop("base_authorization"))
        with self.assertRaisesRegex(BaseIntegrationError, "AUTHORIZATION_INVALID"):
            self.start()

    def test_index_and_test_content_cas_preserved(self):
        fixtures.IntegrationTests.test_test_side_effect_cas_is_rejected(self)

    def test_unrelated_edits_and_markers_preserved(self):
        fixtures.IntegrationTests.test_unresolved_markers_and_unrelated_edits_stop(self)

    def test_failed_tests_preserve_pending(self):
        fixtures.IntegrationTests.test_test_failure_preserves_pending_state(self)

    def test_registration_requires_live_pr_and_clean_exact_head(self):
        self.api.pull["state"] = "closed"
        with self.assertRaisesRegex(BaseIntegrationError, "PR_NOT_OPEN"):
            self.execute(REGISTER, self.start_args)
        self.api.pull["state"] = "open"
        args = self.start_args.copy()
        args[5] = "a" * 40
        with self.assertRaisesRegex(BaseIntegrationError, "HEAD_OID_MISMATCH"):
            self.execute(REGISTER, args)

    def authorize_test_module(self, content):
        (self.work / "tests/test_acceptance.py").write_text(content)
        git(self.work, "commit", "-am", "test module fixture")
        self.head = git(self.work, "rev-parse", "HEAD")
        git(self.work, "push", str(self.remote), "fix")
        self.api.pull["head"]["sha"] = self.start_args[5] = self.head
        self.entry_id = self.execute(REGISTER, self.start_args)["session"]

    def test_real_zero_test_run_does_not_commit(self):
        self.authorize_test_module("# deliberately no unittest cases\n")
        self.start()
        self.resolve()
        original_run = subprocess.run
        def zero_success(command, **kwargs):
            result = original_run(command, **kwargs)
            if "unittest" in command:
                self.assertIn("Ran 0 tests", result.stderr)
                result.returncode = 0  # Older Python reports success for a zero-case run.
            return result
        with mock.patch("gitgate.base_tests.subprocess.run", side_effect=zero_success):
            with self.assertRaisesRegex(BaseIntegrationError, "TEST_FAILED"):
                self.continue_()
        self.assertEqual(git(self.work, "rev-parse", "HEAD"), self.head)
        self.assertEqual(self.entry()["base_integrations"][-1]["tests"]["exit_code"], 0)

    def test_real_failing_test_run_does_not_commit(self):
        self.authorize_test_module("import unittest\nclass Failure(unittest.TestCase):\n"
                                   " def test_failure(self): self.fail('expected failure')\n")
        self.start()
        self.resolve()
        with self.assertRaisesRegex(BaseIntegrationError, "TEST_FAILED"):
            self.continue_()
        self.assertEqual(git(self.work, "rev-parse", "HEAD"), self.head)
        self.assertNotEqual(self.entry()["base_integrations"][-1]["tests"]["exit_code"], 0)

    def test_protected_incoming_guidance_rejected(self):
        with mock.patch("gitgate.base_protection.protected", return_value=True):
            with self.assertRaisesRegex(BaseIntegrationError, "PROTECTED_INCOMING"):
                self.start()


class RegistrationHostGateTests(unittest.TestCase):
    def test_registration_denied_for_every_host_role(self):
        for gate in (claude_gate, codex_gate):
            for role in (None, "main", "issue-fixer", "issue-implementer", "pr-reviewer"):
                for form in ("python3 -m gitgate", "python3 -Bmgitgate"):
                    result = gate({**payload(role, form + " " + REGISTER), "tool_name": "Bash"})
                    self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
                    self.assertIn("unavailable on this host", result["hookSpecificOutput"]["permissionDecisionReason"])
