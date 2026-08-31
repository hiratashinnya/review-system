"""Issue #452: Codex durable workspace binding の unit / 実 git integration。"""

import io
import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
import unittest
from unittest.mock import patch

from issue_start import worktree_ledger
from issue_start.codex_binding import (
    CodexBindingError,
    bind_agent_identity,
    collect_binding,
    inspect_git_facts,
    prepare_binding,
    release_binding,
    run_hook,
    validate_spawn_binding,
    verify_command_binding,
)
from issue_start.gate import IssueStartError, parse_dispatch_payload
from issue_start.hook import run as run_issue_start_hook


NOW = datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)
REPOSITORY = "example/repo"


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=str(cwd), text=True, capture_output=True, check=True
    ).stdout.strip()


class RealGitBindingTests(unittest.TestCase):
    """実 worktree で origin/branch/OID/registration と lifecycle を通す。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.main = Path(self.temp.name) / "main"
        self.main.mkdir()
        git(self.main, "init", "-b", "main")
        git(self.main, "config", "user.email", "test@example.invalid")
        git(self.main, "config", "user.name", "Binding Test")
        git(self.main, "remote", "add", "origin", "https://github.com/example/repo.git")
        (self.main / "seed.txt").write_text("seed\n", encoding="utf-8")
        git(self.main, "add", "seed.txt")
        git(self.main, "commit", "-m", "seed")
        self.workspace = self.main / ".worktrees" / "issue-10"
        self.workspace.parent.mkdir()
        git(self.main, "worktree", "add", "-b", "codex/issue-10", str(self.workspace), "HEAD")
        self.oid = git(self.workspace, "rev-parse", "HEAD")
        self.task_key = "issue_10"
        self.handoff = "tmp/_handoff/issue-implementer--issue-10.yaml"

    def prepare(self, **overrides):
        values = {
            "issue": 10,
            "round_number": 1,
            "repository": REPOSITORY,
            "workspace": self.workspace,
            "branch_name": "codex/issue-10",
            "expected_oid": self.oid,
            "handoff_path": self.handoff,
            "role": "issue-implementer",
            "task_key": self.task_key,
            "now": NOW,
        }
        values.update(overrides)
        return prepare_binding(**values)

    def validate(self, **overrides):
        values = {
            "repo_root": self.workspace,
            "role": "issue-implementer",
            "task_key": self.task_key,
            "now": NOW + timedelta(seconds=1),
        }
        values.update(overrides)
        return validate_spawn_binding(**values)

    def bind(self, agent_id="agent-owner", **overrides):
        values = {
            "repo_root": self.workspace,
            "workspace": self.workspace,
            "role": "issue-implementer",
            "task_key": self.task_key,
            "agent_id": agent_id,
            "now": NOW + timedelta(seconds=1),
        }
        values.update(overrides)
        return bind_agent_identity(**values)

    def issue_start_payload(self):
        return {
            "cwd": str(self.main),
            "tool_name": "collaborationspawn_agent",
            "tool_input": {
                "agent_type": "issue-implementer",
                "task_name": self.task_key,
                "message": "ENC[not-a-binding]",
            },
        }

    def run_issue_start(self, evidence):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.gate._require_transport_available"), patch(
            "issue_start.hook.resolve_github_token", return_value=None
        ), patch("issue_start.hook.evaluate_issue_start", return_value=evidence) as evaluate:
            rc = run_issue_start_hook(
                stdin=io.StringIO(json.dumps(self.issue_start_payload())),
                stdout=stdout,
                stderr=stderr,
                cwd=self.main,
                ledger_root=self.main,
                now=NOW + timedelta(seconds=1),
            )
        self.assertEqual(rc, 0)
        return stdout.getvalue(), stderr.getvalue(), evaluate

    def assert_prepared_open(self):
        entry = next(
            item for item in worktree_ledger.read_ledger(self.main)["entries"]
            if item.get("task_key") == self.task_key
        )
        self.assertEqual(entry["status"], "open")
        self.assertIsNone(entry["agent_id"])

    def test_prepare_validate_bind_verify_collect_release_lifecycle(self):
        prepared = self.prepare()
        self.assertEqual(prepared["status"], "open")
        self.assertEqual(prepared["platform"], "codex")
        self.assertEqual(prepared["worktree_path"], ".worktrees/issue-10")
        validated = self.validate()
        self.assertEqual(validated["status"], "open", "spawn 前 validation は consume しない")
        self.assertIsNone(validated["agent_id"])
        running = self.bind()
        self.assertEqual(running["status"], "running")
        self.assertEqual(running["agent_id"], "agent-owner")
        self.assertIsNone(running["consumed_at"])
        self.assertEqual(running["bound_at"], "2026-08-26T09:00:01Z")
        verified = verify_command_binding(
            repo_root=self.workspace,
            workspace=self.workspace,
            role="issue-implementer",
            agent_id="agent-owner",
        )
        self.assertEqual(verified["task_key"], self.task_key)

        # agent 自身の正当な commit 後は expected OID の descendant として継続できる。
        (self.workspace / "change.txt").write_text("change\n", encoding="utf-8")
        git(self.workspace, "add", "change.txt")
        git(self.workspace, "commit", "-m", "descendant")
        verify_command_binding(
            repo_root=self.workspace,
            workspace=self.workspace,
            role="issue-implementer",
            agent_id="agent-owner",
        )

        source = self.workspace / self.handoff
        source.parent.mkdir(parents=True)
        source.write_text("agent: issue-implementer\nstatus: pr_opened\n", encoding="utf-8")
        collected = collect_binding(
            task_key=self.task_key, repo_root=self.workspace, now=NOW + timedelta(seconds=2)
        )
        self.assertEqual(collected["status"], "collected")
        self.assertEqual(collected["collected_to"], self.handoff)
        self.assertEqual((self.main / self.handoff).read_text(encoding="utf-8"), source.read_text())
        released = release_binding(
            task_key=self.task_key, repo_root=self.workspace, now=NOW + timedelta(seconds=3)
        )
        self.assertEqual(released["status"], "released")
        self.assertEqual(released["collected_to"], self.handoff)
        current_oid = git(self.workspace, "rev-parse", "HEAD")
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_TASK_REUSED"):
            self.prepare(now=NOW + timedelta(seconds=4), expected_oid=current_oid)

    def test_running_task_reuse_and_expired_validate_fail_close(self):
        self.prepare()
        self.bind()
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_TASK_REUSED"):
            self.validate(now=NOW + timedelta(seconds=2))

        # 別 task の prepare は許可されるが、期限後の consume は拒否し open のまま残す。
        second = self.main / ".worktrees" / "issue-11"
        git(self.main, "worktree", "add", "-b", "codex/issue-11", str(second), self.oid)
        prepare_binding(
            issue=11, round_number=1, repository=REPOSITORY, workspace=second,
            branch_name="codex/issue-11", expected_oid=self.oid,
            handoff_path="tmp/_handoff/issue-implementer--issue-11.yaml",
            role="issue-implementer", task_key="issue_11", now=NOW, ttl_seconds=30,
        )
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_EXPIRED"):
            validate_spawn_binding(
                repo_root=second, role="issue-implementer",
                task_key="issue_11", now=NOW + timedelta(seconds=31),
            )
        entries = worktree_ledger.read_ledger(self.main)["entries"]
        expired = next(item for item in entries if item.get("task_key") == "issue_11")
        self.assertEqual(expired["status"], "open")

    def test_expired_open_can_be_atomically_refreshed_with_audit_history(self):
        prepared = self.prepare(ttl_seconds=30)
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_EXPIRED"):
            self.validate(now=NOW + timedelta(seconds=31))

        refreshed = self.prepare(now=NOW + timedelta(seconds=31), ttl_seconds=30)
        self.assertEqual(refreshed["entry_id"], prepared["entry_id"])
        self.assertEqual(refreshed["status"], "open")
        self.assertEqual(refreshed["prepared_at"], "2026-08-26T09:00:31Z")
        self.assertEqual(refreshed["expires_at"], "2026-08-26T09:01:01Z")
        self.assertEqual(refreshed["refresh_history"], [{
            "refreshed_at": "2026-08-26T09:00:31Z",
            "previous_prepared_at": "2026-08-26T09:00:00Z",
            "previous_expires_at": "2026-08-26T09:00:30Z",
            "new_expires_at": "2026-08-26T09:01:01Z",
        }])
        self.assertIn("expired open binding refreshed", refreshed["notes"][-1]["note"])
        validated = self.validate(now=NOW + timedelta(seconds=32))
        self.assertEqual(validated["entry_id"], prepared["entry_id"])

    def test_expired_open_refresh_rejects_different_identity_and_concurrent_reuse(self):
        self.prepare(ttl_seconds=30)
        with self.assertRaisesRegex(
            CodexBindingError, "CODEX_BINDING_REFRESH_IDENTITY_MISMATCH"
        ):
            self.prepare(
                now=NOW + timedelta(seconds=31),
                ttl_seconds=30,
                handoff_path="tmp/_handoff/issue-implementer--issue-10-retry.yaml",
            )

        barrier = Barrier(2)

        def concurrent_prepare():
            barrier.wait()
            try:
                return "OK", self.prepare(now=NOW + timedelta(seconds=31), ttl_seconds=30)
            except CodexBindingError as exc:
                return exc.reason, None

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: concurrent_prepare(), range(2)))
        self.assertEqual(
            sorted(reason for reason, _entry in results),
            ["CODEX_BINDING_TASK_REUSED", "OK"],
        )
        refreshed = next(entry for reason, entry in results if reason == "OK")
        entries = [
            item for item in worktree_ledger.read_ledger(self.main)["entries"]
            if item.get("task_key") == self.task_key
        ]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["entry_id"], refreshed["entry_id"])

    def test_blocker_and_api_denies_leave_binding_retryable(self):
        self.prepare()
        for result, reason in (("BLOCK", "OPEN_BLOCKER"), ("ERROR", "API_UNAVAILABLE")):
            with self.subTest(result=result):
                stdout, _stderr, evaluate = self.run_issue_start({
                    "schema_version": "issue-start-evidence/1",
                    "policy_version": "issue-start/1.0",
                    "result": result,
                    "exit_code": 10 if result == "BLOCK" else 20,
                    "reason": reason,
                    "blockers": [],
                })
                self.assertEqual(
                    json.loads(stdout)["hookSpecificOutput"]["permissionDecision"], "deny"
                )
                evaluate.assert_called_once()
                self.assert_prepared_open()

    def test_router_failure_after_allow_can_retry_the_same_open_binding(self):
        self.prepare()
        allow = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
            "blockers": [],
        }
        for attempt in (1, 2):
            with self.subTest(attempt=attempt):
                stdout, stderr, evaluate = self.run_issue_start(allow)
                self.assertEqual(stdout, "")
                self.assertIn("ISSUE_START_ALLOWED", stderr)
                evaluate.assert_called_once()
                self.assert_prepared_open()

    def test_residue_deny_leaves_binding_retryable(self):
        self.prepare()
        residue_path = self.main / ".claude" / "worktrees" / "agent-residue"
        residue_path.mkdir(parents=True)
        worktree_ledger.open_entry(
            self.main,
            issue=99,
            agent_type="issue-implementer",
            round=None,
            branch_name=None,
            handoff_path=None,
            now=NOW,
        )
        residue_id = worktree_ledger.bind_agent(
            self.main,
            agent_type="issue-implementer",
            agent_id="residue",
            worktree_path=".claude/worktrees/agent-residue",
        )
        worktree_ledger.mark(self.main, residue_id, "stopped", now=NOW)
        stdout, _stderr, evaluate = self.run_issue_start({
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
            "blockers": [],
        })
        self.assertIn("ISSUE_START_WORKTREE_RESIDUE", stdout)
        evaluate.assert_not_called()
        self.assert_prepared_open()

    def test_wrong_cwd_origin_branch_and_stale_oid_fail_close(self):
        self.prepare()
        self.bind()
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_ACTIVE_MISSING"):
            verify_command_binding(
                repo_root=self.workspace, workspace=self.main, role="issue-implementer",
                agent_id="agent-owner",
            )

        git(self.workspace, "remote", "set-url", "origin", "https://github.com/evil/repo.git")
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_ORIGIN_MISMATCH"):
            verify_command_binding(
                repo_root=self.workspace, workspace=self.workspace, role="issue-implementer",
                agent_id="agent-owner",
            )
        git(self.workspace, "remote", "set-url", "origin", "https://github.com/example/repo.git")

        git(self.workspace, "switch", "-c", "codex/wrong-branch")
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_BRANCH_MISMATCH"):
            verify_command_binding(
                repo_root=self.workspace, workspace=self.workspace, role="issue-implementer",
                agent_id="agent-owner",
            )
        git(self.workspace, "switch", "codex/issue-10")

        # amend は expected OID と親子関係のない HEAD を作る。
        (self.workspace / "seed.txt").write_text("rewritten\n", encoding="utf-8")
        git(self.workspace, "add", "seed.txt")
        git(self.workspace, "commit", "--amend", "-m", "rewritten root")
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_STALE_OID"):
            verify_command_binding(
                repo_root=self.workspace, workspace=self.workspace, role="issue-implementer",
                agent_id="agent-owner",
            )

    def test_actual_agent_identity_is_bound_once_and_stale_thread_is_denied(self):
        self.prepare()
        owner = self.bind("agent-owner")
        self.assertEqual(self.bind("agent-owner")["entry_id"], owner["entry_id"])
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_AGENT_MISMATCH"):
            self.bind("agent-stale")
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_AGENT_MISMATCH"):
            verify_command_binding(
                repo_root=self.workspace,
                workspace=self.workspace,
                role="issue-implementer",
                agent_id="agent-stale",
            )
        verified = verify_command_binding(
            repo_root=self.workspace,
            workspace=self.workspace,
            role="issue-implementer",
            agent_id="agent-owner",
        )
        self.assertEqual(verified["agent_id"], "agent-owner")

    def test_missing_handoff_and_task_role_round_mismatch_fail_before_write(self):
        bad = (
            ({"handoff_path": ""}, "CODEX_BINDING_HANDOFF_MISSING"),
            ({"task_key": "issue_11"}, "CODEX_BINDING_TASK_KEY_MISMATCH"),
            ({"round_number": 2}, "CODEX_BINDING_ROUND_INVALID"),
            ({"role": "issue-fixer"}, "CODEX_BINDING_TASK_KEY_MISMATCH"),
        )
        for override, reason in bad:
            with self.subTest(reason=reason), self.assertRaisesRegex(CodexBindingError, reason):
                self.prepare(**override)
        self.assertEqual(worktree_ledger.read_ledger(self.main)["entries"], [])

    def test_prepare_persists_only_normalized_owner_protected_paths(self):
        prepared = self.prepare(protected_paths=(".codex/agents/example.toml",))
        self.assertEqual(prepared["protected_paths"], [".codex/agents/example.toml"])
        for candidate in ("../escape", "/absolute", ".codex/../escape", "docs/not-protected"):
            with self.subTest(candidate=candidate):
                self.setUp()
                self.addCleanup(self.temp.cleanup)
                with self.assertRaisesRegex(
                    CodexBindingError, "CODEX_BINDING_PROTECTED_PATH_INVALID"
                ):
                    self.prepare(protected_paths=(candidate,))

    def test_hook_fails_closed_for_target_roles_until_transport_observations_exist(self):
        missing_stdout = io.StringIO()
        run_hook(
            stdin=io.StringIO(json.dumps({
                "agent_type": "issue-implementer", "cwd": str(self.workspace),
                "tool_name": "apply_patch", "tool_input": {},
            })),
            stdout=missing_stdout, stderr=io.StringIO(), cwd=self.workspace,
        )
        self.assertEqual(
            json.loads(missing_stdout.getvalue())["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )
        self.prepare()
        self.bind()
        stdout = io.StringIO()
        run_hook(
            stdin=io.StringIO(json.dumps({
                "agent_type": "issue-implementer", "cwd": str(self.workspace),
                "tool_name": "apply_patch", "tool_input": {},
            })),
            stdout=stdout, stderr=io.StringIO(), cwd=self.workspace,
        )
        decision = json.loads(stdout.getvalue())["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("CODEX_BINDING_TRANSPORT_UNAVAILABLE", decision["permissionDecisionReason"])
        unmanaged = io.StringIO()
        run_hook(
            stdin=io.StringIO(json.dumps({"agent_type": "pr-reviewer"})),
            stdout=unmanaged, stderr=io.StringIO(), cwd=self.workspace,
        )
        self.assertEqual(unmanaged.getvalue(), "")

    def test_hook_never_treats_turn_cwd_as_the_effective_tool_workspace(self):
        self.prepare()
        self.bind()
        other = self.main / ".worktrees" / "other"
        for payload_cwd in (self.main, self.workspace, other):
            stdout = io.StringIO()
            run_hook(
                stdin=io.StringIO(json.dumps({
                    "agent_type": "issue-implementer",
                    "cwd": str(payload_cwd),
                    "tool_name": "Bash",
                    "tool_input": {"command": "git status"},
                })),
                stdout=stdout,
                stderr=io.StringIO(),
                cwd=self.workspace,
            )
            with self.subTest(payload_cwd=payload_cwd):
                decision = json.loads(stdout.getvalue())["hookSpecificOutput"]
                self.assertEqual(decision["permissionDecision"], "deny")
                self.assertIn(
                    "CODEX_BINDING_TRANSPORT_UNAVAILABLE",
                    decision["permissionDecisionReason"],
                )

    def test_codex_fixer_transport_is_denied_without_consuming_the_open_binding(self):
        prepare_binding(
            issue=10, round_number=2, repository=REPOSITORY, workspace=self.workspace,
            branch_name="codex/issue-10", expected_oid=self.oid,
            handoff_path="tmp/_handoff/issue-fixer--issue-10-r2.yaml",
            role="issue-fixer", task_key="issue_10_fix_r2", now=NOW,
        )
        payload = {
            "cwd": str(self.main),
            "tool_name": "collaborationspawn_agent",
            "tool_input": {
                "agent_type": "issue-fixer",
                "task_name": "issue_10_fix_r2",
                "message": "ENC[not-a-binding]",
            },
        }
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_TRANSPORT_UNAVAILABLE"):
            parse_dispatch_payload(payload, cwd=self.main, now=NOW + timedelta(seconds=1))
        entry = next(
            item for item in worktree_ledger.read_ledger(self.main)["entries"]
            if item.get("task_key") == "issue_10_fix_r2"
        )
        self.assertEqual(entry["status"], "open")
        self.assertIsNone(entry["agent_id"])


class UnregisteredWorktreeTests(unittest.TestCase):
    def test_linked_layout_missing_from_git_worktree_list_is_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            main = Path(temp) / "main"
            workspace = main / ".worktrees" / "orphan"
            gitdir = main / ".git" / "worktrees" / "orphan"
            gitdir.mkdir(parents=True)
            workspace.mkdir(parents=True)
            (workspace / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
            (gitdir / "commondir").write_text("../..\n", encoding="utf-8")

            class Completed:
                def __init__(self, stdout):
                    self.stdout = stdout
                    self.stderr = ""
                    self.returncode = 0

            def runner(argv, **_kwargs):
                outputs = {
                    ("git", "rev-parse", "--show-toplevel"): str(workspace),
                    ("git", "worktree", "list", "--porcelain"): f"worktree {main}\n",
                }
                return Completed(outputs[tuple(argv)] + "\n")

            with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_WORKTREE_UNREGISTERED"):
                inspect_git_facts(workspace, runner=runner)


if __name__ == "__main__":
    unittest.main()
