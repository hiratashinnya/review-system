import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from issue_start import codex_exec_broker, worktree_ledger
from issue_start.codex_binding import prepare_binding
from issue_start.codex_exec_broker import BOUNDARY_VERSION, Broker, BrokerError, _tool_schema
from issue_start.codex_supervisor import SupervisorSpec, _reserve_attempt


NOW = datetime(2026, 9, 5, tzinfo=timezone.utc)


def git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=True
    )
    return completed.stdout.strip()


class CodexExecBrokerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.temporary.cleanup)
        self.main = Path(self.temporary.name) / "main"
        self.main.mkdir()
        git(self.main, "init", "-b", "main")
        git(self.main, "config", "user.email", "broker@example.invalid")
        git(self.main, "config", "user.name", "Broker Test")
        git(self.main, "remote", "add", "origin", "https://github.com/example/repo.git")
        (self.main / ".codex").mkdir()
        (self.main / ".agents").mkdir()
        (self.main / ".ai/agents").mkdir(parents=True)
        (self.main / ".ai/agents/issue-implementer.md").write_text("role\n", encoding="utf-8")
        (self.main / "seed.txt").write_text("needle\n", encoding="utf-8")
        (self.main / ".gitignore").write_text("tmp/\n", encoding="utf-8")
        git(self.main, "add", ".")
        git(self.main, "commit", "-m", "seed")
        self.workspace = self.main / ".worktrees/broker"
        self.workspace.parent.mkdir()
        git(self.main, "worktree", "add", "-b", "codex/broker", str(self.workspace), "HEAD")
        self.handoff = "tmp/_handoff/issue-implementer--issue-452-f19.yaml"
        self.task_key = "issue_452"
        oid = git(self.workspace, "rev-parse", "HEAD")
        prepare_binding(
            issue=452, round_number=1, repository="example/repo", workspace=self.workspace,
            branch_name="codex/broker", expected_oid=oid, handoff_path=self.handoff,
            role="issue-implementer", task_key=self.task_key, protected_paths=(), now=NOW,
        )
        self.spec = SupervisorSpec(
            repo_root=self.workspace, workspace=self.workspace, role="issue-implementer",
            task_key=self.task_key, handoff_path=self.handoff,
        )
        self.fence = "b" * 32
        self.attempt = _reserve_attempt(
            self.spec, now=NOW, resume_thread=None, broker_fence=self.fence
        )
        self.bwrap = shutil.which("bwrap") or "/usr/bin/false"
        source = Path(codex_exec_broker.__file__).resolve()
        self.broker_args = {
            "ledger": worktree_ledger.ledger_path(self.main), "workspace": self.workspace,
            "role": "issue-implementer", "task_key": self.task_key,
            "attempt_id": self.attempt, "fence": self.fence, "handoff_path": self.handoff,
            "bwrap": Path(self.bwrap), "python": Path("/usr/bin/python3"),
            "git_common": self.main / ".git",
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
        boundary = mock.patch.dict(
            os.environ, {"CODEX_EXEC_BROKER_BOUNDARY": BOUNDARY_VERSION}
        )
        boundary.start()
        self.addCleanup(boundary.stop)
        self.broker = Broker(**self.broker_args)

    def request(self, action, params, *, request_id="request-1", pty=False, **changes):
        value = {
            "task_key": self.task_key, "attempt_id": self.attempt,
            "fence": self.fence, "role": "issue-implementer",
            "workspace": str(self.workspace.resolve()), "cwd": ".",
            "request_id": request_id, "timeout_seconds": 30,
            "action": action, "params": params, "pty": pty,
        }
        value.update(changes)
        return value

    def events(self):
        document = worktree_ledger.read_ledger(self.main)
        entry = next(item for item in document["entries"] if item["task_key"] == self.task_key)
        return entry["broker_events"]

    def test_direct_read_list_search_and_bound_handoff_write(self):
        read = self.broker.execute(self.request(
            "read_file", {"path": "seed.txt", "max_bytes": 100}
        ))
        listed = self.broker.execute(self.request(
            "list_files", {"path": ".", "max_entries": 100}, request_id="request-2"
        ))
        searched = self.broker.execute(self.request(
            "search_text", {"path": ".", "query": "needle", "max_results": 10},
            request_id="request-3",
        ))
        handoff = self.broker.execute(self.request(
            "handoff_write", {"document": {"status": "ready"}}, request_id="request-4"
        ))

        self.assertEqual(read["result"]["text"], "needle\n")
        self.assertIn("seed.txt", listed["result"]["entries"])
        self.assertEqual(searched["result"]["matches"][0]["path"], "seed.txt")
        self.assertEqual(json.loads((self.workspace / self.handoff).read_text()), {"status": "ready"})
        self.assertEqual(handoff["result"]["path"], self.handoff)
        self.assertTrue(all("argv" not in event for event in self.events()))
        self.assertTrue(all("argv_sha256" in event for event in self.events() if event["state"] != "broker_started"))

    def test_tool_schema_exposes_closed_action_specific_parameter_grammars(self):
        schema = _tool_schema(self.broker)["inputSchema"]
        variants = {
            item["properties"]["action"]["const"]: item
            for item in schema["oneOf"]
        }

        self.assertEqual(
            set(variants),
            {"read_file", "list_files", "search_text", "handoff_write", "git_read", "python_test", "audit"},
        )
        self.assertEqual(
            variants["python_test"]["properties"]["params"]["required"], ["target"]
        )
        self.assertFalse(variants["git_read"]["properties"]["params"]["additionalProperties"])

    def test_git_read_argv_disables_pager_external_diff_and_textconv(self):
        status = self.broker._command(
            "git_read", {"operation": "status", "paths": [], "limit": None, "revision": None}
        )
        diff = self.broker._command(
            "git_read", {"operation": "diff", "paths": [], "limit": None, "revision": None}
        )

        self.assertEqual(status[:3], ("/usr/bin/git", "--no-pager", "status"))
        self.assertIn("--no-ext-diff", diff)
        self.assertIn("--no-textconv", diff)

    def test_handoff_parent_symlink_cannot_escape_workspace(self):
        outside = Path(self.temporary.name) / "outside"
        (outside / "_handoff").mkdir(parents=True)
        (self.workspace / "tmp").symlink_to(outside, target_is_directory=True)

        with self.assertRaisesRegex(BrokerError, "SYMLINK_DENIED"):
            self.broker.execute(self.request(
                "handoff_write", {"document": {"status": "ready"}}, request_id="symlink-parent"
            ))
        self.assertFalse((outside / "_handoff" / Path(self.handoff).name).exists())

    def test_wrong_binding_replay_and_stale_attempt_are_denied(self):
        with self.assertRaisesRegex(BrokerError, "REQUEST_BINDING_MISMATCH"):
            self.broker.execute(self.request(
                "read_file", {"path": "seed.txt", "max_bytes": 100}, fence="c" * 32
            ))
        valid = self.request("read_file", {"path": "seed.txt", "max_bytes": 100})
        self.broker.execute(valid)
        with self.assertRaisesRegex(BrokerError, "REQUEST_REPLAY"):
            self.broker.execute(valid)

        def supersede(document):
            entry = next(item for item in document["entries"] if item["task_key"] == self.task_key)
            entry["supervisor_attempts"].append({
                "at": "2026-09-05T00:00:01Z", "attempt_id": "d" * 32,
                "state": "reserved", "broker_fence": "e" * 32,
                "broker_boundary_version": BOUNDARY_VERSION,
            })

        worktree_ledger.update_ledger(self.main, supersede)
        with self.assertRaisesRegex(BrokerError, "ATTEMPT_STALE"):
            self.broker.execute(self.request(
                "read_file", {"path": "seed.txt", "max_bytes": 100}, request_id="stale"
            ))

    def test_shell_path_launcher_copy_native_node_and_proc_forms_never_reach_preexec(self):
        forbidden = (
            "codex", "/home/user/.local/bin/codex", "node codex.js", "./copied-codex",
            "/proc/self/exe", "sh -c true", "native-launcher", "../codex",
        )
        for index, value in enumerate(forbidden):
            with self.subTest(value=value), self.assertRaisesRegex(BrokerError, "ARGV_DENIED"):
                self.broker.execute(self.request(
                    "python_test", {"target": value}, request_id=f"deny-{index}"
                ))
        with self.assertRaisesRegex(BrokerError, "REQUEST_SCHEMA_INVALID"):
            self.broker.execute(self.request("exec", {"argv": ["codex"]}, request_id="unknown"))
        symlink = self.workspace / "linked-seed"
        symlink.symlink_to("seed.txt")
        with self.assertRaisesRegex(BrokerError, "SYMLINK_DENIED"):
            self.broker.execute(self.request(
                "read_file", {"path": "linked-seed", "max_bytes": 100}, request_id="symlink"
            ))

    def test_source_tamper_and_boundary_mismatch_fail_at_startup(self):
        with self.assertRaisesRegex(BrokerError, "SOURCE_TAMPERED"):
            Broker(**{**self.broker_args, "source_sha256": "0" * 64})
        with mock.patch.dict(os.environ, {"CODEX_EXEC_BROKER_BOUNDARY": "old"}):
            with self.assertRaisesRegex(BrokerError, "BOUNDARY_MISMATCH"):
                Broker(**self.broker_args)

    def test_process_boundary_allows_git_python_and_pty_but_hides_host_state_and_network(self):
        if shutil.which("bwrap") is None:
            self.skipTest("bubblewrap is not installed")
        tests = self.workspace / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        host_auth = Path.home() / ".codex/auth.json"
        host_codex = shutil.which("codex") or "/nonexistent/codex"
        common_probe = self.main / ".git/broker-write-probe"
        (tests / "test_boundary.py").write_text(
            "import pathlib, socket, unittest\n"
            "class Boundary(unittest.TestCase):\n"
            " def test_boundary(self):\n"
            f"  workspace=pathlib.Path({str(self.workspace)!r})\n"
            "  marker=workspace/'broker-child-marker'; marker.write_text('ok'); self.assertEqual(marker.read_text(),'ok')\n"
            f"  self.assertFalse(pathlib.Path({str(self.main / 'seed.txt')!r}).exists())\n"
            f"  self.assertFalse(pathlib.Path({str(host_auth)!r}).exists())\n"
            f"  self.assertFalse(pathlib.Path({str(host_codex)!r}).exists())\n"
            f"  with self.assertRaises(OSError): pathlib.Path({str(common_probe)!r}).write_text('bad')\n"
            "  with self.assertRaises(OSError): socket.create_connection(('127.0.0.1',9),.1)\n",
            encoding="utf-8",
        )
        result = self.broker.execute(self.request(
            "python_test", {"target": "tests.test_boundary"}, request_id="python"
        ))
        if result["exit_code"] != 0 and "Operation not permitted" in result["stderr"]:
            self.skipTest("kernel does not permit unprivileged bubblewrap namespaces")
        self.assertEqual(result["exit_code"], 0, result)
        self.assertEqual((self.workspace / "broker-child-marker").read_text(), "ok")
        self.assertFalse(common_probe.exists())

        git_result = self.broker.execute(self.request(
            "git_read", {"operation": "status", "paths": [], "limit": None, "revision": None},
            request_id="git-pty", pty=True,
        ))
        self.assertEqual(git_result["exit_code"], 0, git_result)
        self.assertIn("broker-child-marker", git_result["stdout"])
        process_events = [item for item in self.events() if item["state"] == "completed" and "pid" in item]
        self.assertTrue(process_events)
        self.assertRegex(process_events[-1]["process_start_token"], r"^[0-9]+$")
        self.assertTrue(all("argv" not in item for item in process_events))


if __name__ == "__main__":
    unittest.main()
