from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import shutil
import subprocess
import tempfile
import threading
import tomllib
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from issue_start import codex_supervisor as supervisor
from issue_start import codex_supervisor_workspace as workspace_boundary
from issue_start import worktree_ledger


NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def process_result(*, exit_code=0, timed_out=False, killed=False):
    return supervisor.ProcessResult(
        pid=123, process_start_token="456", exit_code=exit_code,
        stdout=(), stderr=(), timed_out=timed_out, killed=killed,
    )


class JsonlObserverTests(unittest.TestCase):
    def test_success_binds_one_thread_and_terminal(self):
        seen = []
        observer = supervisor.CodexJsonlObserver(seen.append)
        observer.feed('{"type":"thread.started","thread_id":"thread-1"}')
        observer.feed('{"type":"turn.completed"}')
        self.assertEqual(observer.finalize(process_result(), handoff_exists=True), "succeeded")
        self.assertEqual(seen, ["thread-1"])

    def test_process_and_thread_fail_closed(self):
        cases = [
            (["not-json"], "JSONL_MALFORMED"),
            (['{"type":"turn.completed"}'], "TERMINAL_BEFORE_THREAD"),
            (['{"type":"thread.started","thread_id":"a"}',
              '{"type":"thread.started","thread_id":"b"}'], "THREAD_DUPLICATE"),
            (['{"type":"thread.started","thread_id":"a"}',
              '{"type":"item.completed","item":{"type":"web_search_call"}}'],
             "DENIED_TOOL_EVENT"),
        ]
        for lines, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(
                supervisor.CodexSupervisorError, reason
            ):
                observer = supervisor.CodexJsonlObserver(lambda _value: None)
                for line in lines:
                    observer.feed(line)

    def test_rate_limit_is_paused_for_resume(self):
        observer = supervisor.CodexJsonlObserver(lambda _value: None)
        observer.feed('{"type":"thread.started","thread_id":"thread-1"}')
        observer.feed('{"type":"error","message":"rate limit reached"}')
        self.assertEqual(observer.finalize(process_result(exit_code=1), handoff_exists=False),
                         "paused_rate_limit")

    def test_timeout_kill_nonzero_and_missing_handoff_are_distinct(self):
        for result, handoff, reason in (
            (process_result(timed_out=True), True, "TIMEOUT"),
            (process_result(killed=True), True, "KILLED"),
            (process_result(exit_code=2), True, "EXIT_NONZERO"),
            (process_result(), False, "HANDOFF_MISSING"),
        ):
            with self.subTest(reason=reason), self.assertRaisesRegex(
                supervisor.CodexSupervisorError, reason
            ):
                observer = supervisor.CodexJsonlObserver(lambda _value: None)
                observer.feed('{"type":"thread.started","thread_id":"thread-1"}')
                observer.feed('{"type":"turn.completed"}')
                observer.finalize(result, handoff_exists=handoff)


class LaunchLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.child = self.root / ".worktrees" / "issue-452"
        self.child.mkdir(parents=True)
        (self.child / "tmp" / "_handoff").mkdir(parents=True)
        self.facts = workspace_boundary.GitFacts(
            str(self.child), str(self.root), ".worktrees/issue-452",
            "owner/repo", "codex/issue-452", "a" * 40,
        )

    def tearDown(self):
        self.temp.cleanup()

    def reserve(self, **updates):
        values = dict(
            repo_root=self.root, workspace=self.child, issue=452, round_number=1,
            repository="owner/repo", branch_name="codex/issue-452",
            expected_oid="a" * 40, role="issue-implementer", task_key="issue_452",
            handoff_path="tmp/_handoff/issue-implementer--issue-452.yaml",
            protected_paths=(), attempt_id="1" * 32, resume_thread=None,
            owner_pid=os.getpid(), owner_start_token=supervisor._process_start_token(os.getpid()),
            now=NOW, lease_seconds=60,
        )
        values.update(updates)
        with mock.patch.object(workspace_boundary, "inspect_git_facts", return_value=self.facts), \
             mock.patch.object(workspace_boundary, "assert_live_entry", return_value=self.facts):
            return workspace_boundary.reserve_launch_attempt(**values)

    def seed_canonical(self, *, attempts=None, agent_id=None, digest=None):
        entry = {
            "entry_id": "wl-123456789abc", "platform": "codex-supervisor",
            "issue": 452, "agent_type": "issue-implementer", "round": None,
            "repository": "owner/repo", "workspace": str(self.child),
            "worktree_path": ".worktrees/issue-452",
            "branch_name": "codex/issue-452", "initial_oid": "a" * 40,
            "task_key": "issue_452",
            "handoff_path": "tmp/_handoff/issue-implementer--issue-452.yaml",
            "protected_plan": [], "status": "open", "agent_id": agent_id,
            "supervisor_attempts": list(attempts or []), "publish_attempts": [],
            "notes": [],
        }
        if digest is not None:
            entry["launch_intent_digest"] = digest
        worktree_ledger.update_ledger(
            self.root, lambda document: document["entries"].append(entry)
        )
        return entry

    def reserve_canonical(self, *, mode="run", digest="b" * 64):
        facts = workspace_boundary.GitFacts(
            str(self.child), str(self.root), ".worktrees/issue-452",
            "owner/repo", "codex/issue-452", "a" * 40,
        )
        with mock.patch.object(workspace_boundary, "inspect_git_facts",
                               return_value=facts):
            return workspace_boundary.reserve_canonical_launch_attempt(
                repo_root=self.root, ledger_entry_id="wl-123456789abc",
                workspace=self.child, issue=452, round_number=1,
                repository="owner/repo", branch_name="codex/issue-452",
                expected_oid="a" * 40, role="issue-implementer",
                task_key="issue_452",
                handoff_path="tmp/_handoff/issue-implementer--issue-452.yaml",
                protected_paths=(), intent_digest=digest, attempt_id="1" * 32,
                mode=mode, owner_pid=os.getpid(),
                owner_start_token=supervisor._process_start_token(os.getpid()),
                now=NOW, lease_seconds=60,
            )

    def verified_lease(self, *, digest="b" * 64):
        with mock.patch.object(workspace_boundary, "inspect_git_facts",
                               return_value=self.facts):
            return workspace_boundary.verify_canonical_launch_reservation(
                repo_root=self.root, ledger_entry_id="wl-123456789abc",
                attempt_id="1" * 32, intent_digest=digest,
                owner_pid=os.getpid(),
                owner_start_token=supervisor._process_start_token(os.getpid()),
                workspace=self.child, repository="owner/repo",
                branch_name="codex/issue-452", expected_oid="a" * 40,
            )

    def test_canonical_reservation_extends_same_entry_and_immutably_binds_intent(self):
        self.seed_canonical()
        entry, thread = self.reserve_canonical()
        document = worktree_ledger.read_ledger(self.root)
        self.assertEqual(len(document["entries"]), 1)
        self.assertEqual(entry["entry_id"], "wl-123456789abc")
        self.assertEqual(entry["launch_intent_digest"], "b" * 64)
        self.assertEqual(entry["supervisor_attempts"][-1]["intent_digest"], "b" * 64)
        self.assertIsNone(thread)

    def test_verified_lease_blocks_cooperative_writer_until_process_start_record(self):
        self.seed_canonical()
        self.reserve_canonical()
        lease = self.verified_lease()
        self.assertFalse(os.get_inheritable(lease._ledger_lease._fd))
        attempted = threading.Event()
        completed = threading.Event()

        def writer():
            attempted.set()
            worktree_ledger.update_ledger(
                self.root,
                lambda document: document["entries"][0]["notes"].append(
                    {"at": "after-process-start", "note": "cooperative writer"}
                ),
            )
            completed.set()

        thread = threading.Thread(target=writer)
        thread.start()
        self.assertTrue(attempted.wait(1))
        thread.join(0.05)
        self.assertFalse(completed.is_set(), "writer advanced while reservation lock was held")
        lease.record_process_started(123, "456", now=NOW)
        thread.join(1)
        self.assertTrue(completed.is_set(), "writer did not advance after process-start boundary")
        attempts = worktree_ledger.read_ledger(self.root)["entries"][0]["supervisor_attempts"]
        self.assertEqual(attempts[-1]["state"], "spawned")

    def test_process_start_record_failure_releases_lease(self):
        self.seed_canonical()
        self.reserve_canonical()
        lease = self.verified_lease()
        with mock.patch.object(
            lease._ledger_lease, "commit",
            side_effect=worktree_ledger.LedgerError("LEDGER_WRITE_ERROR"),
        ), self.assertRaisesRegex(
            workspace_boundary.SupervisorWorkspaceError, "LEDGER_WRITE_ERROR",
        ):
            lease.record_process_started(123, "456", now=NOW)
        self.assertTrue(lease.closed)
        worktree_ledger.update_ledger(self.root, lambda _document: None)

    def test_final_owner_start_token_mismatch_releases_lock(self):
        self.seed_canonical()
        self.reserve_canonical()
        with mock.patch.object(workspace_boundary, "inspect_git_facts",
                               return_value=self.facts), self.assertRaisesRegex(
            workspace_boundary.SupervisorWorkspaceError, "ATTEMPT_FENCED",
        ):
            workspace_boundary.verify_canonical_launch_reservation(
                repo_root=self.root, ledger_entry_id="wl-123456789abc",
                attempt_id="1" * 32, intent_digest="b" * 64,
                owner_pid=os.getpid(), owner_start_token="0",
                workspace=self.child, repository="owner/repo",
                branch_name="codex/issue-452", expected_oid="a" * 40,
            )
        worktree_ledger.update_ledger(self.root, lambda _document: None)

    def test_canonical_resume_is_derived_and_run_requires_resume(self):
        paused = [{
            "at": "2026-09-08T00:00:00Z", "attempt_id": "0" * 32,
            "state": "paused_rate_limit", "thread_id": "thread-1",
        }]
        self.seed_canonical(attempts=paused, agent_id="thread-1", digest="b" * 64)
        with self.assertRaisesRegex(workspace_boundary.SupervisorWorkspaceError,
                                    "RESUME_REQUIRED"):
            self.reserve_canonical(mode="run")
        _entry, thread = self.reserve_canonical(mode="resume")
        self.assertEqual(thread, "thread-1")

    def test_canonical_resume_rejects_missing_or_mismatched_thread(self):
        for label, attempts, agent_id in (
            ("missing", [], None),
            ("later-failure", [{"state": "paused_rate_limit", "thread_id": "thread-1"},
                               {"state": "failed", "thread_id": "thread-1"}], "thread-1"),
            ("mismatch", [{"state": "paused_rate_limit", "thread_id": "thread-1"}],
             "thread-2"),
        ):
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as directory:
                    old_root, old_child = self.root, self.child
                    self.root = Path(directory)
                    self.child = self.root / ".worktrees/issue-452"
                    self.child.mkdir(parents=True)
                    try:
                        self.seed_canonical(attempts=attempts, agent_id=agent_id,
                                            digest="b" * 64)
                        with self.assertRaisesRegex(
                            workspace_boundary.SupervisorWorkspaceError,
                            "RESUME_STATE_INVALID",
                        ):
                            self.reserve_canonical(mode="resume")
                    finally:
                        self.root, self.child = old_root, old_child

    def test_first_run_atomically_creates_launch_and_reserves_attempt(self):
        entry = self.reserve()
        self.assertEqual(entry["platform"], "codex-supervisor")
        self.assertNotIn("prepared_at", entry)
        self.assertNotIn("expires_at", entry)
        self.assertEqual(entry["supervisor_attempts"][-1]["state"], "reserved")
        self.assertEqual(entry["supervisor_attempts"][-1]["transport_contract"],
                         "codex-supervisor/direct-exec-v1")

    def test_launch_identity_is_immutable(self):
        self.reserve()
        with self.assertRaisesRegex(workspace_boundary.SupervisorWorkspaceError,
                                    "LAUNCH_IMMUTABLE_MISMATCH"):
            self.reserve(protected_paths=(".codex/agents/x.toml=" + "0" * 64,),
                         attempt_id="2" * 32)

    def test_active_attempt_cannot_be_double_reserved(self):
        self.reserve()
        with self.assertRaisesRegex(workspace_boundary.SupervisorWorkspaceError,
                                    "ATTEMPT_ACTIVE"):
            self.reserve(attempt_id="2" * 32)

    def test_invalid_task_and_protected_plan_fail_before_ledger_write(self):
        for updates in (
            {"task_key": "issue_451"},
            {"protected_paths": ("docs/nope=" + "0" * 64,)},
        ):
            with self.subTest(updates=updates), self.assertRaises(
                workspace_boundary.SupervisorWorkspaceError
            ):
                self.reserve(**updates)
        self.assertEqual(worktree_ledger.read_ledger(self.root)["entries"], [])


class DirectCommandTests(unittest.TestCase):
    def test_public_launch_cli_accepts_only_four_canonical_inputs(self):
        parser = supervisor.build_parser()
        run = parser.parse_args([
            "run", "--issue", "452", "--role", "issue-implementer",
            "--change-plan-id", "plan-452",
        ])
        self.assertEqual((run.issue, run.role, run.change_plan_id, run.fixer_round),
                         (452, "issue-implementer", "plan-452", None))
        resume = parser.parse_args([
            "resume", "--issue", "452", "--role", "issue-fixer",
            "--change-plan-id", "plan-452-r2", "--fixer-round", "2",
        ])
        self.assertEqual(resume.fixer_round, 2)
        retired = (
            "--repo-root", "--workspace", "--task-key", "--handoff-path", "--round",
            "--repository", "--branch", "--expected-oid", "--protected-path",
            "--prompt-file", "--bwrap", "--codex", "--timeout", "--thread",
        )
        for option in retired:
            with self.subTest(option=option), mock.patch("sys.stderr"), \
                 self.assertRaises(SystemExit):
                parser.parse_args(["run", "--issue", "452", "--role",
                                   "issue-implementer", "--change-plan-id",
                                   "plan-452", option, "value"])
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            parser.parse_args([
                "run", "--issue", "452", "--issue", "453", "--role",
                "issue-implementer", "--change-plan-id", "plan-452",
            ])

    def test_launch_request_enforces_conditional_fixer_round(self):
        for request, reason in (
            (supervisor.codex_launch_intent.LaunchRequest(
                452, "issue-implementer", "p", 1), "FIXER_ROUND_FORBIDDEN"),
            (supervisor.codex_launch_intent.LaunchRequest(
                452, "issue-fixer", "p", None), "FIXER_ROUND_INVALID"),
        ):
            with self.subTest(reason=reason), self.assertRaisesRegex(
                supervisor.codex_launch_intent.LaunchIntentError, reason,
            ):
                supervisor.codex_launch_intent._validate_request(request)

    def test_direct_exec_has_workspace_write_network_deny_and_no_broker(self):
        command = (
            "/usr/bin/bwrap", "--setenv", "CODEX_HOME", "/tmp/codex-home",
            "--", "/opt/codex", "exec", "-C", "/work",
            "--sandbox", "workspace-write", "--config",
            "sandbox_workspace_write.network_access=false", "--config",
            'shell_environment_policy.inherit="none"', "--config",
            "features.multi_agent=false", "--config", "agents.enabled=false",
            "-",
        )
        with self.assertRaisesRegex(
            supervisor.CodexSupervisorError, "LEGACY_SANDBOX_PRESENT"
        ):
            supervisor.validate_cli_compatibility(command)
        supervisor.validate_broker_protocol(command)
        self.assertNotIn("issue_exec_broker", " ".join(command))

    def test_broker_or_weakened_direct_contract_is_denied(self):
        with self.assertRaisesRegex(supervisor.CodexSupervisorError, "RETIRED_BROKER"):
            supervisor.validate_broker_protocol(("codex_exec_broker.py",))
        with self.assertRaisesRegex(supervisor.CodexSupervisorError,
                                    "(DIRECT_EXEC_CONTRACT|CONFIG_INVALID|ENVIRONMENT_INVALID)"):
            supervisor.validate_cli_compatibility(("bwrap", "--", "codex", "exec", "-"))

    def _profile_fixture(self, root):
        home = root / "home"
        auth_home = home / ".codex"
        auth_home.mkdir(parents=True, mode=0o700)
        auth = auth_home / "auth.json"
        auth.write_text("fake", encoding="utf-8")
        auth.chmod(0o600)
        workspace = root / "workspace"
        workspace.mkdir(mode=0o700)
        install = root / "codex-install"
        (install / "bin").mkdir(parents=True, mode=0o700)
        (install / "package.json").write_text("{}", encoding="utf-8")
        codex = install / "bin" / "codex"
        codex.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        codex.chmod(0o755)
        runtime = root / "runtime-home"
        (runtime / "sessions").mkdir(parents=True, mode=0o700)
        (runtime / "sqlite").mkdir(mode=0o700)
        runtime.chmod(0o700)
        runtime_home = supervisor.RuntimeHome(
            runtime, runtime / "sqlite", runtime / "sessions", auth, runtime / "auth.json"
        )
        spec = supervisor.SupervisorSpec(
            root, workspace, "issue-implementer", "issue_452", "tmp/_handoff/x.yaml"
        )
        return home, workspace, codex, runtime_home, spec

    def test_permission_profile_is_typed_exact_and_denies_runtime_auth_tree_and_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, workspace, codex, runtime, spec = self._profile_fixture(root)
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                snapshot = supervisor.snapshot_credentials(runtime)
                profile = supervisor.generate_permission_profile(
                    spec, runtime, codex_executable=codex
                )
                checked = supervisor.validate_permission_profile(
                    profile, expected_deny_paths=profile.deny_paths,
                    expected_digest=profile.digest,
                )
                self.assertEqual(snapshot.source_digest, snapshot.target_digest)
                self.assertEqual(checked.digest, profile.digest)
                document = tomllib.loads(profile.path.read_text(encoding="utf-8"))
                selected = document["permissions"]["issue-supervised"]
                self.assertEqual(document["default_permissions"], "issue-supervised")
                self.assertEqual(selected["extends"], ":workspace")
                self.assertEqual(set(selected["filesystem"].values()), {"deny"})
                self.assertFalse(selected["network"]["enabled"])
                self.assertFalse(selected["network"]["allow_local_binding"])
                self.assertFalse(selected["network"]["dangerously_allow_all_unix_sockets"])
                self.assertFalse(selected["network"]["dangerously_allow_non_loopback_proxy"])
                self.assertIn(str(runtime.root), selected["filesystem"])
                self.assertIn(str(home / ".codex"), selected["filesystem"])
                self.assertIn(str(codex.parent.parent), selected["filesystem"])
                self.assertNotIn(str(codex.parent), selected["filesystem"])
                self.assertNotIn(str(runtime.auth_target), selected["filesystem"])
                self.assertNotIn(str(home / ".codex" / "auth.json"), selected["filesystem"])
                self.assertNotIn(str(codex), selected["filesystem"])
                supervisor.cleanup_credentials(runtime)
                self.assertFalse(runtime.auth_target.exists())

    def test_cli_preflight_rejects_project_legacy_and_critical_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, workspace, codex, runtime, spec = self._profile_fixture(root)
            (workspace / ".codex").mkdir(mode=0o700)
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                supervisor.snapshot_credentials(runtime)
                profile = supervisor.generate_permission_profile(
                    spec, runtime, codex_executable=codex
                )
                command = (
                    str(root / "bwrap"), "--clearenv", "--setenv", "HOME", str(runtime.root),
                    "--setenv", "CODEX_HOME", str(runtime.root), "--setenv", "TMPDIR", "/tmp",
                    "--ro-bind", str(codex), str(codex),
                    "--", str(codex), "--profile", profile.name, "--strict-config",
                    "--ask-for-approval", "never", "exec", "-C", str(workspace),
                    "--ignore-user-config", "--json", "-",
                )
                (workspace / ".codex/config.toml").write_text(
                    "sandbox_mode = \"workspace-write\"\n", encoding="utf-8"
                )
                with self.assertRaisesRegex(supervisor.CodexSupervisorError, "LEGACY_SANDBOX_PRESENT"):
                    supervisor.validate_cli_compatibility(
                        command, runner=lambda *args, **kwargs: subprocess.CompletedProcess([], 0)
                    )
                (workspace / ".codex/config.toml").write_text(
                    "default_permissions = \"danger-full-access\"\n", encoding="utf-8"
                )
                with self.assertRaisesRegex(supervisor.CodexSupervisorError, "EFFECTIVE_MISMATCH"):
                    supervisor.validate_cli_compatibility(
                        command, runner=lambda *args, **kwargs: subprocess.CompletedProcess([], 0)
                    )
                supervisor.cleanup_credentials(runtime)

    def test_cli_preflight_rejects_runtime_config_overrides_before_probe_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, workspace, codex, runtime, spec = self._profile_fixture(root)
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                supervisor.snapshot_credentials(runtime)
                profile = supervisor.generate_permission_profile(
                    spec, runtime, codex_executable=codex
                )
                command = (
                    str(root / "bwrap"), "--clearenv", "--setenv", "HOME", str(runtime.root),
                    "--setenv", "CODEX_HOME", str(runtime.root), "--setenv", "TMPDIR", "/tmp",
                    "--", str(codex), "--profile", profile.name, "--strict-config",
                    "--ask-for-approval", "never", "exec", "-C", str(workspace),
                    "--ignore-user-config", "--json", "-",
                )
                (runtime.root / "config.toml").write_text(
                    "permissions = { issue-supervised = { network = { enabled = true } } }\n",
                    encoding="utf-8",
                )
                runner = mock.Mock()
                with self.assertRaisesRegex(
                    supervisor.CodexSupervisorError, "EFFECTIVE_MISMATCH"
                ):
                    supervisor.validate_cli_compatibility(command, runner=runner)
                runner.assert_not_called()
                supervisor.cleanup_credentials(runtime)

    def test_permission_profile_tamper_owner_mode_symlink_and_hardlink_fail_close(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, workspace, codex, runtime, spec = self._profile_fixture(root)
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                supervisor.snapshot_credentials(runtime)
                profile = supervisor.generate_permission_profile(
                    spec, runtime, codex_executable=codex
                )
                profile.path.chmod(0o600)
                profile.path.write_text(profile.path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
                with self.assertRaisesRegex(supervisor.CodexSupervisorError, "PROFILE_(TAMPERED|SCHEMA_INVALID|INVALID)"):
                    supervisor.validate_permission_profile(profile, expected_digest=profile.digest)
                profile.path.write_text(supervisor._render_permission_profile(
                    deny_paths=profile.deny_paths, profile_name="issue-supervised"
                ), encoding="utf-8")
                profile.path.chmod(0o600)
                with self.assertRaisesRegex(supervisor.CodexSupervisorError, "PROFILE_INVALID"):
                    supervisor.validate_permission_profile(profile)
                profile.path.chmod(0o400)
                other = runtime.root / "profile-copy"
                os.link(profile.path, other)
                with self.assertRaisesRegex(supervisor.CodexSupervisorError, "PROFILE_INVALID"):
                    supervisor.validate_permission_profile(profile)
                other.unlink()
                profile.path.unlink()
                profile.path.symlink_to(runtime.root / "profile-copy")
                with self.assertRaisesRegex(supervisor.CodexSupervisorError, "PROFILE_INVALID"):
                    supervisor.validate_permission_profile(profile)

    def test_generated_profile_unknown_key_is_denied_before_probe_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, workspace, codex, runtime, spec = self._profile_fixture(root)
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                supervisor.snapshot_credentials(runtime)
                profile = supervisor.generate_permission_profile(
                    spec, runtime, codex_executable=codex
                )
                profile.path.chmod(0o600)
                profile.path.write_text(
                    profile.path.read_text(encoding="utf-8") + "unknown = true\n",
                    encoding="utf-8",
                )
                profile.path.chmod(0o400)
                with self.assertRaisesRegex(
                    supervisor.CodexSupervisorError,
                    "PROFILE_(SCHEMA_INVALID|TAMPERED|INVALID)|EFFECTIVE_MISMATCH",
                ):
                    supervisor.validate_permission_profile(profile)
                supervisor.cleanup_credentials(runtime)

    def test_generated_profile_missing_or_malformed_is_denied_before_probe_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, workspace, codex, runtime, spec = self._profile_fixture(root)
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                supervisor.snapshot_credentials(runtime)
                profile = supervisor.generate_permission_profile(
                    spec, runtime, codex_executable=codex
                )
                command = (
                    str(root / "bwrap"), "--clearenv", "--setenv", "HOME", str(runtime.root),
                    "--setenv", "CODEX_HOME", str(runtime.root), "--setenv", "TMPDIR", "/tmp",
                    "--", str(codex), "--profile", profile.name, "--strict-config",
                    "--ask-for-approval", "never", "exec", "-C", str(workspace),
                    "--ignore-user-config", "--json", "-",
                )
                profile.path.unlink()
                runner = mock.Mock()
                with self.assertRaisesRegex(
                    supervisor.CodexSupervisorError, "PROFILE_INVALID"
                ):
                    supervisor.validate_cli_compatibility(command, runner=runner)
                runner.assert_not_called()
                profile = supervisor.generate_permission_profile(
                    spec, runtime, codex_executable=codex
                )
                profile.path.chmod(0o600)
                profile.path.write_bytes(b"permissions = [\n")
                profile.path.chmod(0o400)
                with self.assertRaisesRegex(
                    supervisor.CodexSupervisorError, "PROFILE_(INVALID|SCHEMA_INVALID)"
                ):
                    supervisor.validate_cli_compatibility(command, runner=runner)
                runner.assert_not_called()
                supervisor.cleanup_credentials(runtime)

    def test_auth_source_hardlink_and_snapshot_cleanup_fail_close(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, _workspace, _codex, runtime, _spec = self._profile_fixture(root)
            auth = home / ".codex/auth.json"
            hardlink = home / ".codex/auth-copy.json"
            os.link(auth, hardlink)
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                with self.assertRaisesRegex(supervisor.CodexSupervisorError, "AUTH_SOURCE_INVALID"):
                    supervisor.snapshot_credentials(runtime)
            hardlink.unlink()
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                snapshot = supervisor.snapshot_credentials(runtime)
                self.assertEqual(snapshot.source_digest, snapshot.target_digest)
                supervisor.cleanup_credentials(runtime)

    def test_snapshot_post_publish_failure_removes_public_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, _workspace, _codex, runtime, _spec = self._profile_fixture(root)
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                with mock.patch.object(
                    supervisor, "_read_private_file_at",
                    side_effect=supervisor.CodexSupervisorError(
                        "CODEX_SUPERVISOR_AUTH_TARGET_INVALID"
                    ),
                ):
                    with self.assertRaisesRegex(
                        supervisor.CodexSupervisorError, "AUTH_TARGET_INVALID"
                    ):
                        supervisor.snapshot_credentials(runtime)
                self.assertFalse(runtime.auth_target.exists())

    def test_snapshot_post_publish_baseexception_still_cleans_target(self):
        for injected in (KeyboardInterrupt(), SystemExit(), RuntimeError("injected")):
            with self.subTest(injected=type(injected).__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                home, _workspace, _codex, runtime, _spec = self._profile_fixture(root)
                with mock.patch.dict(os.environ, {"HOME": str(home)}), mock.patch.object(
                    supervisor, "_read_private_file_at", side_effect=injected
                ):
                    with self.assertRaises(type(injected)):
                        supervisor.snapshot_credentials(runtime)
                self.assertFalse(runtime.auth_target.exists())

    def test_snapshot_dir_fsync_and_target_digest_failures_clean_target(self):
        for failure in ("fsync", "digest"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                home, _workspace, _codex, runtime, _spec = self._profile_fixture(root)
                with mock.patch.dict(os.environ, {"HOME": str(home)}):
                    if failure == "fsync":
                        real_fsync = supervisor.os.fsync
                        calls = 0

                        def fail_directory_fsync(descriptor):
                            nonlocal calls
                            calls += 1
                            if calls == 2:
                                raise OSError("directory fsync injection")
                            return real_fsync(descriptor)

                        patcher = mock.patch.object(
                            supervisor.os, "fsync", side_effect=fail_directory_fsync
                        )
                    else:
                        real_sha256 = supervisor.hashlib.sha256
                        calls = 0

                        def fail_target_digest(*args, **kwargs):
                            nonlocal calls
                            calls += 1
                            if calls == 2:
                                raise RuntimeError("digest injection")
                            return real_sha256(*args, **kwargs)

                        patcher = mock.patch.object(
                            supervisor.hashlib, "sha256", side_effect=fail_target_digest
                        )
                    with patcher:
                        expected_error = (
                            RuntimeError if failure == "digest"
                            else supervisor.CodexSupervisorError
                        )
                        with self.assertRaises(expected_error):
                            supervisor.snapshot_credentials(runtime)
                    self.assertFalse(runtime.auth_target.exists())

    def test_snapshot_post_publish_dirfd_and_stat_failures_clean_target(self):
        for failure in ("dirfd", "stat"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                home, _workspace, _codex, runtime, _spec = self._profile_fixture(root)
                with mock.patch.dict(os.environ, {"HOME": str(home)}):
                    if failure == "dirfd":
                        real_open = supervisor._open_private_directory_fd
                        calls = 0

                        def fail_post_publish_dirfd(path, *, reason):
                            nonlocal calls
                            calls += 1
                            if calls == 2:
                                raise OSError("directory fd injection")
                            return real_open(path, reason=reason)

                        patcher = mock.patch.object(
                            supervisor, "_open_private_directory_fd",
                            side_effect=fail_post_publish_dirfd,
                        )
                        expected_reason = "AUTH_SNAPSHOT_FAILED"
                    else:
                        real_stat = supervisor.os.stat
                        injected = False

                        def fail_target_stat(path, *args, **kwargs):
                            nonlocal injected
                            if (
                                not injected and kwargs.get("dir_fd") is not None
                                and path == runtime.auth_target.name
                            ):
                                injected = True
                                raise OSError("target stat injection")
                            return real_stat(path, *args, **kwargs)

                        patcher = mock.patch.object(
                            supervisor.os, "stat", side_effect=fail_target_stat
                        )
                        expected_reason = "AUTH_TARGET_CHANGED"
                    with patcher:
                        with self.assertRaisesRegex(
                            supervisor.CodexSupervisorError, expected_reason
                        ):
                            supervisor.snapshot_credentials(runtime)
                    self.assertFalse(runtime.auth_target.exists())

    def test_post_publish_cleanup_failure_preserves_original_and_reason(self):
        original = RuntimeError("digest injection")
        cleanup_failure = supervisor.CodexSupervisorError(
            "CODEX_SUPERVISOR_AUTH_TARGET_CHANGED", "replacement"
        )
        with mock.patch.object(
            supervisor, "_remove_stale_auth_target", side_effect=cleanup_failure
        ):
            with self.assertRaisesRegex(
                supervisor.CodexSupervisorError,
                "AUTH_CLEANUP_FAILED: CODEX_SUPERVISOR_AUTH_TARGET_CHANGED",
            ) as raised:
                supervisor._cleanup_published_snapshot_after_failure(
                    Path("/private/auth.json"), original=original
                )
        self.assertIs(raised.exception.__cause__, original)

    def test_cleanup_rechecks_dirfd_entry_before_unlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, _workspace, _codex, runtime, _spec = self._profile_fixture(root)
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                supervisor.snapshot_credentials(runtime)
                original_stat = os.stat
                def swapped_stat(path, *args, **kwargs):
                    if kwargs.get("dir_fd") is not None and path == runtime.auth_target.name:
                        return original_stat(home / ".codex" / "auth.json")
                    return original_stat(path, *args, **kwargs)

                with mock.patch.object(supervisor.os, "stat", side_effect=swapped_stat):
                    with self.assertRaisesRegex(
                        supervisor.CodexSupervisorError, "AUTH_TARGET_CHANGED"
                    ):
                        supervisor.cleanup_credentials(runtime)
                self.assertTrue(runtime.auth_target.exists())
                supervisor.cleanup_credentials(runtime)

    def test_cleanup_rejects_renamed_and_symlink_target_without_deleting_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, _workspace, _codex, runtime, _spec = self._profile_fixture(root)
            renamed = runtime.root / "auth-renamed.json"
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                supervisor.snapshot_credentials(runtime)
                runtime.auth_target.rename(renamed)
                runtime.auth_target.symlink_to(renamed)
                with self.assertRaisesRegex(
                    supervisor.CodexSupervisorError, "AUTH_PLACEHOLDER_INVALID"
                ):
                    supervisor.cleanup_credentials(runtime)
                self.assertTrue(runtime.auth_target.is_symlink())
                self.assertTrue(renamed.exists())
                runtime.auth_target.unlink()
                renamed.rename(runtime.auth_target)
                supervisor.cleanup_credentials(runtime)
                self.assertFalse(runtime.auth_target.exists())

    def test_active_profile_probe_is_model_free_and_not_synthetic_outer_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, workspace, codex, runtime, spec = self._profile_fixture(root)
            # This active-profile fixture models the production native executable
            # boundary.  The runner seam below means the bytes are never executed,
            # but the command must still carry the one read-only private alias bind
            # that validate_cli_compatibility authorizes in production.
            codex.write_bytes(b"\x7fELFfixture-native-codex")
            alias = supervisor._CODEX_CONTROL_ALIAS
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                supervisor.snapshot_credentials(runtime)
                profile = supervisor.generate_permission_profile(
                    spec, runtime, codex_executable=codex
                )
                command = (
                    str(root / "bwrap"), "--die-with-parent", "--new-session",
                    "--unshare-pid", "--tmpfs", "/run", "--dir", str(alias.parent),
                    "--ro-bind", str(codex), str(alias), "--tmpfs", "/tmp", "--clearenv",
                    "--setenv", "HOME", str(runtime.root),
                    "--setenv", "CODEX_HOME", str(runtime.root),
                    "--setenv", "TMPDIR", "/tmp",
                    "--", str(alias), "--profile", profile.name, "--strict-config",
                    "--ask-for-approval", "never", "exec", "-C", str(workspace),
                    "--ignore-user-config", "--json", "-",
                )
                probe = supervisor._build_active_boundary_probe_command(
                    command, python_executable="/usr/bin/python3", workspace=workspace,
                    runtime_home=runtime.root, host_auth=home / ".codex/auth.json",
                    codex=str(alias), tcp_port=31000,
                    unix_path=workspace / ".probe.sock",
                )
                separator = probe.index("--")
                inner = probe[separator + 1:]
                self.assertEqual(
                    inner[:8],
                    (str(alias), "--profile", "issue-supervised", "sandbox",
                     "-P", "issue-supervised", "-C", str(workspace)),
                )
                self.assertNotIn("--strict-config", inner)
                self.assertNotIn("--unshare-net", probe)
                self.assertEqual(probe.count("--tmpfs"), 1)
                payload = json.loads(probe[-1])
                self.assertEqual(payload["runtime"], str(runtime.root))
                self.assertEqual(payload["host_auth"], str(home / ".codex/auth.json"))
                supervisor.cleanup_credentials(runtime)

    def test_active_profile_probe_missing_result_is_not_a_completion_pass(self):
        with self.assertRaisesRegex(
            supervisor.CodexSupervisorError, "PROBE_NOT_TESTED"
        ):
            supervisor._validate_active_boundary_probe(
                "", 0, workspace=Path("/workspace"), runtime_home=Path("/runtime")
            )

    def test_active_profile_probe_rejects_each_weakened_boundary_result(self):
        expected = {
            "workspace": {"read": True, "write": True, "exec": True},
            "runtime": {"read": False, "write": False, "exec": False},
            "runtime_auth": {"read": False, "write": False, "exec": False},
            "host_auth": {"read": False, "write": False, "exec": False},
            "install": {"read": False, "write": False, "exec": False},
            "network": {"tcp": False, "unix": False},
            "environment": {"HOME": None, "CODEX_HOME": None, "TMPDIR": None,
                            "PATH": "/usr/bin:/bin"},
            "inherited_fds": [],
            "proc": {"self_status": True, "pid1": True},
        }
        weakenings = (
            ("workspace", "write", False),
            ("runtime", "read", True),
            ("runtime_auth", "exec", True),
            ("host_auth", "read", True),
            ("install", "write", True),
            ("network", "tcp", True),
            ("network", "unix", True),
        )
        for key, field, value in weakenings:
            with self.subTest(key=key, field=field):
                observed = json.loads(json.dumps(expected))
                observed[key][field] = value
                with self.assertRaisesRegex(
                    supervisor.CodexSupervisorError, "PROBE_BOUNDARY_MISMATCH"
                ):
                    supervisor._validate_active_boundary_probe(
                        json.dumps(observed), 0,
                        workspace=Path("/workspace"), runtime_home=Path("/runtime"),
                    )

    def test_cli_preflight_runs_active_profile_probe_and_returns_evidence(self):
        try:
            probe_socket = socket.socket()
        except PermissionError:
            self.skipTest("outer test sandbox denies local socket creation")
        else:
            probe_socket.close()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, workspace, codex, runtime, spec = self._profile_fixture(root)
            codex.write_bytes(b"\x7fELFfixture-native-codex")
            alias = supervisor._CODEX_CONTROL_ALIAS
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                supervisor.snapshot_credentials(runtime)
                profile = supervisor.generate_permission_profile(
                    spec, runtime, codex_executable=codex
                )
                command = (
                    str(root / "bwrap"), "--tmpfs", "/run", "--dir", str(alias.parent),
                    "--ro-bind", str(codex), str(alias),
                    "--clearenv", "--setenv", "HOME", str(runtime.root),
                    "--setenv", "CODEX_HOME", str(runtime.root), "--setenv", "TMPDIR", "/tmp",
                    "--", str(alias), "--profile", profile.name, "--strict-config",
                    "--ask-for-approval", "never", "exec", "-C", str(workspace),
                    "--ignore-user-config", "--json", "-",
                )
                expected = {
                    "workspace": {"read": True, "write": True, "exec": True},
                    "runtime": {"read": False, "write": False, "exec": False},
                    "runtime_auth": {"read": False, "write": False, "exec": False},
                    "host_auth": {"read": False, "write": False, "exec": False},
                    "install": {"read": False, "write": False, "exec": False},
                    "network": {"tcp": False, "unix": False},
                    "environment": {"HOME": None, "CODEX_HOME": None, "TMPDIR": None,
                                    "PATH": "/usr/bin:/bin"},
                    "inherited_fds": [],
                    "proc": {"self_status": True, "pid1": True},
                }
                seen = {}

                def runner(probe_command, **kwargs):
                    seen["command"] = probe_command
                    seen["kwargs"] = kwargs
                    return subprocess.CompletedProcess(probe_command, 0, json.dumps(expected), "")

                evidence = supervisor.validate_cli_compatibility(command, runner=runner)
                self.assertEqual(evidence, expected)
                separator = seen["command"].index("--")
                self.assertEqual(seen["command"][separator + 1:separator + 7], (
                    str(alias), "--profile", "issue-supervised", "sandbox", "-P",
                    "issue-supervised",
                ))
                supervisor.cleanup_credentials(runtime)

    def test_installed_codex_profile_normal_and_negative_matrix_is_model_free(self):
        codex = shutil.which("codex")
        bwrap = shutil.which("bwrap")
        if codex is None or bwrap is None:
            self.skipTest("NOT_TESTED: installed codex or bubblewrap unavailable")
        # The production outer sandbox mounts a private /tmp. Keep the fixture
        # below the checkout so that mount cannot hide its workspace/runtime.
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            home, workspace, _fixture_codex, runtime, spec = self._profile_fixture(root)
            installed_codex = supervisor._resolved_codex_runtime_executable(Path(codex))
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                supervisor.snapshot_credentials(runtime)
                profile = supervisor.generate_permission_profile(
                    spec, runtime, codex_executable=installed_codex
                )
                install_roots = supervisor._resolved_codex_install_roots(installed_codex)
                alias = supervisor._CODEX_CONTROL_ALIAS
                command = (
                    bwrap, "--die-with-parent", "--new-session", "--unshare-pid",
                    "--ro-bind", "/", "/", "--dev", "/dev", "--remount-ro", "/dev",
                    "--proc", "/proc", "--bind", str(workspace), str(workspace),
                    "--bind", str(runtime.root), str(runtime.root), "--tmpfs", "/tmp",
                    "--tmpfs", "/run", "--dir", str(alias.parent),
                    "--ro-bind", str(installed_codex), str(alias),
                    "--clearenv", "--setenv", "HOME", str(runtime.root),
                    "--setenv", "CODEX_HOME", str(runtime.root), "--setenv", "TMPDIR", "/tmp",
                    "--setenv", "PATH", supervisor._codex_launch_path(installed_codex),
                    "--setenv", "CODEX_SQLITE_HOME", str(runtime.sqlite),
                    "--chdir", str(workspace), "--", str(alias),
                    "--profile", profile.name, "--strict-config",
                    "--ask-for-approval", "never", "exec", "-C", str(workspace),
                    "--ignore-user-config", "--json", "-",
                )
                try:
                    evidence = supervisor.validate_cli_compatibility(
                        command, runner=subprocess.run
                    )
                except supervisor.CodexSupervisorError as exc:
                    if exc.reason == "CODEX_SUPERVISOR_PROBE_NOT_TESTED":
                        self.skipTest(f"NOT_TESTED: installed active boundary unavailable ({exc})")
                    raise
                else:
                    self.assertEqual(evidence["network"], {"tcp": False, "unix": False})
                    self.assertIsNone(evidence["environment"]["HOME"])

                    valid_profile = profile.path.read_text(encoding="utf-8")

                    def write_profile(payload):
                        profile.path.chmod(0o600)
                        profile.path.write_text(payload, encoding="utf-8")
                        profile.path.chmod(0o400)

                    def assert_real_cli_nonpass(
                        payload, label, expected_reason, observed_change=None
                    ):
                        if payload is None:
                            profile.path.unlink()
                        else:
                            write_profile(payload)
                        with self.subTest(real_cli_control=label):
                            with self.assertRaises(
                                supervisor.CodexSupervisorError
                            ) as raised:
                                supervisor._run_active_boundary_probe(
                                    command, workspace=workspace, runtime_home=runtime.root,
                                    host_auth=home / ".codex/auth.json", codex=str(alias),
                                    install_probe=install_roots[0], runner=subprocess.run,
                                )
                            self.assertEqual(raised.exception.reason, expected_reason)
                            if observed_change is not None:
                                section, field, expected_value = observed_change
                                observed = json.loads(raised.exception.detail)
                                self.assertEqual(
                                    observed[section][field], expected_value,
                                    f"{label} did not exercise the intended weakened boundary",
                                )
                        if not profile.path.exists():
                            profile.path.write_text(valid_profile, encoding="utf-8")
                            profile.path.chmod(0o400)

                    assert_real_cli_nonpass(
                        None, "missing", "CODEX_SUPERVISOR_PROBE_NOT_TESTED"
                    )
                    assert_real_cli_nonpass(
                        "permissions = [\n", "malformed",
                        "CODEX_SUPERVISOR_PROBE_NOT_TESTED",
                    )
                    write_profile(valid_profile + "unknown_key = true\n")
                    # 0.153.4 accepts an unknown permission key; the supervisor's
                    # exact-schema gate, not the CLI, must therefore fail closed.
                    unknown_evidence = supervisor._run_active_boundary_probe(
                        command, workspace=workspace, runtime_home=runtime.root,
                        host_auth=home / ".codex/auth.json", codex=str(alias),
                        install_probe=install_roots[0], runner=subprocess.run,
                    )
                    self.assertEqual(unknown_evidence["network"], {"tcp": False, "unix": False})
                    with self.assertRaisesRegex(
                        supervisor.CodexSupervisorError,
                        "(SCHEMA_INVALID|EFFECTIVE_MISMATCH)",
                    ):
                        supervisor.validate_permission_profile(profile.path)
                    write_profile("sandbox_mode = \"danger-full-access\"\n" + valid_profile)
                    legacy_evidence = supervisor._run_active_boundary_probe(
                        command, workspace=workspace, runtime_home=runtime.root,
                        host_auth=home / ".codex/auth.json", codex=str(alias),
                        install_probe=install_roots[0], runner=subprocess.run,
                    )
                    self.assertEqual(legacy_evidence["network"], {"tcp": False, "unix": False})
                    with self.assertRaisesRegex(
                        supervisor.CodexSupervisorError, "SCHEMA_INVALID"
                    ):
                        supervisor.validate_permission_profile(profile.path)
                    assert_real_cli_nonpass(
                        valid_profile.replace(
                            'enabled = false', 'enabled = true', 1
                        ).replace(
                            'allow_local_binding = false', 'allow_local_binding = true', 1
                        ).replace(
                            'dangerously_allow_all_unix_sockets = false',
                            'dangerously_allow_all_unix_sockets = true', 1,
                        ),
                        "critical-network-override",
                        "CODEX_SUPERVISOR_PROBE_BOUNDARY_MISMATCH",
                        ("network", "tcp", True),
                    )
                    runtime_key = json.dumps(str(runtime.root)) + ' = "deny"'
                    assert_real_cli_nonpass(
                        valid_profile.replace(runtime_key, json.dumps(str(runtime.root)) + ' = "read"'),
                        "critical-runtime-override",
                        "CODEX_SUPERVISOR_PROBE_BOUNDARY_MISMATCH",
                        ("runtime", "read", True),
                    )
                finally:
                    supervisor.cleanup_credentials(runtime)


class ProductionLaunchLeaseTests(unittest.TestCase):
    """The four-input production entrypoint must carry the lease into Popen."""

    class Lease:
        def __init__(self, *, record_error=None):
            self._lock = threading.Lock()
            self._lock.acquire()
            self.closed = False
            self.record_error = record_error
            self.events = []

        def record_process_started(self, pid, token, *, now):
            self.events.append(("spawned-commit", pid, token, now))
            try:
                if self.record_error is not None:
                    raise self.record_error
            finally:
                self.release()

        def release(self):
            if not self.closed:
                self.closed = True
                self._lock.release()

        def wait_for_writer(self, timeout):
            acquired = self._lock.acquire(timeout=timeout)
            if acquired:
                self._lock.release()
            return acquired

    def setUp(self):
        self.request = supervisor.codex_launch_intent.LaunchRequest(
            452, "issue-implementer", "plan-452",
        )
        self.intent = supervisor.codex_launch_intent.LaunchIntent(
            schema_version="codex-launch-intent/1", issue=452,
            role="issue-implementer", round_number=1,
            change_plan_id="plan-452", repository="owner/repo",
            workspace="/repo/.worktrees/issue-452",
            branch_name="codex/issue-452", expected_oid="a" * 40,
            task_key="issue_452",
            handoff_path="tmp/_handoff/issue-implementer--issue-452.yaml",
            model="gpt-5.6-sol", reasoning_effort="xhigh",
            bwrap_executable="/usr/bin/bwrap", codex_executable="/opt/codex",
            executable_evidence={"codex": {"sha256": "b" * 64}},
            permission_profile="issue-supervised",
            runtime_root="tmp/_codex_sessions/issue_452/runtime-home",
            protected_paths=(), finding_ids=(),
            source_provenance={"issue": {"sha256": "c" * 64}}, prompt="task",
            ledger_entry_id="wl-123456789abc", plan_digest="d" * 64,
            manifest_digest="e" * 64, canonical_entry_digest="f" * 64,
            role_contract_digest="1" * 64,
        )
        self.spec = supervisor.SupervisorSpec(
            Path("/repo"), Path(self.intent.workspace), "issue-implementer",
            "issue_452", self.intent.handoff_path, issue=452,
            repository="owner/repo", branch_name="codex/issue-452",
            expected_oid="a" * 40,
        )
        self.entry = {
            "workspace": self.intent.workspace,
            "handoff_path": self.intent.handoff_path,
        }

    def execute(self, lease, runner):
        def validate(*_args, **_kwargs):
            return lease

        patches = (
            mock.patch.object(supervisor.codex_launch_intent, "load_launch_intent",
                              return_value=self.intent),
            mock.patch.object(supervisor, "_spec_from_intent", return_value=self.spec),
            mock.patch.object(supervisor.secrets, "token_hex", return_value="1" * 32),
            mock.patch.object(supervisor, "_process_start_token", return_value="789"),
            mock.patch.object(
                supervisor.supervisor_workspace, "reserve_canonical_launch_attempt",
                return_value=(self.entry, None),
            ),
            mock.patch.object(supervisor, "validate_pre_spawn_authority",
                              side_effect=validate),
            mock.patch.object(supervisor, "build_codex_command", return_value=("codex",)),
            mock.patch.object(supervisor.supervisor_workspace, "one_by_task",
                              return_value=(Path("/repo"), self.entry)),
            mock.patch.object(supervisor, "_record_attempt"),
            mock.patch.object(supervisor.supervisor_workspace, "bind_thread"),
            mock.patch.object(supervisor, "_validate_handoff", return_value={}),
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
             patches[5], patches[6], patches[7], patches[8], patches[9], patches[10]:
            return supervisor.execute_launch_request(
                self.request, mode="run", now=NOW, runner=runner,
                compatibility_checker=lambda _command: {},
                broker_checker=lambda _command: None,
            )

    @staticmethod
    def successful_runner(_command, **kwargs):
        kwargs["on_process_started"](123, "456")
        kwargs["on_stdout_line"]('{"type":"thread.started","thread_id":"thread-1"}')
        kwargs["on_stdout_line"]('{"type":"turn.completed"}')
        return process_result()

    def test_production_entry_holds_writer_until_spawned_commit(self):
        lease = self.Lease()
        writer_started = threading.Event()
        writer_advanced = threading.Event()

        def writer():
            writer_started.set()
            if lease.wait_for_writer(1):
                writer_advanced.set()

        def runner(command, **kwargs):
            thread = threading.Thread(target=writer)
            thread.start()
            self.assertTrue(writer_started.wait(1))
            thread.join(0.05)
            self.assertFalse(writer_advanced.is_set())
            result = self.successful_runner(command, **kwargs)
            thread.join(1)
            self.assertTrue(writer_advanced.is_set())
            return result

        result = self.execute(lease, runner)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(lease.events[0][:3], ("spawned-commit", 123, "456"))
        self.assertTrue(lease.closed)

    def test_production_entry_returns_real_canonical_lease_to_process_callback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = root / ".worktrees" / "issue-452"
            child.mkdir(parents=True)
            runtime = root / "tmp" / "_codex_sessions" / "issue_452" / "runtime-home"
            runtime.mkdir(parents=True)
            for private in (root / "tmp", root / "tmp" / "_codex_sessions",
                            root / "tmp" / "_codex_sessions" / "issue_452", runtime):
                private.chmod(0o700)
            intent = replace(
                self.intent, workspace=str(child),
                runtime_root="tmp/_codex_sessions/issue_452/runtime-home",
                executable_evidence={
                    "codex": {"path": "/opt/codex", "sha256": "b" * 64},
                },
            )
            spec = replace(self.spec, repo_root=root, workspace=child)
            facts = workspace_boundary.GitFacts(
                str(child), str(root), ".worktrees/issue-452", "owner/repo",
                "codex/issue-452", "a" * 40,
            )
            worktree_ledger.update_ledger(root, lambda document: document["entries"].append({
                "entry_id": intent.ledger_entry_id, "platform": "codex-supervisor",
                "issue": 452, "agent_type": "issue-implementer", "round": None,
                "repository": "owner/repo", "workspace": str(child),
                "worktree_path": ".worktrees/issue-452",
                "branch_name": "codex/issue-452", "initial_oid": "a" * 40,
                "task_key": "issue_452", "handoff_path": intent.handoff_path,
                "protected_plan": [], "status": "open", "agent_id": None,
                "supervisor_attempts": [], "publish_attempts": [], "notes": [],
            }))
            profile = mock.Mock()
            profile.name = "issue-supervised"
            observed_lease = []
            original_validate = supervisor.validate_pre_spawn_authority
            writer_started = threading.Event()
            writer_advanced = threading.Event()

            def validate(*args, **kwargs):
                lease = original_validate(*args, **kwargs)
                observed_lease.append(lease)
                self.assertFalse(lease.closed)
                self.assertFalse(os.get_inheritable(lease._ledger_lease._fd))
                return lease

            def writer():
                writer_started.set()
                worktree_ledger.update_ledger(
                    root,
                    lambda document: document["entries"][0]["notes"].append({
                        "at": "after-spawned", "note": "cooperative writer",
                    }),
                )
                writer_advanced.set()

            def runner(_command, **kwargs):
                thread = threading.Thread(target=writer)
                thread.start()
                self.assertTrue(writer_started.wait(1))
                thread.join(0.05)
                self.assertFalse(writer_advanced.is_set())
                kwargs["on_process_started"](123, "456")
                thread.join(1)
                self.assertTrue(writer_advanced.is_set())
                kwargs["on_stdout_line"](
                    '{"type":"thread.started","thread_id":"thread-1"}'
                )
                kwargs["on_stdout_line"]('{"type":"turn.completed"}')
                return process_result()

            def command_setenv(_command, key):
                return {
                    "CODEX_ISSUE_ROLE": intent.role,
                    "CODEX_ISSUE_ROLE_CONTRACT_SHA256": intent.role_contract_digest,
                }[key]

            with mock.patch.object(
                supervisor.codex_launch_intent, "load_launch_intent", return_value=intent,
            ), mock.patch.object(
                supervisor, "_spec_from_intent", return_value=spec,
            ), mock.patch.object(
                workspace_boundary, "inspect_git_facts", return_value=facts,
            ), mock.patch.object(
                supervisor, "validate_pre_spawn_authority", side_effect=validate,
            ), mock.patch.object(
                supervisor, "build_codex_command", return_value=(intent.bwrap_executable,),
            ), mock.patch.object(
                supervisor, "_inner_config_values",
                return_value=(str(supervisor._CODEX_CONTROL_ALIAS), {}, str(runtime)),
            ), mock.patch.object(
                supervisor, "_inner_argv", return_value=(
                    str(supervisor._CODEX_CONTROL_ALIAS), "--profile",
                    intent.permission_profile,
                ),
            ), mock.patch.object(
                supervisor, "_command_setenv", side_effect=command_setenv,
            ), mock.patch.object(
                supervisor, "_ro_bind_source",
                return_value=Path(intent.executable_evidence["codex"]["path"]),
            ), mock.patch.object(
                supervisor, "validate_permission_profile", return_value=profile,
            ), mock.patch.object(
                supervisor, "_trusted_role_instructions",
                return_value=("role instructions", intent.role_contract_digest),
            ), mock.patch.object(
                supervisor, "_record_attempt",
            ), mock.patch.object(
                workspace_boundary, "bind_thread",
            ), mock.patch.object(
                supervisor, "_validate_handoff", return_value={},
            ):
                result = supervisor.execute_launch_request(
                    self.request, mode="run", now=NOW, runner=runner,
                    compatibility_checker=lambda _command: {},
                    broker_checker=lambda _command: None,
                )

            self.assertEqual(result.status, "succeeded")
            self.assertEqual(len(observed_lease), 1)
            self.assertTrue(observed_lease[0].closed)
            attempts = worktree_ledger.read_ledger(root)["entries"][0][
                "supervisor_attempts"
            ]
            self.assertEqual(attempts[-1]["state"], "spawned")

    def test_production_entry_releases_lease_on_popen_and_runner_failures(self):
        failures = (
            ("popen", supervisor.SubprocessJsonlRunner(
                popen=mock.Mock(side_effect=OSError("popen failed")),
            ), OSError),
            ("runner", lambda _command, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("runner failed")
            ), RuntimeError),
        )
        for label, runner, error_type in failures:
            with self.subTest(label=label):
                lease = self.Lease()
                with self.assertRaisesRegex(error_type, f"{label} failed"):
                    self.execute(lease, runner)
                self.assertTrue(lease.closed)
                self.assertTrue(lease.wait_for_writer(0.1))

    def test_production_entry_releases_lease_on_callback_and_commit_failures(self):
        failures = (
            ("callback", supervisor.CodexSupervisorError(
                "CODEX_SUPERVISOR_PROCESS_CALLBACK_FAILED"
            ), "PROCESS_CALLBACK_FAILED"),
            ("commit", workspace_boundary.SupervisorWorkspaceError(
                "CODEX_SUPERVISOR_LEDGER_WRITE_ERROR"
            ), "LEDGER_WRITE_ERROR"),
        )
        for label, error, reason in failures:
            with self.subTest(label=label):
                lease = self.Lease(record_error=error)
                with self.assertRaisesRegex(supervisor.CodexSupervisorError, reason):
                    self.execute(lease, self.successful_runner)
                self.assertTrue(lease.closed)
                self.assertTrue(lease.wait_for_writer(0.1))

    def test_production_owner_token_mismatch_releases_real_ledger_fd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = root / ".worktrees" / "issue-452"
            child.mkdir(parents=True)
            runtime = root / "runtime-home"
            runtime.mkdir(mode=0o700)
            intent = replace(
                self.intent, workspace=str(child), runtime_root="runtime-home",
                executable_evidence={
                    "codex": {"path": "/opt/codex", "sha256": "b" * 64},
                },
            )
            spec = replace(self.spec, repo_root=root, workspace=child)
            digest = supervisor.codex_launch_intent.intent_digest(intent)
            entry = {
                "entry_id": intent.ledger_entry_id, "platform": "codex-supervisor",
                "issue": 452, "agent_type": "issue-implementer", "round": None,
                "repository": "owner/repo", "workspace": str(child),
                "worktree_path": ".worktrees/issue-452",
                "branch_name": "codex/issue-452", "initial_oid": "a" * 40,
                "task_key": "issue_452", "handoff_path": intent.handoff_path,
                "protected_plan": [], "status": "running", "agent_id": None,
                "launch_intent_digest": digest, "publish_attempts": [], "notes": [],
                "supervisor_attempts": [{
                    "at": workspace_boundary.stamp(NOW), "attempt_id": "1" * 32,
                    "state": "reserved", "owner_pid": os.getpid(),
                    "owner_start_token": "0", "intent_digest": digest,
                    "lease_expires_at": workspace_boundary.stamp(NOW),
                    "transport_contract": "codex-supervisor/direct-exec-v2",
                    "resume_thread": None,
                }],
            }
            worktree_ledger.update_ledger(
                root, lambda document: document["entries"].append(entry)
            )
            facts = workspace_boundary.GitFacts(
                str(child), str(root), ".worktrees/issue-452", "owner/repo",
                "codex/issue-452", "a" * 40,
            )
            profile = mock.Mock()
            profile.name = intent.permission_profile
            runner = mock.Mock()

            def command_setenv(_command, key):
                return {
                    "CODEX_ISSUE_ROLE": intent.role,
                    "CODEX_ISSUE_ROLE_CONTRACT_SHA256": intent.role_contract_digest,
                }[key]

            with mock.patch.object(
                supervisor.codex_launch_intent, "load_launch_intent", return_value=intent,
            ), mock.patch.object(
                supervisor, "_spec_from_intent", return_value=spec,
            ), mock.patch.object(
                supervisor.secrets, "token_hex", return_value="1" * 32,
            ), mock.patch.object(
                supervisor, "_process_start_token", return_value="0",
            ), mock.patch.object(
                workspace_boundary, "inspect_git_facts", return_value=facts,
            ), mock.patch.object(
                workspace_boundary, "reserve_canonical_launch_attempt",
                return_value=(entry, None),
            ), mock.patch.object(
                supervisor, "build_codex_command", return_value=(intent.bwrap_executable,),
            ), mock.patch.object(
                supervisor, "_inner_config_values",
                return_value=(str(supervisor._CODEX_CONTROL_ALIAS), {}, str(runtime)),
            ), mock.patch.object(
                supervisor, "_inner_argv", return_value=(
                    str(supervisor._CODEX_CONTROL_ALIAS), "--profile",
                    intent.permission_profile,
                ),
            ), mock.patch.object(
                supervisor, "_command_setenv", side_effect=command_setenv,
            ), mock.patch.object(
                supervisor, "_ro_bind_source", return_value=Path("/opt/codex"),
            ), mock.patch.object(
                supervisor, "validate_permission_profile", return_value=profile,
            ), mock.patch.object(
                supervisor, "_trusted_role_instructions",
                return_value=("role instructions", intent.role_contract_digest),
            ), mock.patch.object(
                supervisor.supervisor_workspace, "one_by_task",
                return_value=(root, entry),
            ), mock.patch.object(supervisor, "_record_attempt"):
                with self.assertRaisesRegex(
                    supervisor.CodexSupervisorError, "ATTEMPT_FENCED",
                ):
                    supervisor.execute_launch_request(
                        self.request, mode="run", now=NOW, runner=runner,
                        compatibility_checker=lambda _command: {},
                        broker_checker=lambda _command: None,
                    )

            runner.assert_not_called()
            worktree_ledger.update_ledger(
                root, lambda document: document["entries"][0]["notes"].append({
                    "at": "after-fence", "note": "lock released",
                }),
            )


class SupervisedFlowTests(unittest.TestCase):
    def spec(self):
        return supervisor.SupervisorSpec(
            Path("/repo"), Path("/repo/.worktrees/issue-452"), "issue-implementer",
            "issue_452", "tmp/_handoff/issue-implementer--issue-452.yaml",
            issue=452, repository="owner/repo", branch_name="codex/issue-452",
            expected_oid="a" * 40,
        )

    def test_success_records_process_thread_and_success(self):
        events = []
        pre_spawn = mock.Mock(return_value=None)
        entry = {"workspace": str(self.spec().workspace), "handoff_path": self.spec().handoff_path}
        def runner(_command, **kwargs):
            kwargs["on_process_started"](123, "456")
            kwargs["on_stdout_line"]('{"type":"thread.started","thread_id":"thread-1"}')
            kwargs["on_stdout_line"]('{"type":"turn.completed"}')
            return process_result()
        with mock.patch.object(supervisor, "_reserve_attempt", return_value="1" * 32), \
             mock.patch.object(supervisor.supervisor_workspace, "one_by_task", return_value=(Path("/repo"), entry)), \
             mock.patch.object(supervisor, "build_codex_command", return_value=("codex",)), \
             mock.patch.object(supervisor, "_record_attempt", side_effect=lambda *a, **k: events.append(k["state"])), \
             mock.patch.object(supervisor.supervisor_workspace, "bind_thread"), \
             mock.patch.object(supervisor, "_validate_handoff", return_value={}), \
             mock.patch.object(supervisor, "validate_cli_compatibility"), \
             mock.patch.object(supervisor, "validate_broker_protocol"):
            result = supervisor.run_supervised(
                self.spec(), prompt="task", now=NOW, bwrap_executable="/bwrap",
                codex_executable="/codex", runner=runner,
                pre_spawn_validator=pre_spawn,
            )
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(events, ["spawned", "running", "succeeded"])
        pre_spawn.assert_called_once_with(("codex",), "1" * 32)

    def test_authority_lease_is_released_at_process_started_callback(self):
        order = []

        class Lease:
            def record_process_started(self, pid, token, *, now):
                order.append(("record", pid, token, now))

            def release(self):
                order.append(("release",))

        lease = Lease()

        def runner(_command, **kwargs):
            order.append(("runner-enter",))
            kwargs["on_process_started"](123, "456")
            order.append(("model-execution",))
            kwargs["on_stdout_line"]('{"type":"thread.started","thread_id":"thread-1"}')
            kwargs["on_stdout_line"]('{"type":"turn.completed"}')
            return process_result()

        entry = {"workspace": str(self.spec().workspace),
                 "handoff_path": self.spec().handoff_path}
        with mock.patch.object(supervisor, "_reserve_attempt", return_value="1" * 32), \
             mock.patch.object(supervisor.supervisor_workspace, "one_by_task",
                               return_value=(Path("/repo"), entry)), \
             mock.patch.object(supervisor, "build_codex_command", return_value=("codex",)), \
             mock.patch.object(supervisor, "_record_attempt"), \
             mock.patch.object(supervisor.supervisor_workspace, "bind_thread"), \
             mock.patch.object(supervisor, "_validate_handoff", return_value={}), \
             mock.patch.object(supervisor, "validate_cli_compatibility"), \
             mock.patch.object(supervisor, "validate_broker_protocol"):
            supervisor.run_supervised(
                self.spec(), prompt="task", now=NOW, bwrap_executable="/bwrap",
                codex_executable="/codex", runner=runner,
                pre_spawn_validator=lambda _command, _attempt: lease,
            )
        self.assertEqual([item[0] for item in order],
                         ["runner-enter", "record", "release", "model-execution"])

    def test_runner_exception_before_callback_releases_authority_lease(self):
        lease = mock.Mock()
        entry = {"workspace": str(self.spec().workspace),
                 "handoff_path": self.spec().handoff_path}
        with mock.patch.object(supervisor, "_reserve_attempt", return_value="1" * 32), \
             mock.patch.object(supervisor.supervisor_workspace, "one_by_task",
                               return_value=(Path("/repo"), entry)), \
             mock.patch.object(supervisor, "build_codex_command", return_value=("codex",)), \
             mock.patch.object(supervisor, "_record_attempt"), \
             mock.patch.object(supervisor, "validate_cli_compatibility"), \
             mock.patch.object(supervisor, "validate_broker_protocol"), \
             self.assertRaisesRegex(OSError, "popen failed"):
            supervisor.run_supervised(
                self.spec(), prompt="task", now=NOW, bwrap_executable="/bwrap",
                codex_executable="/codex",
                runner=lambda _command, **_kwargs: (_ for _ in ()).throw(
                    OSError("popen failed")
                ),
                pre_spawn_validator=lambda _command, _attempt: lease,
            )
        lease.release.assert_called_once_with()
        lease.record_process_started.assert_not_called()

    def test_each_authority_race_fails_before_popen(self):
        races = ("plan", "manifest", "issue", "karte", "ledger", "role",
                 "executable", "git")
        for label in races:
            with self.subTest(label=label):
                runner = mock.Mock()
                def reject(_command, _attempt_id, label=label):
                    raise supervisor.CodexSupervisorError(
                        "CODEX_SUPERVISOR_INTENT_CHANGED", label
                    )
                with mock.patch.object(supervisor, "_reserve_attempt", return_value="1" * 32), \
                     mock.patch.object(supervisor.supervisor_workspace, "one_by_task", return_value=(
                         Path("/repo"), {"workspace": str(self.spec().workspace)}
                     )), mock.patch.object(supervisor, "build_codex_command", return_value=("codex",)), \
                     mock.patch.object(supervisor, "_record_attempt"), \
                     mock.patch.object(supervisor, "validate_cli_compatibility"), \
                     mock.patch.object(supervisor, "validate_broker_protocol"):
                    with self.assertRaisesRegex(
                        supervisor.CodexSupervisorError, "INTENT_CHANGED"
                    ):
                        supervisor.run_supervised(
                            self.spec(), prompt="task", now=NOW,
                            bwrap_executable="/bwrap", codex_executable="/codex",
                            runner=runner, pre_spawn_validator=reject,
                        )
                runner.assert_not_called()

    def test_pre_spawn_comparison_detects_each_authority_evidence_change(self):
        base = supervisor.codex_launch_intent.LaunchIntent(
            schema_version="codex-launch-intent/1", issue=452,
            role="issue-implementer", round_number=1, change_plan_id="plan-452",
            repository="owner/repo", workspace="/repo/.worktrees/issue-452",
            branch_name="codex/issue-452", expected_oid="a" * 40,
            task_key="issue_452",
            handoff_path="tmp/_handoff/issue-implementer--issue-452.yaml",
            model="gpt-5.6-sol", reasoning_effort="xhigh",
            bwrap_executable="/usr/bin/bwrap", codex_executable="/opt/codex",
            executable_evidence={"codex": {"sha256": "b" * 64}},
            permission_profile="issue-supervised",
            runtime_root="tmp/_codex_sessions/issue_452/runtime-home",
            protected_paths=(), finding_ids=(),
            source_provenance={"issue": {"sha256": "c" * 64}}, prompt="task",
            ledger_entry_id="wl-123456789abc", plan_digest="d" * 64,
            manifest_digest="e" * 64, canonical_entry_digest="f" * 64,
            role_contract_digest="1" * 64,
        )
        changes = {
            "plan": {"plan_digest": "2" * 64},
            "manifest": {"manifest_digest": "2" * 64},
            "issue": {"source_provenance": {"issue": {"sha256": "2" * 64}}},
            "karte": {"source_provenance": {
                "issue": {"sha256": "c" * 64},
                "karte": {"sha256": "2" * 64},
            }},
            "ledger": {"canonical_entry_digest": "2" * 64},
            "role": {"role_contract_digest": "2" * 64},
            "executable": {"executable_evidence": {
                "codex": {"sha256": "2" * 64},
            }},
            "git": {"expected_oid": "2" * 40},
        }
        request = supervisor.codex_launch_intent.LaunchRequest(
            452, "issue-implementer", "plan-452"
        )
        ledger_verify = mock.Mock()
        for label, update in changes.items():
            with self.subTest(label=label), mock.patch.object(
                supervisor.codex_launch_intent, "load_launch_intent",
                return_value=replace(base, **update),
            ), mock.patch.object(
                supervisor.supervisor_workspace,
                "verify_canonical_launch_reservation", ledger_verify,
            ), self.assertRaisesRegex(
                supervisor.CodexSupervisorError, "INTENT_CHANGED",
            ):
                supervisor.validate_pre_spawn_authority(
                    request, base, self.spec(),
                    digest=supervisor.codex_launch_intent.intent_digest(base),
                    command=(), attempt_id="1" * 32, owner_pid=os.getpid(),
                    owner_start_token="1",
                )
        ledger_verify.assert_not_called()

    def test_default_preflight_fails_before_process_when_read_deny_is_unavailable(self):
        command = (
            "bwrap", "--setenv", "CODEX_HOME", "/runtime", "--", "codex", "exec",
            "-C", "/repo/.worktrees/issue-452",
            "--sandbox", "workspace-write", "--config",
            "sandbox_workspace_write.network_access=false", "--config",
            'shell_environment_policy.inherit="none"', "--config",
            "features.multi_agent=false", "--config", "agents.enabled=false", "-",
        )
        runner = mock.Mock()
        with mock.patch.object(supervisor, "_reserve_attempt", return_value="a" * 32), \
             mock.patch.object(supervisor.supervisor_workspace, "one_by_task", return_value=(
                 Path("/repo"), {"workspace": str(self.spec().workspace)}
             )), mock.patch.object(supervisor, "build_codex_command", return_value=command), \
             mock.patch.object(supervisor, "_record_attempt"):
            with self.assertRaisesRegex(
                supervisor.CodexSupervisorError, "LEGACY_SANDBOX_PRESENT"
            ):
                supervisor.run_supervised(
                    self.spec(), prompt="task", now=NOW, bwrap_executable="/bwrap",
                    codex_executable="/codex", runner=runner,
                )
        runner.assert_not_called()

    def test_default_preflight_not_tested_records_nonpass_security_completion(self):
        command = ("bwrap", "--", "codex", "exec", "-")
        runner = mock.Mock()
        evidence = []
        with mock.patch.object(supervisor, "_reserve_attempt", return_value="a" * 32), \
             mock.patch.object(supervisor.supervisor_workspace, "one_by_task", return_value=(
                 Path("/repo"), {"workspace": str(self.spec().workspace)}
             )), mock.patch.object(supervisor, "build_codex_command", return_value=command), \
             mock.patch.object(
                 supervisor, "_record_attempt",
                 side_effect=lambda *args, **kwargs: evidence.append(kwargs["evidence"]),
             ), mock.patch.object(
                 supervisor, "validate_cli_compatibility",
                 side_effect=supervisor.CodexSupervisorError("CODEX_SUPERVISOR_PROBE_NOT_TESTED"),
             ):
            with self.assertRaisesRegex(
                supervisor.CodexSupervisorError, "PROBE_NOT_TESTED"
            ):
                supervisor.run_supervised(
                    self.spec(), prompt="task", now=NOW, bwrap_executable="/bwrap",
                    codex_executable="/codex", runner=runner,
                )
        self.assertEqual(evidence[-1]["security_completion"], "NOT_TESTED")
        runner.assert_not_called()

    def test_rate_limit_returns_resume_availability_without_raw_command(self):
        entry = {"workspace": str(self.spec().workspace), "handoff_path": self.spec().handoff_path}
        def runner(_command, **kwargs):
            kwargs["on_process_started"](123, "456")
            kwargs["on_stdout_line"]('{"type":"thread.started","thread_id":"thread-1"}')
            kwargs["on_stdout_line"]('{"type":"error","message":"usage limit"}')
            return process_result(exit_code=1)
        with mock.patch.object(supervisor, "_reserve_attempt", return_value="1" * 32), \
             mock.patch.object(supervisor.supervisor_workspace, "one_by_task", return_value=(Path("/repo"), entry)), \
             mock.patch.object(supervisor, "build_codex_command", return_value=("run",)), \
             mock.patch.object(supervisor, "_record_attempt"), \
             mock.patch.object(supervisor.supervisor_workspace, "bind_thread"), \
             mock.patch.object(supervisor, "validate_cli_compatibility"), \
             mock.patch.object(supervisor, "validate_broker_protocol"):
            result = supervisor.run_supervised(
                self.spec(), prompt="task", now=NOW, bwrap_executable="/bwrap",
                codex_executable="/codex", runner=runner,
            )
        self.assertEqual(result.status, "paused_rate_limit")
        self.assertTrue(result.resume_available)
        self.assertFalse(hasattr(result, "resume_command"))


class PublishAndPatchTests(unittest.TestCase):
    def test_role_publish_asymmetry_and_reviewer_is_not_a_supervised_role(self):
        self.assertIn("gh.pr.create", supervisor.publish_allowlist("issue-implementer"))
        self.assertNotIn("gh.pr.create", supervisor.publish_allowlist("issue-fixer"))
        with self.assertRaisesRegex(supervisor.CodexSupervisorError, "ROLE_INVALID"):
            supervisor.publish_allowlist("pr-reviewer")

    def test_protected_patch_requires_exact_owner_plan_and_atomic_base(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / ".codex" / "agents" / "role.toml"
            target.parent.mkdir(parents=True)
            target.write_text("old", encoding="utf-8")
            digest = hashlib.sha256(b"old").hexdigest()
            document = {"schema_version": 1, "role": "issue-implementer", "operations": [{
                "path": ".codex/agents/role.toml", "base_sha256": digest,
                "content_base64": base64.b64encode(b"new").decode("ascii"),
            }]}
            operations = supervisor.validate_protected_patch(
                root, document, role="issue-implementer",
                allowed_paths={".codex/agents/role.toml"},
            )
            self.assertEqual(supervisor.apply_protected_patch(root, operations),
                             (".codex/agents/role.toml",))
            self.assertEqual(target.read_text(encoding="utf-8"), "new")
            with self.assertRaisesRegex(supervisor.CodexSupervisorError, "BASE_MISMATCH"):
                supervisor.validate_protected_patch(
                    root, document, role="issue-implementer",
                    allowed_paths={".codex/agents/role.toml"},
                )


if __name__ == "__main__":
    unittest.main()
