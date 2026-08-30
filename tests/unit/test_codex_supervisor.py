import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from issue_start import worktree_ledger
from issue_start.codex_binding import prepare_binding
from issue_start.codex_supervisor import (
    CodexSupervisorError,
    ProcessResult,
    SupervisorSpec,
    apply_protected_patch,
    build_codex_command,
    build_sandbox_probe_command,
    publish_allowlist,
    run_supervised,
    validate_protected_patch,
    validate_probe_result,
)


NOW = datetime(2026, 8, 30, 0, 0, tzinfo=timezone.utc)


def git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


class FakeRunner:
    def __init__(
        self,
        lines,
        *,
        exit_code=0,
        timed_out=False,
        killed=False,
        announce_process=True,
    ):
        self.lines = list(lines)
        self.exit_code = exit_code
        self.timed_out = timed_out
        self.killed = killed
        self.announce_process = announce_process
        self.calls = []

    def __call__(
        self,
        command,
        *,
        cwd,
        env,
        prompt,
        timeout_seconds,
        on_process_started,
        on_stdout_line,
    ):
        self.calls.append((tuple(command), cwd, prompt, timeout_seconds))
        if self.announce_process:
            on_process_started(4242, "123456")
        for line in self.lines:
            on_stdout_line(line)
        return ProcessResult(
            pid=4242,
            process_start_token="123456",
            exit_code=self.exit_code,
            stdout=tuple(self.lines),
            stderr=(),
            timed_out=self.timed_out,
            killed=self.killed,
        )


class CodexSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.main = Path(self.temp.name) / "main"
        self.main.mkdir()
        git(self.main, "init", "-b", "main")
        git(self.main, "config", "user.email", "test@example.invalid")
        git(self.main, "config", "user.name", "Supervisor Test")
        git(self.main, "remote", "add", "origin", "https://github.com/example/repo.git")
        (self.main / ".codex").mkdir()
        (self.main / ".agents").mkdir()
        (self.main / ".codex" / "seed").write_text("seed\n", encoding="utf-8")
        (self.main / ".agents" / "seed").write_text("seed\n", encoding="utf-8")
        (self.main / "seed.txt").write_text("seed\n", encoding="utf-8")
        git(self.main, "add", ".")
        git(self.main, "commit", "-m", "seed")
        self.workspace = self.main / ".worktrees" / "issue-10"
        self.workspace.parent.mkdir()
        git(self.main, "worktree", "add", "-b", "codex/issue-10", str(self.workspace), "HEAD")
        self.oid = git(self.workspace, "rev-parse", "HEAD")
        self.handoff = "tmp/_handoff/issue-implementer--issue-10.yaml"
        self.task_key = "issue_10"
        self.bin_dir = Path(self.temp.name) / "bin"
        self.bin_dir.mkdir()
        self.bwrap = self.bin_dir / "bwrap"
        self.codex = self.bin_dir / "codex"
        for executable in (self.bwrap, self.codex):
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
        prepare_binding(
            issue=10,
            round_number=1,
            repository="example/repo",
            workspace=self.workspace,
            branch_name="codex/issue-10",
            expected_oid=self.oid,
            handoff_path=self.handoff,
            role="issue-implementer",
            task_key=self.task_key,
            now=NOW,
        )
        self.spec = SupervisorSpec(
            repo_root=self.workspace,
            workspace=self.workspace,
            role="issue-implementer",
            task_key=self.task_key,
            handoff_path=self.handoff,
            timeout_seconds=30,
        )

    def handoff_file(self):
        target = self.workspace / self.handoff
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("status: ready\n", encoding="utf-8")

    def run_supervisor(self, runner, **overrides):
        values = {
            "spec": self.spec,
            "prompt": "Implement only the assigned work unit.",
            "now": NOW + timedelta(seconds=1),
            "bwrap_executable": self.bwrap,
            "codex_executable": self.codex,
            "runner": runner,
        }
        values.update(overrides)
        return run_supervised(**values)

    @staticmethod
    def success_lines(thread="thread-10"):
        return [
            json.dumps({"type": "thread.started", "thread_id": thread}),
            json.dumps({"type": "turn.started"}),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1}}),
        ]

    def entry(self):
        document = worktree_ledger.read_ledger(self.main)
        return next(item for item in document["entries"] if item.get("task_key") == self.task_key)

    def assert_reason(self, reason, runner, **overrides):
        with self.assertRaises(CodexSupervisorError) as caught:
            self.run_supervisor(runner, **overrides)
        self.assertEqual(caught.exception.reason, reason)

    def test_success_binds_only_after_process_and_thread_then_records_evidence(self):
        self.handoff_file()
        runner = FakeRunner(self.success_lines())

        result = self.run_supervisor(runner)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.thread_id, "thread-10")
        entry = self.entry()
        self.assertEqual(entry["status"], "running")
        self.assertEqual(entry["agent_id"], "thread-10")
        states = [attempt["state"] for attempt in entry["supervisor_attempts"]]
        self.assertEqual(states, ["spawned", "running", "succeeded"])
        self.assertEqual(entry["supervisor_attempts"][0]["pid"], 4242)
        self.assertEqual(entry["supervisor_attempts"][0]["process_start_token"], "123456")

    def test_command_pins_model_reasoning_sandbox_and_disabled_capabilities(self):
        command = build_codex_command(
            self.spec, bwrap_executable=self.bwrap, codex_executable=self.codex
        )
        joined = " ".join(command)
        self.assertIn("--unshare-net", command)
        self.assertIn("--sandbox workspace-write", joined)
        self.assertIn("--ask-for-approval never", joined)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--json", command)
        self.assertIn("--model gpt-5.6-sol", joined)
        self.assertIn('model_reasoning_effort="xhigh"', command)
        self.assertIn('web_search="disabled"', command)
        self.assertIn("sandbox_workspace_write.network_access=false", command)
        self.assertIn("agents.enabled=false", command)
        self.assertIn("features.multi_agent=false", command)
        for protected in (".git", ".codex", ".agents"):
            target = str(self.workspace / protected)
            index = command.index(target)
            self.assertEqual(command[index - 1], "--ro-bind")

    def test_missing_duplicate_and_malformed_jsonl_fail_close(self):
        self.assert_reason(
            "CODEX_SUPERVISOR_THREAD_MISSING",
            FakeRunner([json.dumps({"type": "turn.started"})]),
        )

        with self.subTest("duplicate"):
            self.setUp()
            self.addCleanup(self.temp.cleanup)
            self.assert_reason(
                "CODEX_SUPERVISOR_THREAD_DUPLICATE",
                FakeRunner([
                    json.dumps({"type": "thread.started", "thread_id": "thread-10"}),
                    json.dumps({"type": "thread.started", "thread_id": "thread-10"}),
                ]),
            )

        with self.subTest("malformed"):
            self.setUp()
            self.addCleanup(self.temp.cleanup)
            self.assert_reason("CODEX_SUPERVISOR_JSONL_MALFORMED", FakeRunner(["{"]))

    def test_nonzero_timeout_kill_and_missing_handoff_fail_close(self):
        cases = [
            ("CODEX_SUPERVISOR_EXIT_NONZERO", FakeRunner(self.success_lines(), exit_code=7), True),
            ("CODEX_SUPERVISOR_TIMEOUT", FakeRunner(self.success_lines(), timed_out=True, killed=True), True),
            ("CODEX_SUPERVISOR_KILLED", FakeRunner(self.success_lines(), killed=True), True),
            ("CODEX_SUPERVISOR_HANDOFF_MISSING", FakeRunner(self.success_lines()), False),
        ]
        for reason, runner, create_handoff in cases:
            with self.subTest(reason=reason):
                self.setUp()
                self.addCleanup(self.temp.cleanup)
                if create_handoff:
                    self.handoff_file()
                self.assert_reason(reason, runner)
                self.assertNotIn(self.entry()["status"], worktree_ledger.TERMINAL_STATUSES)

    def test_rate_limit_pauses_and_resume_keeps_thread_model_reasoning_and_workspace(self):
        runner = FakeRunner([
            json.dumps({"type": "thread.started", "thread_id": "thread-10"}),
            json.dumps({"type": "error", "message": "rate limit exceeded"}),
        ], exit_code=1)

        result = self.run_supervisor(runner)

        self.assertEqual(result.status, "paused_rate_limit")
        self.assertIsNotNone(result.resume_command)
        joined = " ".join(result.resume_command or ())
        self.assertIn("resume thread-10 -", joined)
        self.assertIn("--model gpt-5.6-sol", joined)
        self.assertIn('model_reasoning_effort="xhigh"', result.resume_command or ())
        self.assertIn(str(self.workspace), result.resume_command or ())
        self.assertEqual(self.entry()["status"], "running")

    def test_resume_rejects_a_different_thread(self):
        first = FakeRunner([
            json.dumps({"type": "thread.started", "thread_id": "thread-10"}),
            json.dumps({"type": "error", "message": "rate limit exceeded"}),
        ], exit_code=1)
        self.run_supervisor(first)
        second = FakeRunner(self.success_lines("thread-other"))

        self.assert_reason(
            "CODEX_SUPERVISOR_RESUME_THREAD_MISMATCH",
            second,
            now=NOW + timedelta(seconds=2),
            resume_thread="thread-10",
        )

    def test_denied_web_or_redelegation_event_fails_close(self):
        for item_type in ("web_search", "collaboration_tool_call"):
            with self.subTest(item_type=item_type):
                self.setUp()
                self.addCleanup(self.temp.cleanup)
                self.assert_reason(
                    "CODEX_SUPERVISOR_DENIED_TOOL_EVENT",
                    FakeRunner([
                        json.dumps({"type": "thread.started", "thread_id": "thread-10"}),
                        json.dumps({"type": "item.started", "item": {"type": item_type}}),
                    ]),
                )

    def test_process_identity_must_precede_thread(self):
        self.assert_reason(
            "CODEX_SUPERVISOR_PROCESS_IDENTITY_MISSING",
            FakeRunner(self.success_lines(), announce_process=False),
        )

    def test_handoff_symlink_is_rejected(self):
        target = self.workspace / "actual.yaml"
        target.write_text("status: ready\n", encoding="utf-8")
        handoff = self.workspace / self.handoff
        handoff.parent.mkdir(parents=True)
        handoff.symlink_to(target)

        self.assert_reason(
            "CODEX_BINDING_HANDOFF_SYMLINK", FakeRunner(self.success_lines())
        )

    def test_publish_allowlist_preserves_role_asymmetry_and_merge_denial(self):
        implementer = publish_allowlist("issue-implementer")
        fixer = publish_allowlist("issue-fixer")
        self.assertIn("gh.pr.create", implementer)
        self.assertNotIn("gh.pr.create", fixer)
        for actions in (implementer, fixer):
            self.assertNotIn("git.merge", actions)
            self.assertNotIn("gh.pr.merge", actions)

    def test_probe_validator_requires_exact_boundary_result(self):
        expected = {
            "workspace": True,
            "main": False,
            "git": False,
            "codex": False,
            "agents": False,
            "tmp_private": True,
            "network": False,
        }
        self.assertEqual(validate_probe_result(json.dumps(expected), 0), expected)
        expected["main"] = True
        with self.assertRaisesRegex(CodexSupervisorError, "BOUNDARY_MISMATCH"):
            validate_probe_result(json.dumps(expected), 0)

    def test_protected_patch_requires_owner_exact_path_digest_and_schema(self):
        relative = ".codex/seed"
        target = self.workspace / relative
        original = target.read_bytes()
        replacement = b"updated\n"
        document = {
            "schema_version": 1,
            "role": "issue-implementer",
            "operations": [{
                "path": relative,
                "base_sha256": hashlib.sha256(original).hexdigest(),
                "content_base64": base64.b64encode(replacement).decode("ascii"),
            }],
        }

        operations = validate_protected_patch(
            self.workspace,
            document,
            role="issue-implementer",
            allowed_paths={relative},
        )
        self.assertEqual(apply_protected_patch(self.workspace, operations), (relative,))
        self.assertEqual(target.read_bytes(), replacement)

        for mutation, reason in (
            ({"allowed_paths": set()}, "PATCH_PATH_NOT_APPROVED"),
            ({"allowed_paths": {".codex/../seed"}}, "PATCH_PATH_INVALID"),
        ):
            with self.subTest(reason=reason):
                candidate = dict(document)
                candidate["operations"] = [dict(document["operations"][0])]
                if ".." in next(iter(mutation["allowed_paths"]), ""):
                    candidate["operations"][0]["path"] = ".codex/../seed"
                with self.assertRaisesRegex(CodexSupervisorError, reason):
                    validate_protected_patch(
                        self.workspace,
                        candidate,
                        role="issue-implementer",
                        allowed_paths=mutation["allowed_paths"],
                    )

    def test_protected_patch_rechecks_base_before_apply(self):
        relative = ".agents/seed"
        target = self.workspace / relative
        original = target.read_bytes()
        document = {
            "schema_version": 1,
            "role": "issue-fixer",
            "operations": [{
                "path": relative,
                "base_sha256": hashlib.sha256(original).hexdigest(),
                "content_base64": base64.b64encode(b"fixed\n").decode("ascii"),
            }],
        }
        operations = validate_protected_patch(
            self.workspace, document, role="issue-fixer", allowed_paths={relative}
        )
        target.write_text("raced\n", encoding="utf-8")

        with self.assertRaisesRegex(CodexSupervisorError, "PATCH_TARGET_CHANGED"):
            apply_protected_patch(self.workspace, operations)


class BubblewrapSandboxProbeTests(unittest.TestCase):
    def test_model_free_probe_allows_only_worktree_and_private_tmp(self):
        bwrap = shutil.which("bwrap")
        if bwrap is None:
            self.skipTest("bubblewrap is not installed")
        # fixture 自体を /tmp 配下へ置くと、検証対象の private tmpfs が
        # fixture mount を隠すため、repository workspace 配下に一時作成する。
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            main = Path(temporary) / "main"
            main.mkdir()
            git(main, "init", "-b", "main")
            git(main, "config", "user.email", "test@example.invalid")
            git(main, "config", "user.name", "Sandbox Probe")
            (main / ".codex").mkdir()
            (main / ".agents").mkdir()
            (main / ".codex" / "seed").write_text("seed\n", encoding="utf-8")
            (main / ".agents" / "seed").write_text("seed\n", encoding="utf-8")
            (main / "seed.txt").write_text("seed\n", encoding="utf-8")
            git(main, "add", ".")
            git(main, "commit", "-m", "seed")
            workspace = main / ".worktrees" / "probe"
            workspace.parent.mkdir()
            git(main, "worktree", "add", "-b", "probe", str(workspace), "HEAD")
            command = build_sandbox_probe_command(
                workspace, bwrap_executable=bwrap, python_executable=sys.executable
            )

            completed = subprocess.run(
                command, cwd=workspace, capture_output=True, text=True, timeout=15
            )

            if completed.returncode != 0 and "Operation not permitted" in completed.stderr:
                self.skipTest("kernel does not permit unprivileged bubblewrap namespaces")
            try:
                validate_probe_result(completed.stdout, completed.returncode)
            except CodexSupervisorError as exc:
                self.fail(
                    f"sandbox probe failed: {exc}; stdout={completed.stdout!r}; "
                    f"stderr={completed.stderr!r}"
                )
            self.assertFalse((main / ".supervisor-probe").exists())
            self.assertFalse((workspace / ".supervisor-probe").exists())


if __name__ == "__main__":
    unittest.main()
