"""Issue 専用 worktree 内で別 Codex CLI process を監督実行する。

``collaboration.spawn_agent`` では観測できなかった child workspace と process identity を、
repo 側 supervisor が OS process と JSONL の両側から観測する。内側 Codex は編集・テスト・
handoff 作成だけを担当し、Git publish は終了後に host 側の既存 gate へ戻す。
"""

from __future__ import annotations

import json
import os
import queue
import re
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence, TextIO

from . import codex_binding, worktree_ledger


MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "xhigh"
DEFAULT_TIMEOUT_SECONDS = 1800
_THREAD_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_RATE_LIMIT = re.compile(r"rate.?limit|too many requests|usage limit", re.IGNORECASE)
_DENIED_ITEM_MARKERS = ("web_search", "subagent", "collaboration", "agent_tool")
_PROTECTED_ROOTS = (".git", ".codex", ".agents")


class CodexSupervisorError(RuntimeError):
    """Supervisor が fail-close した理由コード付き例外。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class SupervisorSpec:
    repo_root: Path
    workspace: Path
    role: str
    task_key: str
    handoff_path: str
    model: str = MODEL
    reasoning_effort: str = REASONING_EFFORT
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class ProcessResult:
    pid: int
    process_start_token: str
    exit_code: int
    stdout: tuple[str, ...]
    stderr: tuple[str, ...]
    timed_out: bool = False
    killed: bool = False


@dataclass(frozen=True)
class SupervisedResult:
    status: str
    thread_id: str
    terminal_event: str | None
    process: ProcessResult
    resume_command: tuple[str, ...] | None = None


class ProcessRunner(Protocol):
    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        prompt: str,
        timeout_seconds: int,
        on_process_started: Callable[[int, str], None],
        on_stdout_line: Callable[[str], None],
    ) -> ProcessResult: ...


def _stamp(now: datetime) -> str:
    if now.tzinfo is None or now.utcoffset() is None:
        raise CodexSupervisorError("CODEX_SUPERVISOR_TIME_NAIVE")
    return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _process_start_token(pid: int) -> str:
    """Linux procfs の process start time tick を PID 再利用対策として取得する。"""

    try:
        text = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        closing = text.rfind(")")
        fields = text[closing + 2 :].split()
        token = fields[19]
    except (OSError, IndexError) as exc:
        raise CodexSupervisorError("CODEX_SUPERVISOR_PROCESS_TOKEN_UNAVAILABLE", str(pid)) from exc
    if not token.isdigit():
        raise CodexSupervisorError("CODEX_SUPERVISOR_PROCESS_TOKEN_INVALID", token)
    return token


class SubprocessJsonlRunner:
    """stdout JSONL を監視しつつ timeout 時に process group を停止する runner。"""

    def __init__(
        self,
        *,
        popen: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._popen = popen
        self._monotonic = monotonic

    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        prompt: str,
        timeout_seconds: int,
        on_process_started: Callable[[int, str], None],
        on_stdout_line: Callable[[str], None],
    ) -> ProcessResult:
        process = self._popen(
            list(command), cwd=cwd, env=dict(env), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True, bufsize=1,
        )
        if process.stdin is None or process.stdout is None or process.stderr is None:
            raise CodexSupervisorError("CODEX_SUPERVISOR_PIPE_MISSING")
        token = _process_start_token(process.pid)
        on_process_started(process.pid, token)
        stream: queue.Queue[tuple[str, str | None]] = queue.Queue()

        def drain(name: str, handle: TextIO) -> None:
            try:
                for line in handle:
                    stream.put((name, line.rstrip("\n")))
            finally:
                stream.put((name, None))

        threads = [
            threading.Thread(target=drain, args=("stdout", process.stdout), daemon=True),
            threading.Thread(target=drain, args=("stderr", process.stderr), daemon=True),
        ]
        for thread in threads:
            thread.start()
        process.stdin.write(prompt)
        process.stdin.close()
        deadline = self._monotonic() + timeout_seconds
        stdout: list[str] = []
        stderr: list[str] = []
        closed: set[str] = set()
        timed_out = False
        killed = False
        observer_error: BaseException | None = None

        while len(closed) != 2:
            remaining = deadline - self._monotonic()
            if remaining <= 0:
                timed_out = True
                break
            try:
                name, line = stream.get(timeout=min(0.1, remaining))
            except queue.Empty:
                if process.poll() is not None and all(not thread.is_alive() for thread in threads):
                    break
                continue
            if line is None:
                closed.add(name)
                continue
            if name == "stdout":
                stdout.append(line)
                try:
                    on_stdout_line(line)
                except BaseException as exc:  # fail-close and preserve the original reason
                    observer_error = exc
                    break
            else:
                stderr.append(line)

        if timed_out or observer_error is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
                killed = True
            except ProcessLookupError:
                pass
        exit_code = process.wait()
        for thread in threads:
            thread.join(timeout=1)
        if observer_error is not None:
            raise observer_error
        return ProcessResult(
            pid=process.pid, process_start_token=token, exit_code=exit_code,
            stdout=tuple(stdout), stderr=tuple(stderr), timed_out=timed_out, killed=killed,
        )


class CodexJsonlObserver:
    """Codex ``--json`` の順序・一意性・禁止tool eventを検査する。"""

    def __init__(self, on_thread_started: Callable[[str], None]) -> None:
        self._on_thread_started = on_thread_started
        self.thread_id: str | None = None
        self.terminal_event: str | None = None
        self.rate_limited = False
        self.line_count = 0

    def feed(self, line: str) -> None:
        self.line_count += 1
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CodexSupervisorError(
                "CODEX_SUPERVISOR_JSONL_MALFORMED", f"line={self.line_count}"
            ) from exc
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise CodexSupervisorError(
                "CODEX_SUPERVISOR_JSONL_EVENT_INVALID", f"line={self.line_count}"
            )
        event_type = event["type"]
        if event_type == "thread.started":
            thread_id = event.get("thread_id")
            if self.thread_id is not None:
                raise CodexSupervisorError("CODEX_SUPERVISOR_THREAD_DUPLICATE")
            if not isinstance(thread_id, str) or not _THREAD_ID.fullmatch(thread_id):
                raise CodexSupervisorError("CODEX_SUPERVISOR_THREAD_ID_INVALID", repr(thread_id))
            if self.terminal_event is not None:
                raise CodexSupervisorError("CODEX_SUPERVISOR_THREAD_AFTER_TERMINAL")
            self.thread_id = thread_id
            self._on_thread_started(thread_id)
            return
        if event_type in {"turn.completed", "turn.failed"}:
            if self.thread_id is None:
                raise CodexSupervisorError("CODEX_SUPERVISOR_TERMINAL_BEFORE_THREAD", event_type)
            if self.terminal_event is not None:
                raise CodexSupervisorError("CODEX_SUPERVISOR_TERMINAL_DUPLICATE", event_type)
            self.terminal_event = event_type
            return
        if event_type == "error":
            detail = json.dumps(event, ensure_ascii=False, sort_keys=True)
            if _RATE_LIMIT.search(detail):
                self.rate_limited = True
            return
        item = event.get("item")
        if isinstance(item, dict):
            item_type = str(item.get("type", "")).lower()
            if any(marker in item_type for marker in _DENIED_ITEM_MARKERS):
                raise CodexSupervisorError("CODEX_SUPERVISOR_DENIED_TOOL_EVENT", item_type)

    def finalize(self, process: ProcessResult, *, handoff_exists: bool) -> str:
        if self.thread_id is None:
            raise CodexSupervisorError("CODEX_SUPERVISOR_THREAD_MISSING")
        if process.timed_out:
            raise CodexSupervisorError("CODEX_SUPERVISOR_TIMEOUT")
        if process.killed:
            raise CodexSupervisorError("CODEX_SUPERVISOR_KILLED")
        if self.rate_limited:
            return "paused_rate_limit"
        if process.exit_code != 0:
            raise CodexSupervisorError("CODEX_SUPERVISOR_EXIT_NONZERO", str(process.exit_code))
        if self.terminal_event != "turn.completed":
            reason = "CODEX_SUPERVISOR_TERMINAL_MISSING" if self.terminal_event is None else "CODEX_SUPERVISOR_TURN_FAILED"
            raise CodexSupervisorError(reason)
        if not handoff_exists:
            raise CodexSupervisorError("CODEX_SUPERVISOR_HANDOFF_MISSING")
        return "succeeded"


def _require_executable(path: Path | str, reason: str) -> str:
    candidate = Path(path)
    if not candidate.is_absolute() or not candidate.is_file() or not os.access(candidate, os.X_OK):
        raise CodexSupervisorError(reason, str(candidate))
    return str(candidate)


def build_codex_command(
    spec: SupervisorSpec,
    *,
    bwrap_executable: Path | str,
    codex_executable: Path | str,
    resume_thread: str | None = None,
) -> tuple[str, ...]:
    """外側 bubblewrap と内側 Codex sandbox の二段 command を組み立てる。"""

    workspace = spec.workspace.resolve(strict=True)
    bwrap = _require_executable(bwrap_executable, "CODEX_SUPERVISOR_BWRAP_UNAVAILABLE")
    codex = _require_executable(codex_executable, "CODEX_SUPERVISOR_CODEX_UNAVAILABLE")
    protected: list[str] = []
    for relative in _PROTECTED_ROOTS:
        target = workspace / relative
        if not target.exists() and not target.is_symlink():
            raise CodexSupervisorError("CODEX_SUPERVISOR_PROTECTED_PATH_MISSING", relative)
        protected.extend(("--ro-bind", str(target), str(target)))
    inner = [
        codex, "exec", "--cd", str(workspace), "--sandbox", "workspace-write",
        "--ask-for-approval", "never", "--ignore-user-config", "--json",
        "--model", spec.model,
        "--config", f'model_reasoning_effort="{spec.reasoning_effort}"',
        "--config", 'web_search="disabled"',
        "--config", "sandbox_workspace_write.network_access=false",
        "--config", "sandbox_workspace_write.exclude_slash_tmp=true",
        "--config", "sandbox_workspace_write.exclude_tmpdir_env_var=true",
        "--config", "agents.enabled=false",
        "--config", "features.multi_agent=false",
        "--config", "apps._default.enabled=false",
    ]
    if resume_thread is not None:
        if not _THREAD_ID.fullmatch(resume_thread):
            raise CodexSupervisorError("CODEX_SUPERVISOR_THREAD_ID_INVALID", resume_thread)
        inner.extend(("resume", resume_thread, "-"))
    else:
        inner.append("-")
    return tuple([
        bwrap, "--die-with-parent", "--new-session", "--unshare-net",
        "--ro-bind", "/", "/", "--bind", str(workspace), str(workspace),
        *protected, "--tmpfs", "/tmp", "--setenv", "TMPDIR", "/tmp",
        "--setenv", "CODEX_ISSUE_SUPERVISED", "1", "--chdir", str(workspace),
        "--", *inner,
    ])


def build_sandbox_probe_command(
    workspace: Path | str,
    *,
    bwrap_executable: Path | str,
    python_executable: Path | str,
) -> tuple[str, ...]:
    """モデルを呼ばずに write/network/private tmp 境界を実測する command。"""

    root = Path(workspace).resolve(strict=True)
    bwrap = _require_executable(bwrap_executable, "CODEX_SUPERVISOR_BWRAP_UNAVAILABLE")
    python = _require_executable(python_executable, "CODEX_SUPERVISOR_PYTHON_UNAVAILABLE")
    script = (
        "import json,os,pathlib,socket,tempfile;"
        "w=pathlib.Path(os.environ['PROBE_WORKSPACE']);"
        "targets={'workspace':w/'.supervisor-probe','main':pathlib.Path(os.environ['PROBE_MAIN'])/'.supervisor-probe',"
        "'git':pathlib.Path(os.environ['PROBE_GIT'])/'.supervisor-probe','codex':w/'.codex/.supervisor-probe','agents':w/'.agents/.supervisor-probe'};"
        "out={};"
        "\nfor k,p in targets.items():\n"
        " try:p.write_text('probe');out[k]=True;p.unlink()\n"
        " except OSError:out[k]=False\n"
        "out['tmp_private']=pathlib.Path(tempfile.gettempdir()).resolve()==pathlib.Path('/tmp');"
        "\ntry:socket.socket().connect(('127.0.0.1',9));out['network']=True\n"
        "except OSError:out['network']=False\n"
        "print(json.dumps(out,sort_keys=True))"
    )
    git_common = codex_binding._git_output(
        ["git", "rev-parse", "--git-common-dir"], cwd=root, runner=subprocess.run
    )
    git_path = (root / git_common).resolve(strict=True)
    main_root = Path(worktree_ledger.main_worktree_root(root)).resolve(strict=True)
    return tuple([
        bwrap, "--die-with-parent", "--new-session", "--unshare-net",
        "--ro-bind", "/", "/", "--bind", str(root), str(root),
        "--ro-bind", str(root / ".git"), str(root / ".git"),
        "--ro-bind", str(root / ".codex"), str(root / ".codex"),
        "--ro-bind", str(root / ".agents"), str(root / ".agents"),
        "--tmpfs", "/tmp", "--setenv", "TMPDIR", "/tmp",
        "--setenv", "PROBE_WORKSPACE", str(root),
        "--setenv", "PROBE_MAIN", str(main_root),
        "--setenv", "PROBE_GIT", str(git_path),
        "--chdir", str(root), "--", python, "-c", script,
    ])


def validate_probe_result(stdout: str, exit_code: int) -> dict[str, bool]:
    if exit_code != 0:
        raise CodexSupervisorError("CODEX_SUPERVISOR_PROBE_EXIT_NONZERO", str(exit_code))
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise CodexSupervisorError("CODEX_SUPERVISOR_PROBE_JSON_INVALID") from exc
    expected = {
        "workspace": True, "main": False, "git": False, "codex": False,
        "agents": False, "tmp_private": True, "network": False,
    }
    if result != expected:
        raise CodexSupervisorError(
            "CODEX_SUPERVISOR_PROBE_BOUNDARY_MISMATCH",
            json.dumps(result, sort_keys=True),
        )
    return result


def _record_attempt(
    spec: SupervisorSpec,
    *,
    now: datetime,
    state: str,
    evidence: Mapping[str, Any],
) -> None:
    root, entry = codex_binding._one_by_task(spec.repo_root, spec.task_key)
    stamp = _stamp(now)

    def mutate(document: dict[str, Any]) -> None:
        target = next(
            (item for item in document["entries"] if item.get("entry_id") == entry["entry_id"]),
            None,
        )
        if target is None:
            raise CodexSupervisorError("CODEX_SUPERVISOR_BINDING_MISSING", spec.task_key)
        attempts = target.setdefault("supervisor_attempts", [])
        if not isinstance(attempts, list):
            raise CodexSupervisorError("CODEX_SUPERVISOR_LEDGER_CORRUPT", "supervisor_attempts")
        attempts.append({"at": stamp, "state": state, **dict(evidence)})

    try:
        worktree_ledger.update_ledger(root, mutate)
    except worktree_ledger.LedgerError as exc:
        raise CodexSupervisorError(exc.reason, exc.detail) from exc


def _handoff_is_valid(spec: SupervisorSpec) -> bool:
    handoff = spec.workspace / spec.handoff_path
    try:
        codex_binding._assert_no_symlink_components(spec.workspace, spec.handoff_path)
        return handoff.is_file() and not handoff.is_symlink() and handoff.stat().st_size > 0
    except (OSError, codex_binding.CodexBindingError):
        return False


def run_supervised(
    spec: SupervisorSpec,
    *,
    prompt: str,
    now: datetime,
    bwrap_executable: Path | str,
    codex_executable: Path | str,
    runner: ProcessRunner | None = None,
    resume_thread: str | None = None,
) -> SupervisedResult:
    """prepared bindingを検証し、process/thread観測をledgerへ残す。"""

    if spec.role not in codex_binding.TARGET_ROLES:
        raise CodexSupervisorError("CODEX_SUPERVISOR_ROLE_INVALID", spec.role)
    if not isinstance(prompt, str) or not prompt.strip():
        raise CodexSupervisorError("CODEX_SUPERVISOR_PROMPT_INVALID")
    if spec.timeout_seconds <= 0:
        raise CodexSupervisorError("CODEX_SUPERVISOR_TIMEOUT_INVALID")
    if resume_thread is None:
        entry = codex_binding.validate_spawn_binding(
            repo_root=spec.repo_root, role=spec.role, task_key=spec.task_key, now=now
        )
    else:
        entry = codex_binding.verify_command_binding(
            repo_root=spec.repo_root, workspace=spec.workspace, role=spec.role,
            agent_id=resume_thread,
        )
    if entry["workspace"] != str(spec.workspace.resolve(strict=True)):
        raise CodexSupervisorError("CODEX_SUPERVISOR_WORKSPACE_MISMATCH")
    if entry["handoff_path"] != spec.handoff_path:
        raise CodexSupervisorError("CODEX_SUPERVISOR_HANDOFF_MISMATCH")
    command = build_codex_command(
        spec, bwrap_executable=bwrap_executable, codex_executable=codex_executable,
        resume_thread=resume_thread,
    )
    actual_runner = runner or SubprocessJsonlRunner()
    bound_thread: str | None = None
    process_identity: tuple[int, str] | None = None

    def process_started(pid: int, token: str) -> None:
        nonlocal process_identity
        if process_identity is not None:
            raise CodexSupervisorError("CODEX_SUPERVISOR_PROCESS_DUPLICATE")
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            raise CodexSupervisorError("CODEX_SUPERVISOR_PID_INVALID", repr(pid))
        if not isinstance(token, str) or not token.isdigit():
            raise CodexSupervisorError("CODEX_SUPERVISOR_PROCESS_TOKEN_INVALID", repr(token))
        process_identity = (pid, token)
        _record_attempt(
            spec, now=now, state="spawned",
            evidence={"pid": pid, "process_start_token": token},
        )

    def started(thread_id: str) -> None:
        nonlocal bound_thread
        if resume_thread is not None and thread_id != resume_thread:
            raise CodexSupervisorError(
                "CODEX_SUPERVISOR_RESUME_THREAD_MISMATCH", f"{resume_thread}!={thread_id}"
            )
        codex_binding.bind_agent_identity(
            repo_root=spec.repo_root, workspace=spec.workspace, role=spec.role,
            task_key=spec.task_key, agent_id=thread_id, now=now,
        )
        bound_thread = thread_id
        if process_identity is None:
            raise CodexSupervisorError("CODEX_SUPERVISOR_PROCESS_IDENTITY_MISSING")
        _record_attempt(
            spec, now=now, state="running",
            evidence={
                "pid": process_identity[0],
                "process_start_token": process_identity[1],
                "thread_id": thread_id,
            },
        )

    observer = CodexJsonlObserver(started)
    try:
        process = actual_runner(
            command, cwd=spec.workspace, env=os.environ, prompt=prompt,
            timeout_seconds=spec.timeout_seconds, on_process_started=process_started,
            on_stdout_line=observer.feed,
        )
        evidence = {
            "pid": process.pid,
            "process_start_token": process.process_start_token,
            "thread_id": observer.thread_id,
            "terminal_event": observer.terminal_event,
            "exit_code": process.exit_code,
            "timed_out": process.timed_out,
            "killed": process.killed,
        }
        state = observer.finalize(process, handoff_exists=_handoff_is_valid(spec))
        if state == "paused_rate_limit":
            resume = build_codex_command(
                spec, bwrap_executable=bwrap_executable, codex_executable=codex_executable,
                resume_thread=observer.thread_id,
            )
            _record_attempt(spec, now=now, state=state, evidence=evidence)
            return SupervisedResult(state, observer.thread_id or "", observer.terminal_event, process, resume)
        _record_attempt(spec, now=now, state=state, evidence=evidence)
        return SupervisedResult(state, observer.thread_id or "", observer.terminal_event, process)
    except BaseException as exc:
        reason = exc.reason if isinstance(exc, CodexSupervisorError) else type(exc).__name__
        _record_attempt(
            spec, now=now, state="failed",
            evidence={"thread_id": bound_thread, "reason": reason},
        )
        raise


def publish_allowlist(role: str) -> tuple[str, ...]:
    """Codex終了後にhost supervisorが許可する外部publish操作。"""

    if role == "issue-implementer":
        return ("gitgate.add", "gitgate.commit", "gitgate.push", "gh.pr.create")
    if role == "issue-fixer":
        return ("gitgate.add", "gitgate.commit", "gitgate.push")
    raise CodexSupervisorError("CODEX_SUPERVISOR_ROLE_INVALID", role)
