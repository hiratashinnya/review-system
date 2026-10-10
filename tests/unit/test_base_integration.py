"""Real Git acceptance tests for the fixer-only PR-base workflow (#594)."""

import copy
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from gitgate import base_cli, base_journal
from gitgate.base_error import BaseIntegrationError
from gitgate.base_git import git_path, output
from gitgate.base_request import parse_request
from gitgate.base_snapshot import snapshot
from issue_start import subagent_hooks, worktree_ledger
from tests.unit.test_agent_command_gate import run_gate as claude_gate, payload
from tests.unit.test_codex_agent_command_gate import run_gate as codex_gate

NOW = datetime(2026, 10, 9, tzinfo=timezone.utc)
REPOSITORY = "example/repo"


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True,
                          check=True).stdout.strip()


class PullApi:
    def __init__(self, head, base):
        self.pull = {"number": 9, "state": "open",
                     "head": {"ref": "fix", "sha": head, "repo": {"full_name": REPOSITORY}},
                     "base": {"ref": "main", "sha": base, "repo": {"full_name": REPOSITORY}}}

    def pull_request(self, repository, number):
        return copy.deepcopy(self.pull)

    def repository(self, repository):
        return {"default_branch": "main"}


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.main, self.remote = root / "main", root / "remote.git"
        self.main.mkdir()
        git(self.main, "init", "-b", "main")
        git(self.main, "config", "user.name", "Integration test")
        git(self.main, "config", "user.email", "integration@example.invalid")
        (self.main / ".gitignore").write_text("tmp/\n.claude/worktrees/\n.worktrees/\n__pycache__/\n")
        (self.main / "item.txt").write_text("seed\n")
        (self.main / "other.txt").write_text("unrelated\n")
        (self.main / "tests").mkdir()
        (self.main / "tests/__init__.py").write_text("")
        (self.main / "tests/test_acceptance.py").write_text(
            "import unittest\nfrom pathlib import Path\n"
            "class Acceptance(unittest.TestCase):\n"
            " def test_resolution(self):\n"
            "  self.assertNotIn('<<<<<<<', Path('item.txt').read_text())\n")
        git(self.main, "add", ".")
        git(self.main, "commit", "-m", "seed")
        git(root, "init", "--bare", str(self.remote))
        git(self.main, "remote", "add", "origin", "https://github.com/example/repo.git")
        git(self.main, "config", f"url.{self.remote}.insteadOf", "https://github.com/example/repo.git")
        git(self.main, "push", "origin", "main")
        git(self.main, "switch", "-c", "fix")
        (self.main / "item.txt").write_text("head\n")
        git(self.main, "commit", "-am", "head change")
        self.head = git(self.main, "rev-parse", "HEAD")
        git(self.main, "push", "-u", "origin", "fix")
        git(self.main, "switch", "main")
        (self.main / "item.txt").write_text("base\n")
        git(self.main, "commit", "-am", "base change")
        self.base = git(self.main, "rev-parse", "HEAD")
        git(self.main, "push", "origin", "main")
        self.work = self.main / ".claude/worktrees/agent-base"
        git(self.main, "worktree", "add", str(self.work), "fix")
        git(self.main, "config", "--unset", f"url.{self.remote}.insteadOf")
        actual_run = subprocess.run
        def local_transport(command, **kwargs):
            command = list(command)
            if command[0] == "git" and "origin" in command and any(
                    verb in command for verb in ("fetch", "push")):
                command[command.index("origin")] = str(self.remote)
            return actual_run(command, **kwargs)
        transport = mock.patch("gitgate.base_git.subprocess.run", side_effect=local_transport)
        transport.start()
        self.addCleanup(transport.stop)
        self.entry_id = worktree_ledger.open_entry(
            self.main, issue=10, agent_type="issue-fixer", round=1, branch_name="fix",
            handoff_path="tmp/_handoff/issue-fixer--issue-10.yaml", now=NOW)
        # Exercise the real SubagentStart transport; no role environment injection.
        subagent_hooks.run_bind(stdin=io.StringIO(json.dumps({"agent_type": "issue-fixer",
            "agent_id": "base", "cwd": str(self.work)})), stdout=io.StringIO(),
            stderr=io.StringIO(), cwd=self.work, now=NOW)
        self.assertEqual(self.entry()["status"], "running")
        self.api = PullApi(self.head, self.base)
        self.start_args = ["--repository", REPOSITORY, "--pr", "9", "--expected-head",
                           self.head, "--expected-base", self.base]

    def entry(self):
        return next(item for item in worktree_ledger.read_ledger(self.main)["entries"]
                    if item["entry_id"] == self.entry_id)

    def mutate(self, callback):
        def apply(document):
            callback(next(item for item in document["entries"] if item["entry_id"] == self.entry_id))
        worktree_ledger.update_ledger(self.main, apply)

    def execute(self, verb, args=()):
        return base_cli.execute(verb, list(args), workspace=self.work, api=self.api)

    def start(self):
        return self.execute("integrate-base", self.start_args)

    def resolve(self):
        (self.work / "item.txt").write_text("resolved\n")

    def continue_(self):
        return self.execute("integrate-base-continue", ["--test-module", "tests.test_acceptance"])

    def test_conflict_edit_tests_commit_two_parents(self):
        self.assertEqual(self.start()["status"], "conflicts")
        self.assertTrue(snapshot(self.work)["index"])
        self.assertNotEqual(git(self.work, "ls-files", "--unmerged"), "")
        self.resolve()
        result = self.continue_()
        self.assertEqual(result["parents"], [self.head, self.base])
        self.assertEqual(git(self.work, "rev-parse", "HEAD^{tree}"), result["tree"])
        self.assertEqual(self.entry()["base_integrations"][-1]["tests"]["result"], "pass")
        self.assertIsNone(base_journal.active_operation(self.entry()))

    def test_nonconflicting_merge_and_already_integrated(self):
        git(self.main, "reset", "--hard", "main~1")
        (self.main / "added.txt").write_text("new\n")
        git(self.main, "add", "added.txt")
        git(self.main, "commit", "-m", "nonconflicting base")
        self.base = git(self.main, "rev-parse", "HEAD")
        git(self.main, "push", "--force", "origin", "main")
        self.api.pull["base"]["sha"] = self.base
        self.start_args[-1] = self.base
        self.assertEqual(self.start()["status"], "ready")
        result = self.continue_()
        git(self.work, "push", "origin", "fix")
        self.api.pull["head"]["sha"] = result["oid"]
        self.start_args[-3] = result["oid"]
        self.assertEqual(self.start()["status"], "no_change")

    def test_abort_saves_resolution_unrelated_and_untracked_without_api(self):
        self.start()
        self.resolve()
        (self.work / "other.txt").write_text("valuable unrelated edit\n")
        (self.work / "untracked.txt").write_text("valuable new file\n")
        with mock.patch.object(self.api, "pull_request", side_effect=AssertionError("API must not run")):
            result = self.execute("integrate-base-abort")
        with tarfile.open(result["recovery"]) as archive:
            self.assertEqual(archive.extractfile("worktree/item.txt").read(), b"resolved\n")
            self.assertEqual(archive.extractfile("worktree/other.txt").read(), b"valuable unrelated edit\n")
            self.assertEqual(archive.extractfile("worktree/untracked.txt").read(), b"valuable new file\n")
        self.assertEqual(git(self.work, "rev-parse", "HEAD"), self.head)
        self.assertEqual((self.work / "untracked.txt").read_text(), "valuable new file\n")

    def test_dirty_and_foreign_operations_are_rejected(self):
        (self.work / "other.txt").write_text("dirty")
        with self.assertRaisesRegex(BaseIntegrationError, "NOT_CLEAN"):
            self.start()
        git(self.work, "restore", "other.txt")
        git_path(self.work, "CHERRY_PICK_HEAD").write_text(self.base)
        with self.assertRaisesRegex(BaseIntegrationError, "NOT_CLEAN"):
            self.start()

    def test_live_pr_closed_fork_and_oid_drift(self):
        variants = [("state", "closed"), ("number", 99)]
        for field, value in variants:
            original = copy.deepcopy(self.api.pull)
            self.api.pull[field] = value
            with self.assertRaises(BaseIntegrationError): self.start()
            self.api.pull = original
        self.api.pull["head"]["repo"]["full_name"] = "fork/repo"
        with self.assertRaisesRegex(BaseIntegrationError, "FORK"): self.start()
        self.api.pull["head"]["repo"]["full_name"] = REPOSITORY
        self.api.pull["base"]["sha"] = "a" * 40
        with self.assertRaisesRegex(BaseIntegrationError, "OID_MISMATCH"): self.start()
        self.assertIsNone(base_journal.active_operation(self.entry()))

    def test_api_failure_preserves_clean_tree(self):
        before = snapshot(self.work)
        with mock.patch.object(self.api, "pull_request", side_effect=RuntimeError("offline")):
            with self.assertRaises(RuntimeError): self.start()
        self.assertEqual(snapshot(self.work), before)

    def test_wrong_role_main_branch_repository_and_exact_oid(self):
        self.mutate(lambda entry: entry.update(agent_type="issue-implementer"))
        with self.assertRaisesRegex(BaseIntegrationError, "ROLE_DENIED"): self.start()
        self.mutate(lambda entry: entry.update(agent_type="issue-fixer"))
        with self.assertRaisesRegex(BaseIntegrationError, "MAIN_WORKTREE"):
            base_cli.execute("integrate-base", self.start_args, workspace=self.main, api=self.api)
        self.mutate(lambda entry: entry.update(branch_name="another"))
        with self.assertRaisesRegex(BaseIntegrationError, "BRANCH_MISMATCH"): self.start()
        self.mutate(lambda entry: entry.update(branch_name="fix"))
        args = self.start_args.copy()
        args[1] = "other/repo"
        with self.assertRaisesRegex(BaseIntegrationError, "REPOSITORY_MISMATCH"):
            self.execute("integrate-base", args)
        args = self.start_args.copy()
        args[-3] = "a" * 40
        with self.assertRaisesRegex(BaseIntegrationError, "HEAD_OID_MISMATCH"):
            self.execute("integrate-base", args)

    def test_foreign_merge_head_and_binding_are_rejected(self):
        self.start()
        before = snapshot(self.work)
        git_path(self.work, "MERGE_HEAD").write_text(self.head + "\n")
        with self.assertRaisesRegex(BaseIntegrationError, "MERGE_STATE_INVALID"):
            self.execute("integrate-base-abort")
        git_path(self.work, "MERGE_HEAD").write_text(self.base + "\n")
        self.mutate(lambda entry: entry.update(agent_id="different"))
        with self.assertRaisesRegex(BaseIntegrationError, "BINDING_MISMATCH"): self.continue_()
        self.assertEqual(snapshot(self.work), before)

    def test_ordinary_commit_push_are_fenced(self):
        self.start()
        for _verb in ("commit", "push"):
            with self.assertRaisesRegex(BaseIntegrationError, "COMMIT_PUSH_DENIED"):
                base_cli.refuse_pending_publish(self.work)

    def test_unresolved_markers_and_unrelated_edits_stop(self):
        self.start()
        with self.assertRaisesRegex(BaseIntegrationError, "MARKERS_STOP"): self.continue_()
        self.resolve()
        (self.work / "other.txt").write_text("unrelated")
        with self.assertRaisesRegex(BaseIntegrationError, "UNRELATED_EDIT"): self.continue_()
        git(self.work, "restore", "other.txt")
        (self.work / "new.txt").write_text("untracked")
        with self.assertRaisesRegex(BaseIntegrationError, "UNTRACKED_EDIT"): self.continue_()

    def test_index_tamper_rejected(self):
        self.start()
        self.resolve()
        (self.work / "other.txt").write_text("tampered")
        git(self.work, "add", "other.txt")
        with self.assertRaisesRegex(BaseIntegrationError, "NONCONFLICT_INDEX_CHANGED"): self.continue_()

    def test_test_failure_preserves_pending_state(self):
        self.start()
        self.resolve()
        with mock.patch("gitgate.base_continue.run_tests", return_value={"result": "fail"}):
            with self.assertRaisesRegex(BaseIntegrationError, "TEST_FAILED"): self.continue_()
        self.assertEqual(git(self.work, "rev-parse", "HEAD"), self.head)
        pending = base_journal.active_operation(self.entry())
        self.assertTrue(pending)
        self.assertIsNone(pending["owner_pid"])
        self.assertIsNone(pending["owner_token"])
        self.assertEqual(self.continue_()["status"], "committed")

    def assert_live_reservation(self, state):
        from gitgate.base_authority import identity
        from gitgate.base_git import process_token
        root, entry, binding = identity(self.work)
        operation = base_journal.active_operation(entry)
        self.assertEqual(operation["state"], state)
        self.assertEqual(operation["owner_pid"], os.getpid())
        self.assertEqual(operation["owner_token"], process_token())
        with self.assertRaisesRegex(BaseIntegrationError, "BASE_OPERATION_ACTIVE"):
            base_journal.reserve(root, entry, binding, snapshot(self.work), action="abort")

    def test_continue_fences_stage_test_commit_and_reentrant_abort(self):
        from gitgate import base_continue
        self.start()
        self.resolve()
        phases = []
        originals = {name: getattr(base_continue, name) for name in
                     ("stage_resolution", "run_tests", "commit_resolution")}
        def stage(*args):
            self.assert_live_reservation("reserved")
            phases.append("before_stage")
            result = originals["stage_resolution"](*args)
            self.assert_live_reservation("reserved")
            phases.append("after_stage")
            return result
        def tests(*args):
            self.assert_live_reservation("reserved")
            phases.append("testing")
            return originals["run_tests"](*args)
        def commit(*args):
            self.assert_live_reservation("testing")
            phases.append("before_commit")
            with self.assertRaisesRegex(BaseIntegrationError, "BASE_OPERATION_ACTIVE"):
                self.execute("integrate-base-abort")
            result = originals["commit_resolution"](*args)
            self.assert_live_reservation("testing")
            phases.append("after_commit")
            return result
        with mock.patch.object(base_continue, "stage_resolution", side_effect=stage), \
                mock.patch.object(base_continue, "run_tests", side_effect=tests), \
                mock.patch.object(base_continue, "commit_resolution", side_effect=commit):
            result = self.continue_()
        self.assertEqual(result["status"], "committed")
        self.assertEqual(phases, ["before_stage", "after_stage", "testing", "before_commit", "after_commit"])
        self.assertIsNone(self.entry()["base_integrations"][-1]["owner_pid"])

    def test_only_running_claude_dispatch_can_integrate(self):
        before = snapshot(self.work)
        for platform in ("codex-supervisor", "unknown", None):
            self.mutate(lambda entry: entry.update(platform=platform))
            for verb, args in (("integrate-base", self.start_args),
                               ("integrate-base-continue", []), ("integrate-base-abort", [])):
                with self.assertRaisesRegex(BaseIntegrationError, "HOST_BOUNDARY_DENIED"):
                    self.execute(verb, args)
            self.assertEqual(snapshot(self.work), before)
        self.mutate(lambda entry: entry.update(platform="claude", status="open"))
        with self.assertRaisesRegex(BaseIntegrationError, "DISPATCH_NOT_RUNNING"):
            self.start()
        self.assertEqual(snapshot(self.work), before)

    def test_shared_origin_normalization_and_invalid_remote(self):
        from branch_source.policy import BranchSourceError
        from gitgate.base_authority import identity
        for remote in ("https://github.com/example/repo.git", "git@github.com:example/repo.git",
                       "ssh://git@github.com/example/repo.git", "https://github.com/example/repo/"):
            git(self.work, "remote", "set-url", "origin", remote)
            self.assertEqual(identity(self.work)[2]["repository"], REPOSITORY)
        for remote in ("https://other.invalid/example/repo.git", "file:///example/repo.git"):
            git(self.work, "remote", "set-url", "origin", remote)
            with self.assertRaisesRegex(BranchSourceError, "REMOTE_AMBIGUOUS"):
                identity(self.work)

    def test_abort_fences_recovery_and_merge_abort(self):
        from gitgate import base_abort
        self.start()
        self.resolve()
        original_recovery, original_git = base_abort.save_recovery, base_abort.git
        observed = []
        def recover(*args):
            self.assert_live_reservation("reserved")
            observed.append("recovery")
            return original_recovery(*args)
        def abort_git(workspace, *args, **kwargs):
            if args == ("merge", "--abort"):
                self.assert_live_reservation("aborting")
                observed.append("merge-abort")
            return original_git(workspace, *args, **kwargs)
        with mock.patch.object(base_abort, "save_recovery", side_effect=recover), \
                mock.patch.object(base_abort, "git", side_effect=abort_git):
            self.assertEqual(self.execute("integrate-base-abort")["status"], "aborted")
        self.assertEqual(observed, ["recovery", "merge-abort"])
        self.assertIsNone(self.entry()["base_integrations"][-1]["owner_pid"])

    def test_abort_failure_releases_reservation_for_recovery(self):
        self.start()
        self.resolve()
        with mock.patch("gitgate.base_abort.save_recovery", side_effect=OSError("unavailable")):
            with self.assertRaisesRegex(OSError, "unavailable"):
                self.execute("integrate-base-abort")
        pending = base_journal.active_operation(self.entry())
        self.assertEqual(pending["state"], "pending")
        self.assertIsNone(pending["owner_pid"])
        self.assertIsNone(pending["owner_token"])
        self.assertEqual(self.execute("integrate-base-abort")["status"], "aborted")

    def test_test_side_effect_cas_is_rejected(self):
        self.start()
        self.resolve()
        original_run = subprocess.run
        def tamper(command, **kwargs):
            completed = original_run(command, **kwargs)
            if "unittest" in command:
                (self.work / "item.txt").write_text("after test tamper")
            return completed
        with mock.patch("gitgate.base_tests.subprocess.run", side_effect=tamper):
            with self.assertRaisesRegex(BaseIntegrationError, "TEST_CONTENT_CAS"): self.continue_()
        self.assertEqual(git(self.work, "rev-parse", "HEAD"), self.head)

    def test_protected_incoming_stops_before_merge(self):
        (self.main / ".codex").mkdir()
        (self.main / ".codex/settings.toml").write_text("changed")
        git(self.main, "add", ".codex")
        git(self.main, "commit", "-m", "contract change")
        self.base = git(self.main, "rev-parse", "HEAD")
        git(self.main, "push", "origin", "main")
        self.api.pull["base"]["sha"] = self.base
        self.start_args[-1] = self.base
        with self.assertRaisesRegex(BaseIntegrationError, "PROTECTED_INCOMING"): self.start()
        self.assertIsNone(snapshot(self.work)["merge_head"])

    def test_detached_and_same_branch_rejected(self):
        git(self.work, "switch", "--detach")
        with self.assertRaisesRegex(BaseIntegrationError, "GIT_FAILED"): self.start()
        git(self.work, "switch", "fix")
        self.api.pull["base"]["ref"] = "fix"
        with self.assertRaisesRegex(BaseIntegrationError, "HEAD_BRANCH_MISMATCH"): self.start()

    def test_option_injection_rejected(self):
        for args in (["--strategy", "ours"], ["--repository", REPOSITORY],
                     self.start_args + ["--pr", "10"]):
            with self.assertRaises(BaseIntegrationError): parse_request("integrate-base", args)
        with self.assertRaises(BaseIntegrationError):
            parse_request("integrate-base-continue", ["--test-module", "--help"])


    def test_worktree_fake_state_cannot_authorize_continue_or_abort(self):
        directory = self.work / 'tmp/_base_integration'
        directory.mkdir(parents=True)
        (directory / 'state.json').write_text(json.dumps({'role': 'issue-fixer', 'head': self.head}))
        with self.assertRaisesRegex(BaseIntegrationError, 'OPERATION_MISSING'):
            self.execute('integrate-base-abort')
        with self.assertRaisesRegex(BaseIntegrationError, 'OPERATION_MISSING'):
            self.continue_()

    def test_fetched_oid_drift_and_branch_drift_during_fetch_reject_merge(self):
        self.api.pull['base']['sha'] = self.head
        self.start_args[-1] = self.head
        with self.assertRaisesRegex(BaseIntegrationError, 'FETCH_OID_MISMATCH'):
            self.start()
        self.assertIsNone(snapshot(self.work)['merge_head'])

    def test_ledger_reservation_cas_rejects_parallel_attempt(self):
        from gitgate.base_authority import identity
        root, entry, binding = identity(self.work)
        before = snapshot(self.work)
        self.mutate(lambda item: item.update(agent_id='changed-after-inspection'))
        with self.assertRaisesRegex(BaseIntegrationError, 'LEDGER_CAS_MISMATCH'):
            base_journal.reserve(root, entry, binding, before, request={})
        self.assertIsNone(base_journal.active_operation(self.entry()))


class PlatformGateTests(unittest.TestCase):
    def test_python_option_invocations_keep_fixer_only_boundary(self):
        forms = ("python3 -B -m gitgate", "python3 -I -B -m gitgate",
                 "python3 -W ignore -X dev -m gitgate", "python3 -BWignore -Xdev -m gitgate",
                 "python3 -Bm gitgate", "python3 -Bmgitgate", "python3 -mgitgate",
                 "python3 -R -m gitgate", "python3 -Rm gitgate",
                 "python3 -Rmgitgate.__main__",
                 "python3 --check-hash-based-pycs always -m gitgate",
                 "env PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m gitgate",
                 "true;python3 -B -m gitgate")
        for gate in (claude_gate, codex_gate):
            for role in (None, "main", "unknown", "issue-implementer", "pr-reviewer", "missing"):
                for form in forms:
                    for verb in ("integrate-base", "integrate-base-continue", "integrate-base-abort"):
                        with self.subTest(gate=gate.__module__, role=role, form=form, verb=verb):
                            invocation = {**payload(role, form + " " + verb), "tool_name": "Bash"}
                            if role == "missing":
                                invocation.pop("agent_type")
                            decision = gate(invocation)
                            self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
                            self.assertIn("restricted to issue-fixer", decision["hookSpecificOutput"]["permissionDecisionReason"])

    def test_read_only_mentions_are_not_integration_invocations(self):
        for gate in (claude_gate, codex_gate):
            self.assertIsNone(gate({"tool_name": "Bash", "tool_input": {
                "command": "git log --grep integrate-base"}}))

    def test_universal_fixer_only_and_pr_merge_stays_denied(self):
        for gate in (claude_gate, codex_gate):
            for role in (None, "main", "unknown", "issue-implementer", "pr-reviewer"):
                for verb in ("integrate-base", "integrate-base-continue", "integrate-base-abort"):
                    result = gate({**payload(role, "python3 -m gitgate " + verb), "tool_name": "Bash"})
                    self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
            for verb in ("integrate-base", "integrate-base-continue", "integrate-base-abort"):
                self.assertIsNone(gate({**payload("issue-fixer", "python3 -m gitgate " + verb), "tool_name": "Bash"}))
            for role in (None, "issue-fixer", "issue-implementer", "pr-reviewer"):
                for command in ("git merge origin/main", "gh pr merge 9", "gh pr merge 9 --auto",
                                "rtk git merge origin/main", "gh api repos/example/repo/pulls/9/merge -X PUT"):
                    result = gate({**payload(role, command), "tool_name": "Bash"})
                    self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
