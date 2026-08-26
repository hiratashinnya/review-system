"""Issue #452: Codex durable workspace binding の unit / 実 git integration。"""

import io
import json
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from issue_start import worktree_ledger
from issue_start.codex_binding import (
    CodexBindingError,
    collect_binding,
    consume_spawn_binding,
    inspect_git_facts,
    prepare_binding,
    release_binding,
    run_hook,
    verify_command_binding,
)
from issue_start.gate import CodexIsolationOnlyAck, parse_dispatch_payload


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

    def consume(self, **overrides):
        values = {
            "repo_root": self.workspace,
            "workspace": self.workspace,
            "role": "issue-implementer",
            "task_key": self.task_key,
            "now": NOW + timedelta(seconds=1),
        }
        values.update(overrides)
        return consume_spawn_binding(**values)

    def test_prepare_consume_verify_collect_release_lifecycle(self):
        prepared = self.prepare()
        self.assertEqual(prepared["status"], "open")
        self.assertEqual(prepared["platform"], "codex")
        self.assertEqual(prepared["worktree_path"], ".worktrees/issue-10")
        running = self.consume()
        self.assertEqual(running["status"], "running")
        verified = verify_command_binding(
            repo_root=self.workspace,
            workspace=self.workspace,
            role="issue-implementer",
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

    def test_task_reuse_and_expired_prepare_fail_close(self):
        self.prepare()
        self.consume()
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_TASK_REUSED"):
            self.consume(now=NOW + timedelta(seconds=2))

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
            consume_spawn_binding(
                repo_root=second, workspace=second, role="issue-implementer",
                task_key="issue_11", now=NOW + timedelta(seconds=31),
            )
        entries = worktree_ledger.read_ledger(self.main)["entries"]
        expired = next(item for item in entries if item.get("task_key") == "issue_11")
        self.assertEqual(expired["status"], "open")

    def test_wrong_cwd_origin_branch_and_stale_oid_fail_close(self):
        self.prepare()
        self.consume()
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_ACTIVE_MISSING"):
            verify_command_binding(
                repo_root=self.workspace, workspace=self.main, role="issue-implementer"
            )

        git(self.workspace, "remote", "set-url", "origin", "https://github.com/evil/repo.git")
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_ORIGIN_MISMATCH"):
            verify_command_binding(
                repo_root=self.workspace, workspace=self.workspace, role="issue-implementer"
            )
        git(self.workspace, "remote", "set-url", "origin", "https://github.com/example/repo.git")

        git(self.workspace, "switch", "-c", "codex/wrong-branch")
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_BRANCH_MISMATCH"):
            verify_command_binding(
                repo_root=self.workspace, workspace=self.workspace, role="issue-implementer"
            )
        git(self.workspace, "switch", "codex/issue-10")

        # amend は expected OID と親子関係のない HEAD を作る。
        (self.workspace / "seed.txt").write_text("rewritten\n", encoding="utf-8")
        git(self.workspace, "add", "seed.txt")
        git(self.workspace, "commit", "--amend", "-m", "rewritten root")
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_STALE_OID"):
            verify_command_binding(
                repo_root=self.workspace, workspace=self.workspace, role="issue-implementer"
            )

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

    def test_hook_requires_active_binding_for_target_roles_and_skips_others(self):
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
        self.consume()
        stdout = io.StringIO()
        run_hook(
            stdin=io.StringIO(json.dumps({
                "agent_type": "issue-implementer", "cwd": str(self.workspace),
                "tool_name": "apply_patch", "tool_input": {},
            })),
            stdout=stdout, stderr=io.StringIO(), cwd=self.workspace,
        )
        self.assertEqual(stdout.getvalue(), "")
        unmanaged = io.StringIO()
        run_hook(
            stdin=io.StringIO(json.dumps({"agent_type": "pr-reviewer"})),
            stdout=unmanaged, stderr=io.StringIO(), cwd=self.workspace,
        )
        self.assertEqual(unmanaged.getvalue(), "")

    def test_codex_fixer_transport_consumes_the_canonical_round_task(self):
        prepare_binding(
            issue=10, round_number=2, repository=REPOSITORY, workspace=self.workspace,
            branch_name="codex/issue-10", expected_oid=self.oid,
            handoff_path="tmp/_handoff/issue-fixer--issue-10-r2.yaml",
            role="issue-fixer", task_key="issue_10_fix_r2", now=NOW,
        )
        payload = {
            "cwd": str(self.workspace),
            "tool_name": "collaborationspawn_agent",
            "tool_input": {
                "agent_type": "issue-fixer",
                "task_name": "issue_10_fix_r2",
                "message": "ENC[not-a-binding]",
            },
        }
        ack = parse_dispatch_payload(payload, cwd=self.workspace, now=NOW + timedelta(seconds=1))
        self.assertIsInstance(ack, CodexIsolationOnlyAck)
        self.assertEqual((ack.issue, ack.round, ack.repository), (10, 2, REPOSITORY))
        self.assertEqual(ack.handoff_path, "tmp/_handoff/issue-fixer--issue-10-r2.yaml")
        with self.assertRaisesRegex(CodexBindingError, "CODEX_BINDING_TASK_REUSED"):
            consume_spawn_binding(
                repo_root=self.workspace, workspace=self.workspace, role="issue-fixer",
                task_key="issue_10_fix_r2", now=NOW + timedelta(seconds=2),
            )


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
