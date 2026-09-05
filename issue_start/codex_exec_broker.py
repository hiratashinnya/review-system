"""Task-bound MCP command broker for repo-supervised Codex processes.

The server intentionally exposes one MCP tool and never accepts a shell string or
an executable path.  Every request is compared with the durable supervisor
attempt before an action is evaluated.  Process actions use a fresh bubblewrap
boundary which does not mount the Codex runtime, authentication data, the Codex
installation, or the host network.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import pty
import re
import select
import signal
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import durable_lock


BOUNDARY_VERSION = "codex-exec-broker/2"
TOOL_NAME = "execute"
_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_TASK_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_ROLE = re.compile(r"^issue-(?:implementer|fixer)$")
_HEX = re.compile(r"^[0-9a-f]{32}$")
_MODULE = re.compile(r"^tests(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+$")
_MAX_OUTPUT = 1_048_576
_PROCESS_ACTIONS = frozenset({"git_read", "python_test", "audit"})
_DIRECT_ACTIONS = frozenset({"read_file", "list_files", "search_text", "handoff_write"})
_LOCK_WAIT_SECONDS = 5
_LANDLOCK_ACCESS_FS_EXECUTE = 1 << 0
_LANDLOCK_CREATE_RULESET_VERSION = 1
_LANDLOCK_RULE_PATH_BENEATH = 1
_PR_SET_NO_NEW_PRIVS = 38
_LANDLOCK_SYSCALLS = {
    "x86_64": (444, 445, 446),
    "aarch64": (444, 445, 446),
    "riscv64": (444, 445, 446),
}
_DYNAMIC_LOADERS = {
    "x86_64": "/lib64/ld-linux-x86-64.so.2",
    "aarch64": "/lib/ld-linux-aarch64.so.1",
    "riscv64": "/lib/ld-linux-riscv64-lp64d.so.1",
}


class _LandlockRulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _LandlockPathBeneathAttr(ctypes.Structure):
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
        ("reserved", ctypes.c_uint32),
    ]


class BrokerError(RuntimeError):
    def __init__(self, reason: str, stage: str = "request") -> None:
        super().__init__(reason)
        self.reason = reason
        self.stage = stage


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _process_start_token(pid: int) -> str:
    try:
        text = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        fields = text[text.rfind(")") + 2 :].split()
        token = fields[19]
    except (OSError, IndexError) as exc:
        raise BrokerError("BROKER_PROCESS_TOKEN_UNAVAILABLE", "spawn") from exc
    if not token.isdigit():
        raise BrokerError("BROKER_PROCESS_TOKEN_INVALID", "spawn")
    return token


def _landlock_syscalls() -> tuple[int, int, int]:
    try:
        return _LANDLOCK_SYSCALLS[os.uname().machine]
    except (AttributeError, KeyError) as exc:
        raise BrokerError("BROKER_EXEC_GUARD_UNAVAILABLE", "preexec") from exc


def _dynamic_loader() -> Path:
    try:
        return Path(_DYNAMIC_LOADERS[os.uname().machine]).resolve(strict=True)
    except (AttributeError, KeyError, OSError) as exc:
        raise BrokerError("BROKER_EXEC_GUARD_UNAVAILABLE", "preexec") from exc


def _landlock_abi() -> int:
    create_ruleset, _add_rule, _restrict_self = _landlock_syscalls()
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.syscall(create_ruleset, 0, 0, _LANDLOCK_CREATE_RULESET_VERSION)
    if result < 1:
        raise BrokerError("BROKER_EXEC_GUARD_UNAVAILABLE", "preexec")
    return int(result)


def _restrict_execution(executables: Sequence[Path]) -> None:
    """Allow exec only for host-validated executable inodes; inherited by descendants."""

    _landlock_abi()
    create_ruleset, add_rule, restrict_self = _landlock_syscalls()
    libc = ctypes.CDLL(None, use_errno=True)
    ruleset_attr = _LandlockRulesetAttr(_LANDLOCK_ACCESS_FS_EXECUTE)
    ruleset = libc.syscall(
        create_ruleset, ctypes.byref(ruleset_attr), ctypes.sizeof(ruleset_attr), 0
    )
    if ruleset < 0:
        raise OSError(ctypes.get_errno(), "landlock_create_ruleset")
    try:
        for executable in executables:
            descriptor = os.open(
                executable, getattr(os, "O_PATH", os.O_RDONLY) | os.O_CLOEXEC
            )
            try:
                rule = _LandlockPathBeneathAttr(
                    _LANDLOCK_ACCESS_FS_EXECUTE, descriptor, 0
                )
                if libc.syscall(
                    add_rule, ruleset, _LANDLOCK_RULE_PATH_BENEATH,
                    ctypes.byref(rule), 0,
                ) != 0:
                    raise OSError(ctypes.get_errno(), "landlock_add_rule")
            finally:
                os.close(descriptor)
        if libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "prctl")
        if libc.syscall(restrict_self, ruleset, 0) != 0:
            raise OSError(ctypes.get_errno(), "landlock_restrict_self")
    finally:
        os.close(ruleset)


def _acquire_ledger_lock(path: Path) -> int:
    try:
        return durable_lock.acquire(
            path, attempts=max(1, int(_LOCK_WAIT_SECONDS / 0.01)),
            interval=0.01, sleep=time.sleep,
        )
    except durable_lock.DurableLockError as exc:
        reasons = {
            "LOCK_TIMEOUT": "BROKER_LEDGER_LOCKED",
            "LOCK_PID_REUSED": "BROKER_LEDGER_LOCK_PID_REUSED",
            "LOCK_OWNER_INCONSISTENT": "BROKER_LEDGER_LOCK_INCONSISTENT",
        }
        raise BrokerError(reasons.get(exc.reason, "BROKER_LEDGER_LOCK_TAMPERED"), "ledger") from exc


def _read_document(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BrokerError("BROKER_LEDGER_INVALID", "cas") from exc
    if not isinstance(value, dict) or not isinstance(value.get("entries"), list):
        raise BrokerError("BROKER_LEDGER_INVALID", "cas")
    return value


def _write_document(path: Path, document: Mapping[str, Any]) -> None:
    temporary = path.with_name(path.name + ".new")
    payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


class Broker:
    def __init__(
        self,
        *,
        ledger: Path,
        workspace: Path,
        role: str,
        task_key: str,
        attempt_id: str,
        fence: str,
        handoff_path: str,
        bwrap: Path,
        python: Path,
        git_common: Path,
        source_sha256: str,
    ) -> None:
        self.ledger = ledger.resolve(strict=True)
        self.workspace = workspace.resolve(strict=True)
        self.role = role
        self.task_key = task_key
        self.attempt_id = attempt_id
        self.fence = fence
        self.handoff_path = handoff_path
        self.bwrap = bwrap.resolve(strict=True)
        self.python = python.resolve(strict=True)
        self.git_common = git_common.resolve(strict=True)
        self.source_sha256 = source_sha256
        self.server_pid = os.getpid()
        self.server_start_token = _process_start_token(self.server_pid)
        self._validate_static()
        self._verify_cas()
        self._append_event(
            {"state": "broker_started", "pid": self.server_pid,
             "process_start_token": self.server_start_token}
        )

    def _validate_static(self) -> None:
        source = Path(__file__).resolve(strict=True)
        if hashlib.sha256(source.read_bytes()).hexdigest() != self.source_sha256:
            raise BrokerError("BROKER_SOURCE_TAMPERED", "startup")
        if BOUNDARY_VERSION != os.environ.get("CODEX_EXEC_BROKER_BOUNDARY"):
            raise BrokerError("BROKER_BOUNDARY_MISMATCH", "startup")
        if (
            not _ROLE.fullmatch(self.role)
            or not _TASK_KEY.fullmatch(self.task_key)
            or not _HEX.fullmatch(self.attempt_id)
            or not _HEX.fullmatch(self.fence)
        ):
            raise BrokerError("BROKER_BINDING_INVALID", "startup")
        if self.ledger.is_symlink() or not self.ledger.is_file():
            raise BrokerError("BROKER_LEDGER_INVALID", "startup")
        for executable in (self.bwrap, self.python, Path("/usr/bin/git")):
            if not executable.is_file() or not os.access(executable, os.X_OK):
                raise BrokerError("BROKER_EXECUTABLE_UNAVAILABLE", "startup")
        _landlock_abi()
        _dynamic_loader()
        relative = Path(self.handoff_path)
        if relative.is_absolute() or ".." in relative.parts or not self.handoff_path.startswith("tmp/_handoff/"):
            raise BrokerError("BROKER_HANDOFF_PATH_INVALID", "startup")

    def _entry(self, document: Mapping[str, Any]) -> dict[str, Any]:
        matches = [
            item for item in document["entries"]
            if isinstance(item, dict) and item.get("platform") == "codex"
            and item.get("task_key") == self.task_key
        ]
        if len(matches) != 1:
            raise BrokerError("BROKER_BINDING_MISSING", "cas")
        return matches[0]

    def _verify_cas(self, document: Mapping[str, Any] | None = None) -> dict[str, Any]:
        value = dict(document) if document is not None else _read_document(self.ledger)
        entry = self._entry(value)
        if (
            entry.get("workspace") != str(self.workspace)
            or entry.get("agent_type") != self.role
            or entry.get("handoff_path") != self.handoff_path
            or entry.get("status") not in {"open", "running"}
        ):
            raise BrokerError("BROKER_BINDING_MISMATCH", "cas")
        attempts = entry.get("supervisor_attempts")
        if not isinstance(attempts, list):
            raise BrokerError("BROKER_ATTEMPT_MISSING", "cas")
        latest = next(
            (event for event in reversed(attempts) if isinstance(event, dict)
             and event.get("attempt_id") == self.attempt_id),
            None,
        )
        newer = next((event for event in reversed(attempts) if isinstance(event, dict)), None)
        if (
            latest is None
            or newer is None
            or newer.get("attempt_id") != self.attempt_id
            or latest.get("broker_fence") != self.fence
            or latest.get("broker_boundary_version") != BOUNDARY_VERSION
            or latest.get("state") not in {"reserved", "spawned", "running"}
        ):
            raise BrokerError("BROKER_ATTEMPT_STALE", "cas")
        completed = subprocess.run(
            ["/usr/bin/git", "symbolic-ref", "--short", "HEAD"], cwd=self.workspace,
            text=True, capture_output=True, check=False,
        )
        if completed.returncode != 0 or completed.stdout.strip() != entry.get("branch_name"):
            raise BrokerError("BROKER_GIT_BINDING_MISMATCH", "cas")
        return entry

    def _locked_update(self, mutate) -> None:
        lock = self.ledger.with_name(self.ledger.name + ".lock")
        descriptor = _acquire_ledger_lock(lock)
        try:
            document = _read_document(self.ledger)
            mutate(document)
            _write_document(self.ledger, document)
        finally:
            durable_lock.release(descriptor)

    def _append_event(self, event: Mapping[str, Any], *, request_id: str | None = None) -> None:
        def mutate(document: dict[str, Any]) -> None:
            entry = self._verify_cas(document)
            events = entry.setdefault("broker_events", [])
            if not isinstance(events, list):
                raise BrokerError("BROKER_LEDGER_INVALID", "ledger")
            if request_id is not None and any(
                item.get("request_id") == request_id for item in events if isinstance(item, dict)
            ):
                raise BrokerError("BROKER_REQUEST_REPLAY", "cas")
            events.append({
                "at": _stamp(), "attempt_id": self.attempt_id, "fence": self.fence,
                "boundary_version": BOUNDARY_VERSION, **dict(event),
                **({"request_id": request_id} if request_id is not None else {}),
            })
        self._locked_update(mutate)

    def _validate_request(self, value: Any) -> tuple[str, str, Path, int, str, Mapping[str, Any], bool]:
        required = {
            "task_key", "attempt_id", "fence", "role", "workspace", "cwd",
            "request_id", "timeout_seconds", "action", "params", "pty",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise BrokerError("BROKER_REQUEST_SCHEMA_INVALID")
        if (
            value["task_key"] != self.task_key
            or value["attempt_id"] != self.attempt_id
            or value["fence"] != self.fence
            or value["role"] != self.role
            or value["workspace"] != str(self.workspace)
        ):
            raise BrokerError("BROKER_REQUEST_BINDING_MISMATCH", "cas")
        request_id = value["request_id"]
        timeout = value["timeout_seconds"]
        action = value["action"]
        params = value["params"]
        use_pty = value["pty"]
        if (
            not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id)
            or not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 1200
            or action not in _PROCESS_ACTIONS | _DIRECT_ACTIONS
            or not isinstance(params, dict)
            or not isinstance(use_pty, bool)
            or (use_pty and action not in _PROCESS_ACTIONS)
        ):
            raise BrokerError("BROKER_REQUEST_SCHEMA_INVALID")
        relative_cwd = value["cwd"]
        if not isinstance(relative_cwd, str) or Path(relative_cwd).is_absolute() or ".." in Path(relative_cwd).parts:
            raise BrokerError("BROKER_CWD_INVALID")
        try:
            cwd = (self.workspace / relative_cwd).resolve(strict=True)
            cwd.relative_to(self.workspace)
        except (OSError, RuntimeError, ValueError) as exc:
            raise BrokerError("BROKER_CWD_INVALID") from exc
        if not cwd.is_dir():
            raise BrokerError("BROKER_CWD_INVALID")
        self._verify_cas()
        return request_id, action, cwd, timeout, relative_cwd, params, use_pty

    def _safe_path(self, cwd: Path, value: Any, *, regular: bool = False) -> Path:
        if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
            raise BrokerError("BROKER_PATH_INVALID", "grammar")
        target = cwd / value
        if target.is_symlink():
            raise BrokerError("BROKER_SYMLINK_DENIED", "grammar")
        try:
            resolved = target.resolve(strict=True)
            resolved.relative_to(self.workspace)
        except (OSError, RuntimeError, ValueError) as exc:
            raise BrokerError("BROKER_PATH_INVALID", "grammar") from exc
        if regular and not resolved.is_file():
            raise BrokerError("BROKER_PATH_INVALID", "grammar")
        return resolved

    def _command(self, action: str, params: Mapping[str, Any]) -> tuple[str, ...]:
        if action == "git_read":
            if set(params) != {"operation", "paths", "limit", "revision"}:
                raise BrokerError("BROKER_ARGV_DENIED", "grammar")
            operation, paths, limit, revision = (
                params["operation"], params["paths"], params["limit"], params["revision"]
            )
            if not isinstance(paths, list) or not all(
                isinstance(item, str) and item and not Path(item).is_absolute()
                and ".." not in Path(item).parts and not item.startswith("-") for item in paths
            ):
                raise BrokerError("BROKER_ARGV_DENIED", "grammar")
            if operation == "status" and paths == [] and limit is None and revision is None:
                return ("/usr/bin/git", "--no-pager", "status", "--short", "--branch")
            if operation == "diff_check" and paths == [] and limit is None and revision is None:
                return (
                    "/usr/bin/git", "--no-pager", "diff", "--no-ext-diff", "--no-textconv",
                    "--check",
                )
            if operation in {"diff", "ls_files"} and limit is None and revision is None:
                verb = ("diff",) if operation == "diff" else ("ls-files",)
                safety = ("--no-ext-diff", "--no-textconv") if operation == "diff" else ()
                return ("/usr/bin/git", "--no-pager", *verb, *safety, "--", *paths)
            if operation == "log" and paths == [] and revision is None and isinstance(limit, int) and 1 <= limit <= 50:
                return ("/usr/bin/git", "--no-pager", "log", "-n", str(limit), "--oneline")
            if operation == "show" and paths == [] and limit is None and isinstance(revision, str) and re.fullmatch(r"(?:HEAD|[0-9a-f]{7,40})", revision):
                return (
                    "/usr/bin/git", "--no-pager", "show", "--no-ext-diff", "--no-textconv",
                    "--stat", "--oneline", revision,
                )
            if operation == "rev_parse" and paths == [] and limit is None and revision == "HEAD":
                return ("/usr/bin/git", "--no-pager", "rev-parse", "HEAD")
            raise BrokerError("BROKER_ARGV_DENIED", "grammar")
        if action == "python_test":
            if set(params) != {"target"}:
                raise BrokerError("BROKER_ARGV_DENIED", "grammar")
            target = params["target"]
            if target == "all":
                return (str(self.python), "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")
            if not isinstance(target, str) or not _MODULE.fullmatch(target):
                raise BrokerError("BROKER_ARGV_DENIED", "grammar")
            return (str(self.python), "-m", "unittest", target)
        if action == "audit":
            if set(params) != {"name"} or params["name"] not in {
                "asset_parity", "guidance_sync", "time_fixture_lint"
            }:
                raise BrokerError("BROKER_ARGV_DENIED", "grammar")
            return (str(self.python), "-m", params["name"], "check")
        raise BrokerError("BROKER_ACTION_INVALID", "grammar")

    def _sandbox_command(self, command: Sequence[str], cwd: Path) -> tuple[str, ...]:
        protected: list[str] = []
        for relative in (".git", ".codex", ".agents"):
            target = self.workspace / relative
            if target.exists() or target.is_symlink():
                protected.extend(("--ro-bind", str(target), str(target)))
        role_contract = self.workspace / ".ai" / "agents" / f"{self.role}.md"
        if role_contract.exists() or role_contract.is_symlink():
            protected.extend(("--ro-bind", str(role_contract), str(role_contract)))
        return (
            str(self.bwrap), "--die-with-parent", "--new-session", "--unshare-pid", "--unshare-net",
            "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin",
            "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
            "--ro-bind", "/etc", "/etc", "--dev", "/dev", "--remount-ro", "/dev",
            "--dir", "/proc", "--tmpfs", "/tmp", "--dir", "/tmp/home", "--clearenv",
            "--bind", str(self.workspace), str(self.workspace),
            "--ro-bind", str(self.git_common), str(self.git_common), *protected,
            "--setenv", "HOME", "/tmp/home", "--setenv", "TMPDIR", "/tmp",
            "--setenv", "PATH", "/usr/bin:/bin",
            "--setenv", "GIT_CONFIG_GLOBAL", "/dev/null",
            "--setenv", "GIT_CONFIG_NOSYSTEM", "1", "--setenv", "GIT_PAGER", "cat",
            "--setenv", "PAGER", "cat",
            "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--chdir", str(cwd), "--", *command,
        )

    def _run_process(self, command: Sequence[str], cwd: Path, timeout: int, use_pty: bool) -> dict[str, Any]:
        sandboxed = self._sandbox_command(command, cwd)
        allowed_exec = (
            self.bwrap, self.python, Path("/usr/bin/git").resolve(strict=True), _dynamic_loader()
        )
        child_env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}

        def guard() -> None:
            _restrict_execution(allowed_exec)

        def spawn(**kwargs) -> subprocess.Popen[bytes]:
            try:
                return subprocess.Popen(
                    sandboxed, cwd=cwd, stdin=subprocess.DEVNULL,
                    start_new_session=True, env=child_env, preexec_fn=guard, **kwargs,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise BrokerError("BROKER_EXEC_GUARD_FAILED", "preexec") from exc

        if use_pty:
            master, slave = pty.openpty()
            try:
                process = spawn(stdout=slave, stderr=slave, close_fds=True)
            finally:
                os.close(slave)
            process_start_token = _process_start_token(process.pid)
            output = bytearray()
            deadline = time.monotonic() + timeout
            timed_out = False
            try:
                while process.poll() is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        timed_out = True
                        os.killpg(process.pid, signal.SIGKILL)
                        break
                    readable, _, _ = select.select([master], [], [], min(0.1, remaining))
                    if readable:
                        try:
                            output.extend(os.read(master, min(65536, _MAX_OUTPUT - len(output))))
                        except OSError:
                            break
                    if len(output) >= _MAX_OUTPUT:
                        os.killpg(process.pid, signal.SIGKILL)
                        break
                process.wait()
                while len(output) < _MAX_OUTPUT:
                    readable, _, _ = select.select([master], [], [], 0)
                    if not readable:
                        break
                    try:
                        output.extend(os.read(master, min(65536, _MAX_OUTPUT - len(output))))
                    except OSError:
                        break
            finally:
                os.close(master)
            stdout = output.decode("utf-8", errors="replace")
            stderr = ""
        else:
            process = spawn(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process_start_token = _process_start_token(process.pid)
            try:
                out, err = process.communicate(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                out, err = process.communicate()
                timed_out = True
            stdout = out[:_MAX_OUTPUT].decode("utf-8", errors="replace")
            stderr = err[:_MAX_OUTPUT].decode("utf-8", errors="replace")
        return {
            "pid": process.pid, "process_start_token": process_start_token,
            "exit_code": process.returncode, "timed_out": timed_out,
            "stdout": stdout, "stderr": stderr,
        }

    def _direct(self, action: str, params: Mapping[str, Any], cwd: Path) -> Any:
        if action == "read_file":
            if set(params) != {"path", "max_bytes"} or not isinstance(params["max_bytes"], int) or not 1 <= params["max_bytes"] <= _MAX_OUTPUT:
                raise BrokerError("BROKER_ARGV_DENIED", "grammar")
            target = self._safe_path(cwd, params["path"], regular=True)
            data = target.read_bytes()
            return {"text": data[: params["max_bytes"]].decode("utf-8", errors="replace"), "truncated": len(data) > params["max_bytes"]}
        if action == "list_files":
            if set(params) != {"path", "max_entries"} or not isinstance(params["max_entries"], int) or not 1 <= params["max_entries"] <= 10000:
                raise BrokerError("BROKER_ARGV_DENIED", "grammar")
            target = self._safe_path(cwd, params["path"])
            if not target.is_dir():
                raise BrokerError("BROKER_PATH_INVALID", "grammar")
            entries = sorted(item.name + ("/" if item.is_dir() else "") for item in target.iterdir())
            return {"entries": entries[: params["max_entries"]], "truncated": len(entries) > params["max_entries"]}
        if action == "search_text":
            if set(params) != {"path", "query", "max_results"} or not isinstance(params["query"], str) or not params["query"] or len(params["query"]) > 256 or not isinstance(params["max_results"], int) or not 1 <= params["max_results"] <= 1000:
                raise BrokerError("BROKER_ARGV_DENIED", "grammar")
            target = self._safe_path(cwd, params["path"])
            roots = [target] if target.is_file() else target.rglob("*")
            found = []
            for item in roots:
                if item.is_symlink() or not item.is_file() or item.stat().st_size > _MAX_OUTPUT:
                    continue
                try:
                    for number, line in enumerate(item.read_text(encoding="utf-8").splitlines(), 1):
                        if params["query"] in line:
                            found.append({"path": str(item.relative_to(self.workspace)), "line": number, "text": line[:1000]})
                            if len(found) >= params["max_results"]:
                                return {"matches": found, "truncated": True}
                except (OSError, UnicodeDecodeError):
                    continue
            return {"matches": found, "truncated": False}
        if action == "handoff_write":
            if set(params) != {"document"}:
                raise BrokerError("BROKER_ARGV_DENIED", "grammar")
            payload = json.dumps(params["document"], ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            if len(payload.encode()) > _MAX_OUTPUT:
                raise BrokerError("BROKER_HANDOFF_TOO_LARGE", "grammar")
            target = self.workspace / self.handoff_path
            cursor = self.workspace
            for component in Path(self.handoff_path).parts[:-1]:
                cursor /= component
                if cursor.is_symlink():
                    raise BrokerError("BROKER_SYMLINK_DENIED", "grammar")
                if cursor.exists() and not cursor.is_dir():
                    raise BrokerError("BROKER_HANDOFF_PATH_INVALID", "grammar")
                cursor.mkdir(exist_ok=True)
            try:
                target.parent.resolve(strict=True).relative_to(self.workspace)
            except (OSError, RuntimeError, ValueError) as exc:
                raise BrokerError("BROKER_HANDOFF_PATH_INVALID", "grammar") from exc
            if target.is_symlink():
                raise BrokerError("BROKER_SYMLINK_DENIED", "grammar")
            temporary = target.with_name(f".{target.name}.{os.getpid()}.new")
            try:
                with temporary.open("x", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
            return {"path": self.handoff_path, "sha256": hashlib.sha256(payload.encode()).hexdigest()}
        raise BrokerError("BROKER_ACTION_INVALID", "grammar")

    def execute(self, arguments: Any) -> dict[str, Any]:
        request_id = None
        try:
            request_id, action, cwd, timeout, _relative_cwd, params, use_pty = self._validate_request(arguments)
            digest_input: Any = {"action": action, "params": params}
            if action in _PROCESS_ACTIONS:
                command = self._command(action, params)
                argv_sha256 = _sha256_json(list(command))
                self._append_event(
                    {"state": "request_reserved", "action": action, "argv_sha256": argv_sha256},
                    request_id=request_id,
                )
                result = self._run_process(command, cwd, timeout, use_pty)
                self._append_event({
                    "state": "completed" if result["exit_code"] == 0 and not result["timed_out"] else "failed",
                    "action": action, "argv_sha256": argv_sha256, "pid": result["pid"],
                    "process_start_token": result["process_start_token"], "exit_code": result["exit_code"],
                    "timed_out": result["timed_out"],
                })
                return {"status": "completed", "boundary_version": BOUNDARY_VERSION,
                        "argv_sha256": argv_sha256, **result}
            argv_sha256 = _sha256_json(digest_input)
            self._append_event(
                {"state": "request_reserved", "action": action, "argv_sha256": argv_sha256},
                request_id=request_id,
            )
            result = self._direct(action, params, cwd)
            self._append_event({"state": "completed", "action": action, "argv_sha256": argv_sha256})
            return {"status": "completed", "boundary_version": BOUNDARY_VERSION,
                    "argv_sha256": argv_sha256, "result": result}
        except BrokerError as exc:
            try:
                self._append_event({"state": "denied", "stage": exc.stage, "reason": exc.reason})
            except BrokerError:
                pass
            raise


def _tool_schema(broker: Broker) -> dict[str, Any]:
    common = {
        "task_key": {"const": broker.task_key}, "attempt_id": {"const": broker.attempt_id},
        "fence": {"const": broker.fence}, "role": {"const": broker.role},
        "workspace": {"const": str(broker.workspace)},
        "cwd": {"type": "string", "description": "Workspace-relative existing directory."},
        "request_id": {"type": "string", "pattern": _REQUEST_ID.pattern},
        "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 1200},
        "pty": {"type": "boolean"},
    }
    action_parameters = {
        "read_file": {"path": {"type": "string"}, "max_bytes": {"type": "integer"}},
        "list_files": {"path": {"type": "string"}, "max_entries": {"type": "integer"}},
        "search_text": {
            "path": {"type": "string"}, "query": {"type": "string"},
            "max_results": {"type": "integer"},
        },
        "handoff_write": {"document": {}},
        "python_test": {"target": {"type": "string"}},
        "audit": {"name": {"enum": ["asset_parity", "guidance_sync", "time_fixture_lint"]}},
        "git_read": {
            "operation": {
                "enum": ["status", "diff_check", "diff", "ls_files", "log", "show", "rev_parse"]
            },
            "paths": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": ["integer", "null"]},
            "revision": {"type": ["string", "null"]},
        },
    }
    variants = []
    for action, properties in action_parameters.items():
        variants.append({
            "type": "object", "additionalProperties": False,
            "required": [*common, "action", "params", "pty"],
            "properties": {
                **common, "action": {"const": action},
                "params": {
                    "type": "object", "additionalProperties": False,
                    "required": list(properties), "properties": properties,
                },
            },
        })
    return {
        "name": TOOL_NAME,
        "description": (
            "Execute one task-bound broker action. No shell string, executable, launcher, "
            "absolute path, wrapper, copy, symlink, or network action is accepted. "
            f"Binding: task={broker.task_key} attempt={broker.attempt_id} fence={broker.fence} "
            f"role={broker.role} workspace={broker.workspace}."
        ),
        "inputSchema": {"oneOf": variants},
    }


def serve(broker: Broker) -> int:
    for line in sys.stdin:
        try:
            request = json.loads(line)
            request_id = request.get("id") if isinstance(request, dict) else None
            method = request.get("method") if isinstance(request, dict) else None
            if method == "initialize":
                result = {
                    "protocolVersion": request.get("params", {}).get("protocolVersion", "2025-06-18"),
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "codex-exec-broker", "version": BOUNDARY_VERSION},
                }
            elif method == "notifications/initialized":
                continue
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                broker._verify_cas()
                result = {"tools": [_tool_schema(broker)]}
            elif method == "tools/call":
                params = request.get("params", {})
                if params.get("name") != TOOL_NAME:
                    broker._append_event({"state": "denied", "stage": "tool_catalog", "reason": "BROKER_UNKNOWN_TOOL"})
                    raise BrokerError("BROKER_UNKNOWN_TOOL", "tool_catalog")
                try:
                    value = broker.execute(params.get("arguments"))
                    result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}
                except BrokerError as exc:
                    result = {"content": [{"type": "text", "text": json.dumps(
                        {"status": "denied", "reason": exc.reason, "stage": exc.stage}
                    )}], "isError": True}
            else:
                raise BrokerError("BROKER_UNKNOWN_METHOD", "protocol")
            response = {"jsonrpc": "2.0", "id": request_id, "result": result}
        except (json.JSONDecodeError, BrokerError) as exc:
            reason = exc.reason if isinstance(exc, BrokerError) else "BROKER_PROTOCOL_INVALID"
            response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None,
                        "error": {"code": -32601, "message": reason}}
        sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
        sys.stdout.flush()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--task-key", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--fence", required=True)
    parser.add_argument("--handoff-path", required=True)
    parser.add_argument("--bwrap", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--git-common", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        broker = Broker(
            ledger=args.ledger, workspace=args.workspace, role=args.role, task_key=args.task_key,
            attempt_id=args.attempt_id, fence=args.fence, handoff_path=args.handoff_path,
            bwrap=args.bwrap, python=args.python, git_common=args.git_common,
            source_sha256=args.source_sha256,
        )
        return serve(broker)
    except BrokerError as exc:
        print(json.dumps({"status": "denied", "reason": exc.reason, "stage": exc.stage}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
