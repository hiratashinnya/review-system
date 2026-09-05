import hashlib
import fcntl
import json
import os
import signal
import shutil
import stat
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from issue_start import codex_exec_broker, worktree_ledger
from issue_start.codex_binding import prepare_binding
from issue_start.codex_exec_broker import (
    BOUNDARY_VERSION,
    Broker,
    BrokerError,
    _acquire_ledger_lock,
    _tool_schema,
)
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
        lock_source = Path(codex_exec_broker.durable_lock.__file__).resolve()
        self.broker_args = {
            "ledger": worktree_ledger.ledger_path(self.main), "workspace": self.workspace,
            "role": "issue-implementer", "task_key": self.task_key,
            "attempt_id": self.attempt, "fence": self.fence, "handoff_path": self.handoff,
            "bwrap": Path(self.bwrap), "python": Path("/usr/bin/python3"),
            "git_common": self.main / ".git",
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "lock_source_sha256": hashlib.sha256(lock_source.read_bytes()).hexdigest(),
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
        with self.assertRaisesRegex(BrokerError, "SOURCE_TAMPERED"):
            Broker(**{**self.broker_args, "lock_source_sha256": "0" * 64})
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

    def test_allowed_unittest_descendant_exec_is_os_denied(self):
        if shutil.which("bwrap") is None:
            self.skipTest("bubblewrap is not installed")
        tests = self.workspace / "tests"
        tests.mkdir(exist_ok=True)
        (tests / "__init__.py").write_text("", encoding="utf-8")
        host_codex = shutil.which("codex") or "/host/codex-not-installed"
        (tests / "test_exec_guard.py").write_text(
            "import os, pathlib, shutil, subprocess, unittest\n"
            "class ExecGuard(unittest.TestCase):\n"
            " def denied(self, argv):\n"
            "  with self.assertRaises((FileNotFoundError, PermissionError)):\n"
            "   subprocess.run(argv, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
            " def test_all_nested_forms(self):\n"
            f"  self.denied([{host_codex!r}, '--version'])\n"
            "  self.denied(['codex', '--version'])\n"
            "  root=pathlib.Path.cwd()\n"
            "  copied=root/'copied-native'; shutil.copy2('/usr/bin/git', copied); copied.chmod(0o755)\n"
            "  self.denied([str(copied), '--version'])\n"
            "  linked=root/'linked-node'; linked.symlink_to('/usr/bin/node')\n"
            "  self.denied([str(linked), '--version'])\n"
            "  script=root/'codex.js'; script.write_text('process.exit(0)')\n"
            "  self.denied(['/usr/bin/node', str(script)])\n"
            "  self.denied(['/usr/bin/node', '--version'])\n"
            "  self.assertFalse(pathlib.Path('/proc/self/exe').exists())\n",
            encoding="utf-8",
        )
        result = self.broker.execute(self.request(
            "python_test", {"target": "tests.test_exec_guard"}, request_id="exec-guard"
        ))
        self.assertEqual(result["exit_code"], 0, result)
        combined = result["stdout"] + result["stderr"]
        self.assertNotIn("thread.started", combined)
        self.assertNotIn("turn.started", combined)
        self.assertNotIn("OPENAI", combined)

    def test_process_environment_drops_host_secrets(self):
        if shutil.which("bwrap") is None:
            self.skipTest("bubblewrap is not installed")
        tests = self.workspace / "tests"
        tests.mkdir(exist_ok=True)
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_env_guard.py").write_text(
            "import os, unittest\n"
            "class EnvGuard(unittest.TestCase):\n"
            " def test_env(self):\n"
            "  self.assertEqual(os.environ['HOME'], '/tmp/home')\n"
            "  self.assertEqual(os.environ['TMPDIR'], '/tmp')\n"
            "  self.assertEqual(os.environ['PATH'], '/usr/bin:/bin')\n"
            "  self.assertNotIn('OPENAI_API_KEY', os.environ)\n"
            "  self.assertNotIn('GH_TOKEN', os.environ)\n"
            "  self.assertNotIn('AWS_SECRET_ACCESS_KEY', os.environ)\n",
            encoding="utf-8",
        )
        sentinels = {
            "OPENAI_API_KEY": "sentinel-openai", "GH_TOKEN": "sentinel-gh",
            "AWS_SECRET_ACCESS_KEY": "sentinel-aws",
        }
        with mock.patch.dict(os.environ, sentinels):
            result = self.broker.execute(self.request(
                "python_test", {"target": "tests.test_env_guard"}, request_id="env-guard"
            ))
        self.assertEqual(result["exit_code"], 0, result)
        serialized = json.dumps({"result": result, "events": self.events()})
        for secret in sentinels.values():
            self.assertNotIn(secret, serialized)

    def test_ledger_lock_recovers_only_dead_exact_owner(self):
        lock = self.workspace / "durable.lock"
        dead_owner = {
            "version": 1, "pid": 99999999, "process_start_token": "1",
            "nonce": "a" * 32,
        }
        lock.write_text(json.dumps(dead_owner), encoding="utf-8")
        lock.chmod(0o600)
        descriptor = _acquire_ledger_lock(lock)
        try:
            self.assertEqual(json.loads(lock.read_text())["pid"], os.getpid())
        finally:
            os.ftruncate(descriptor, 0)
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

        reused = {**dead_owner, "pid": os.getpid(), "process_start_token": "0"}
        lock.write_text(json.dumps(reused), encoding="utf-8")
        with self.assertRaisesRegex(BrokerError, "LOCK_PID_REUSED"):
            _acquire_ledger_lock(lock)
        lock.write_text("not-json", encoding="utf-8")
        with self.assertRaisesRegex(BrokerError, "LOCK_TAMPERED"):
            _acquire_ledger_lock(lock)

    def test_ledger_lock_crash_points_are_idempotent(self):
        lock = self.broker.ledger.with_name(self.broker.ledger.name + ".lock")
        descriptor = _acquire_ledger_lock(lock)
        with mock.patch.object(codex_exec_broker, "_LOCK_WAIT_SECONDS", 0):
            with self.assertRaisesRegex(BrokerError, "LEDGER_LOCKED"):
                _acquire_ledger_lock(lock)
        os.ftruncate(descriptor, 0)
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)

        def crash_before_replace(_document):
            raise RuntimeError("crash-before-replace")

        with self.assertRaisesRegex(RuntimeError, "crash-before-replace"):
            self.broker._locked_update(crash_before_replace)
        self.broker._append_event(
            {"state": "completed", "action": "audit", "argv_sha256": "a" * 64},
            request_id="after-crash",
        )
        matches = [event for event in self.events() if event.get("request_id") == "after-crash"]
        self.assertEqual(len(matches), 1)

    def test_sigkill_at_each_ledger_crash_point_recovers_once(self):
        real_replace = os.replace
        real_fsync = os.fsync

        def die(*_args, **_kwargs):
            os.kill(os.getpid(), signal.SIGKILL)

        def run_crash(request_id, install, *, persisted):
            pid = os.fork()
            if pid == 0:
                try:
                    install(die)
                    self.broker._append_event(
                        {"state": "completed", "action": "audit", "argv_sha256": "b" * 64},
                        request_id=request_id,
                    )
                finally:
                    os._exit(120)
            _, status = os.waitpid(pid, 0)
            self.assertTrue(os.WIFSIGNALED(status), (request_id, status))
            self.assertEqual(os.WTERMSIG(status), signal.SIGKILL)
            if persisted:
                with self.assertRaisesRegex(BrokerError, "BROKER_REQUEST_REPLAY"):
                    self.broker._append_event(
                        {"state": "completed", "action": "audit", "argv_sha256": "b" * 64},
                        request_id=request_id,
                    )
            else:
                self.broker._append_event(
                    {"state": "completed", "action": "audit", "argv_sha256": "b" * 64},
                    request_id=request_id,
                )
            matches = [item for item in self.events() if item.get("request_id") == request_id]
            self.assertEqual(len(matches), 1, request_id)

        run_crash(
            "killed-after-lock",
            lambda kill: mock.patch.object(codex_exec_broker, "_read_document", side_effect=kill).start(),
            persisted=False,
        )
        run_crash(
            "killed-before-replace",
            lambda kill: mock.patch.object(os, "replace", side_effect=kill).start(),
            persisted=False,
        )

        def install_after_replace(kill):
            def replace_then_kill(source, target):
                real_replace(source, target)
                kill()
            mock.patch.object(os, "replace", side_effect=replace_then_kill).start()

        run_crash("killed-after-replace", install_after_replace, persisted=True)

        def install_after_directory_fsync(kill):
            def fsync_then_maybe_kill(descriptor):
                real_fsync(descriptor)
                if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                    kill()
            mock.patch.object(os, "fsync", side_effect=fsync_then_maybe_kill).start()

        run_crash("killed-after-fsync", install_after_directory_fsync, persisted=True)
        run_crash(
            "killed-before-unlock",
            lambda kill: mock.patch.object(codex_exec_broker.durable_lock, "release", side_effect=kill).start(),
            persisted=True,
        )


if __name__ == "__main__":
    unittest.main()
