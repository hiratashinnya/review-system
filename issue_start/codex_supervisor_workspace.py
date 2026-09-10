"""Codex supervisor 用の worktree/Git/launch-ledger 境界。

``collaboration.spawn_agent`` の binding とは無関係である。owner が ``run`` に渡した
launch spec を live Git facts と照合し、同じ ledger lock transaction で immutable
launch record と最初の attempt reservation を作る。
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from . import worktree_ledger


TARGET_ROLES = frozenset({"issue-implementer", "issue-fixer"})
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_OID = re.compile(r"^[0-9a-f]{40}$")
_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_TASK_KEY = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
_IMPLEMENTER_TASK = re.compile(r"^issue_([1-9][0-9]*)$")
_FIXER_TASK = re.compile(r"^issue_([1-9][0-9]*)_fix_r([1-9][0-9]*)$")
_HTTPS_REMOTE = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$")
_SSH_REMOTE = re.compile(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$")
_HANDOFF_SUFFIX = re.compile(r"^[A-Za-z0-9._-]*$")
_PROTECTED_ROOTS = (".codex/", ".agents/", ".ai/agents/")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SupervisorWorkspaceError(RuntimeError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class GitFacts:
    workspace: str
    main_root: str
    worktree_path: str
    repository: str
    branch_name: str
    head_oid: str


def stamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_TIME_NAIVE")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_git(
    argv: Sequence[str], *, cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    allow_nonzero: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        result = runner(list(argv), cwd=str(cwd), text=True, capture_output=True,
                        check=False, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_GIT_UNAVAILABLE", " ".join(argv)) from exc
    if result.returncode != 0 and not allow_nonzero:
        raise SupervisorWorkspaceError(
            "CODEX_SUPERVISOR_GIT_FAILED", (result.stderr or result.stdout or "").strip()[:300]
        )
    return result


def git_output(argv: Sequence[str], *, cwd: Path,
               runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> str:
    value = run_git(argv, cwd=cwd, runner=runner).stdout.strip()
    if not value:
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_GIT_OUTPUT_EMPTY", " ".join(argv))
    return value


def _canonical_repository(remote: str) -> str:
    match = _HTTPS_REMOTE.fullmatch(remote) or _SSH_REMOTE.fullmatch(remote)
    if match is None:
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ORIGIN_INVALID", remote)
    value = f"{match.group(1)}/{match.group(2)}"
    if not _REPOSITORY.fullmatch(value):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_REPOSITORY_INVALID", value)
    return value


def inspect_git_facts(
    workspace: Path | str,
    *, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> GitFacts:
    path = Path(workspace)
    if not path.is_absolute():
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_WORKSPACE_NOT_ABSOLUTE", str(path))
    try:
        resolved = path.resolve(strict=True)
        top = Path(git_output(["git", "rev-parse", "--show-toplevel"], cwd=resolved,
                              runner=runner)).resolve(strict=True)
        main_root = worktree_ledger.main_worktree_root(resolved).resolve(strict=True)
        relative = resolved.relative_to(main_root)
    except (OSError, RuntimeError, ValueError, worktree_ledger.LedgerError) as exc:
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_WORKSPACE_INVALID", str(path)) from exc
    if top != resolved or len(relative.parts) != 2 or relative.parts[0] != ".worktrees":
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_WORKSPACE_NOT_DEDICATED", str(resolved))
    registered = {
        str(Path(line[9:]).resolve(strict=True))
        for line in git_output(["git", "worktree", "list", "--porcelain"], cwd=main_root,
                               runner=runner).splitlines()
        if line.startswith("worktree ")
    }
    if str(resolved) not in registered:
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_WORKTREE_UNREGISTERED", str(resolved))
    repository = _canonical_repository(
        git_output(["git", "remote", "get-url", "origin"], cwd=resolved, runner=runner)
    )
    branch = git_output(["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
                        cwd=resolved, runner=runner)
    oid = git_output(["git", "rev-parse", "HEAD"], cwd=resolved, runner=runner)
    if not _BRANCH.fullmatch(branch) or ".." in branch or branch.endswith("/"):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_BRANCH_INVALID", branch)
    if not _OID.fullmatch(oid):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_OID_INVALID", oid)
    return GitFacts(str(resolved), str(main_root), relative.as_posix(), repository, branch, oid)


def validate_handoff_path(role: str, issue: int, round_number: int, value: str) -> str:
    path = Path(value)
    if (not value or path.is_absolute() or ".." in path.parts or len(path.parts) != 3
            or path.parts[:2] != ("tmp", "_handoff") or path.suffix != ".yaml"):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_HANDOFF_INVALID", value)
    prefix = (f"issue-implementer--issue-{issue}" if role == "issue-implementer"
              else f"issue-fixer--issue-{issue}-r{round_number}")
    suffix = path.name[:-5].removeprefix(prefix)
    if not path.name[:-5].startswith(prefix) or (suffix and not suffix.startswith("-")) \
            or not _HANDOFF_SUFFIX.fullmatch(suffix):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_HANDOFF_MISMATCH", value)
    return path.as_posix()


def assert_no_symlink_components(workspace: Path, relative: str) -> None:
    current = workspace
    for part in Path(relative).parts:
        current /= part
        if current.is_symlink():
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_HANDOFF_SYMLINK", str(current))
        if not current.exists():
            break


def validate_launch_identity(*, issue: int, round_number: int, repository: str,
                             role: str, task_key: str, handoff_path: str,
                             branch_name: str, expected_oid: str,
                             protected_paths: Sequence[str]) -> tuple[str, list[dict[str, str]]]:
    if role not in TARGET_ROLES:
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ROLE_INVALID", role)
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ISSUE_INVALID")
    if not isinstance(round_number, int) or isinstance(round_number, bool) or round_number < 1:
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ROUND_INVALID")
    if not _REPOSITORY.fullmatch(repository) or not _BRANCH.fullmatch(branch_name) \
            or not _OID.fullmatch(expected_oid) or not _TASK_KEY.fullmatch(task_key):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LAUNCH_IDENTITY_INVALID")
    pattern = _IMPLEMENTER_TASK if role == "issue-implementer" else _FIXER_TASK
    match = pattern.fullmatch(task_key)
    if match is None or int(match.group(1)) != issue or (
        role == "issue-implementer" and round_number != 1
    ) or (role == "issue-fixer" and int(match.group(2)) != round_number):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_TASK_KEY_MISMATCH", task_key)
    handoff = validate_handoff_path(role, issue, round_number, handoff_path)
    plan: list[dict[str, str]] = []
    for value in protected_paths:
        relative, separator, digest = value.rpartition("=")
        parsed = PurePosixPath(relative)
        if (separator != "=" or parsed.is_absolute() or str(parsed) != relative
                or any(part in {"", ".", ".."} for part in parsed.parts)
                or not relative.startswith(_PROTECTED_ROOTS) or not _SHA256.fullmatch(digest)):
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_PROTECTED_PATH_INVALID", value)
        plan.append({"path": relative, "base_sha256": digest})
    if len({item["path"] for item in plan}) != len(plan):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_PROTECTED_PATH_INVALID", "duplicate")
    return handoff, sorted(plan, key=lambda item: item["path"])


def one_by_task(repo_root: Path | str, task_key: str) -> tuple[Path, dict[str, Any]]:
    try:
        root = worktree_ledger.main_worktree_root(repo_root)
        entries = worktree_ledger.read_ledger(root)["entries"]
    except worktree_ledger.LedgerError as exc:
        raise SupervisorWorkspaceError(exc.reason, exc.detail) from exc
    matches = [item for item in entries if item.get("platform") == "codex-supervisor"
               and item.get("task_key") == task_key]
    if len(matches) != 1:
        raise SupervisorWorkspaceError(
            "CODEX_SUPERVISOR_LAUNCH_MISSING" if not matches else "CODEX_SUPERVISOR_LAUNCH_DUPLICATE",
            task_key,
        )
    return root, matches[0]


def assert_live_entry(entry: Mapping[str, Any], workspace: Path | str,
                      *, allow_descendant: bool) -> GitFacts:
    facts = inspect_git_facts(workspace)
    expected = (entry.get("workspace"), entry.get("repository"), entry.get("branch_name"))
    actual = (facts.workspace, facts.repository, facts.branch_name)
    if actual != expected:
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LIVE_FACT_MISMATCH")
    initial = entry.get("initial_oid")
    if facts.head_oid != initial:
        if not allow_descendant or run_git(
            ["git", "merge-base", "--is-ancestor", str(initial), facts.head_oid],
            cwd=Path(facts.workspace), allow_nonzero=True,
        ).returncode != 0:
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_STALE_OID", facts.head_oid)
    assert_no_symlink_components(Path(facts.workspace), str(entry.get("handoff_path", "")))
    return facts


def reserve_launch_attempt(
    *, repo_root: Path | str, workspace: Path | str, issue: int, round_number: int,
    repository: str, branch_name: str, expected_oid: str, role: str, task_key: str,
    handoff_path: str, protected_paths: Sequence[str], attempt_id: str,
    resume_thread: str | None, owner_pid: int, owner_start_token: str,
    now: datetime, lease_seconds: int,
) -> dict[str, Any]:
    """launch record作成とattempt予約を単一ledger transactionで行う。"""

    handoff, plan = validate_launch_identity(
        issue=issue, round_number=round_number, repository=repository, role=role,
        task_key=task_key, handoff_path=handoff_path, branch_name=branch_name,
        expected_oid=expected_oid, protected_paths=protected_paths,
    )
    facts = inspect_git_facts(workspace)
    if (facts.repository, facts.branch_name, facts.head_oid) != (
        repository, branch_name, expected_oid
    ):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LAUNCH_GIT_FACT_MISMATCH")
    assert_no_symlink_components(Path(facts.workspace), handoff)
    main = Path(facts.main_root)
    requested = {
        "issue": issue, "round": round_number, "repository": repository,
        "workspace": facts.workspace, "worktree_path": facts.worktree_path,
        "branch_name": branch_name, "initial_oid": expected_oid,
        "handoff_path": handoff, "agent_type": role, "task_key": task_key,
        "protected_plan": plan,
    }
    reserved: dict[str, Any] = {}
    at = stamp(now)
    lease = stamp(now + timedelta(seconds=lease_seconds))

    def alive(pid: Any, token: Any) -> bool:
        if not isinstance(pid, int) or isinstance(pid, bool) or not isinstance(token, str):
            return False
        try:
            return Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()[21] == token
        except (OSError, IndexError):
            return False

    def mutate(document: dict[str, Any]) -> None:
        matches = [item for item in document["entries"]
                   if item.get("platform") == "codex-supervisor"
                   and item.get("task_key") == task_key]
        if len(matches) > 1:
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LAUNCH_DUPLICATE", task_key)
        if not matches:
            if resume_thread is not None:
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_RESUME_STATE_INVALID")
            if any(item.get("platform") == "codex-supervisor"
                   and item.get("workspace") == facts.workspace
                   and item.get("status") not in worktree_ledger.TERMINAL_STATUSES
                   for item in document["entries"]):
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_WORKSPACE_OWNED", facts.workspace)
            entry = {
                "entry_id": worktree_ledger._new_entry_id(
                    {item.get("entry_id") for item in document["entries"]}
                ),
                **requested, "platform": "codex-supervisor", "status": "running",
                "agent_id": None, "launched_at": at, "supervisor_attempts": [],
                "publish_attempts": [], "notes": [],
            }
            document["entries"].append(entry)
        else:
            entry = matches[0]
            if any(entry.get(key) != value for key, value in requested.items()):
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LAUNCH_IMMUTABLE_MISMATCH")
            assert_live_entry(entry, workspace, allow_descendant=True)
        attempts = entry.get("supervisor_attempts")
        if not isinstance(attempts, list):
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LEDGER_CORRUPT")
        latest = attempts[-1] if attempts else None
        basis = latest
        if isinstance(latest, dict) and latest.get("state") in {"reserved", "spawned", "running"}:
            if alive(latest.get("owner_pid"), latest.get("owner_start_token")) \
                    or alive(latest.get("pid"), latest.get("process_start_token")):
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ATTEMPT_ACTIVE")
            try:
                unexpired = now < datetime.fromisoformat(
                    str(latest.get("lease_expires_at", "")).replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LEDGER_CORRUPT") from exc
            if unexpired:
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ATTEMPT_ACTIVE")
            attempts.append({"at": at, "attempt_id": latest.get("attempt_id"),
                             "state": "expired", "reason": "owner_exit_after_lease"})
        if resume_thread is not None:
            expired_ids = {
                event.get("attempt_id") for event in attempts
                if isinstance(event, dict) and event.get("state") == "expired"
            }
            basis = next(
                (
                    event for event in reversed(attempts)
                    if isinstance(event, dict) and event.get("attempt_id") not in expired_ids
                ),
                None,
            )
            if not isinstance(basis, dict) or basis.get("thread_id") != resume_thread:
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_RESUME_STATE_INVALID")
            if basis.get("state") != "paused_rate_limit":
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_RESUME_STATE_INVALID")
        attempts.append({
            "at": at, "attempt_id": attempt_id, "state": "reserved",
            "lease_expires_at": lease, "resume_thread": resume_thread,
            "owner_pid": owner_pid, "owner_start_token": owner_start_token,
            "transport_contract": "codex-supervisor/direct-exec-v1",
        })
        reserved.update(entry)

    try:
        worktree_ledger.update_ledger(main, mutate)
    except worktree_ledger.LedgerError as exc:
        raise SupervisorWorkspaceError(exc.reason, exc.detail) from exc
    return reserved


def reserve_canonical_launch_attempt(
    *, repo_root: Path | str, ledger_entry_id: str, workspace: Path | str,
    issue: int, round_number: int, repository: str, branch_name: str,
    expected_oid: str, role: str, task_key: str, handoff_path: str,
    protected_paths: Sequence[str], intent_digest: str, attempt_id: str,
    mode: str, owner_pid: int, owner_start_token: str, now: datetime,
    lease_seconds: int,
) -> tuple[dict[str, Any], str | None]:
    """Reserve the issuer-created canonical entry; never create a second entry."""

    if mode not in {"run", "resume"} or not re.fullmatch(r"[0-9a-f]{64}", intent_digest):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LAUNCH_REQUEST_INVALID")
    handoff, plan = validate_launch_identity(
        issue=issue, round_number=round_number, repository=repository, role=role,
        task_key=task_key, handoff_path=handoff_path, branch_name=branch_name,
        expected_oid=expected_oid, protected_paths=protected_paths,
    )
    facts = inspect_git_facts(workspace)
    if (facts.repository, facts.branch_name, facts.head_oid) != (
        repository, branch_name, expected_oid,
    ):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LAUNCH_GIT_FACT_MISMATCH")
    root = Path(facts.main_root)
    at = stamp(now)
    lease = stamp(now + timedelta(seconds=lease_seconds))
    result: dict[str, Any] = {}

    def alive(pid: Any, token: Any) -> bool:
        if not isinstance(pid, int) or isinstance(pid, bool) or not isinstance(token, str):
            return False
        try:
            return Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()[21] == token
        except (OSError, IndexError):
            return False

    def mutate(document: dict[str, Any]) -> None:
        matches = [item for item in document["entries"]
                   if item.get("entry_id") == ledger_entry_id]
        if len(matches) != 1:
            raise SupervisorWorkspaceError(
                "CODEX_SUPERVISOR_LAUNCH_MISSING" if not matches
                else "CODEX_SUPERVISOR_LAUNCH_DUPLICATE", ledger_entry_id,
            )
        entry = matches[0]
        expected = {
            "platform": "codex-supervisor", "issue": issue, "agent_type": role,
            "round": None if role == "issue-implementer" else round_number,
            "repository": repository, "workspace": facts.workspace,
            "branch_name": branch_name, "initial_oid": expected_oid,
            "task_key": task_key, "handoff_path": handoff, "protected_plan": plan,
        }
        if any(entry.get(key) != value for key, value in expected.items()):
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LAUNCH_IMMUTABLE_MISMATCH")
        recorded = entry.get("launch_intent_digest")
        if recorded not in (None, intent_digest):
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_INTENT_DIGEST_MISMATCH")
        entry["launch_intent_digest"] = intent_digest
        attempts = entry.setdefault("supervisor_attempts", [])
        if not isinstance(attempts, list):
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LEDGER_CORRUPT")
        latest = attempts[-1] if attempts else None
        if isinstance(latest, dict) and latest.get("state") in {"reserved", "spawned", "running"}:
            if alive(latest.get("owner_pid"), latest.get("owner_start_token")) \
                    or alive(latest.get("pid"), latest.get("process_start_token")):
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ATTEMPT_ACTIVE")
            try:
                unexpired = now < datetime.fromisoformat(
                    str(latest.get("lease_expires_at", "")).replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LEDGER_CORRUPT") from exc
            if unexpired:
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ATTEMPT_ACTIVE")
            attempts.append({"at": at, "attempt_id": latest.get("attempt_id"),
                             "state": "expired", "reason": "owner_exit_after_lease"})
        expired_ids = {
            event.get("attempt_id") for event in attempts
            if isinstance(event, dict) and event.get("state") == "expired"
        }
        basis = next((
            event for event in reversed(attempts)
            if isinstance(event, dict) and event.get("attempt_id") not in expired_ids
        ), None)
        paused = basis if isinstance(basis, dict) and basis.get("state") == "paused_rate_limit" else None
        if mode == "run" and paused is not None:
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_RESUME_REQUIRED")
        if mode == "resume":
            if paused is None or not isinstance(entry.get("agent_id"), str) \
                    or paused.get("thread_id") != entry.get("agent_id"):
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_RESUME_STATE_INVALID")
            resume_thread = entry["agent_id"]
        else:
            if isinstance(basis, dict) and basis.get("state") == "succeeded":
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_RUN_STATE_INVALID")
            resume_thread = None
        attempts.append({
            "at": at, "attempt_id": attempt_id, "state": "reserved",
            "lease_expires_at": lease, "resume_thread": resume_thread,
            "owner_pid": owner_pid, "owner_start_token": owner_start_token,
            "intent_digest": intent_digest,
            "transport_contract": "codex-supervisor/direct-exec-v2",
        })
        entry["status"] = "running"
        result.update(entry)
        result["_resume_thread"] = resume_thread

    try:
        worktree_ledger.update_ledger(root, mutate)
    except worktree_ledger.LedgerError as exc:
        raise SupervisorWorkspaceError(exc.reason, exc.detail) from exc
    return result, result.pop("_resume_thread")


def verify_canonical_launch_reservation(
    *, repo_root: Path | str, ledger_entry_id: str, attempt_id: str,
    intent_digest: str, owner_pid: int, owner_start_token: str,
    workspace: Path | str, repository: str, branch_name: str, expected_oid: str,
) -> "CanonicalLaunchReservationLease":
    """Recheck authority and return the still-held ledger lease.

    The caller must retain this lease only until ``Popen`` has produced a PID and
    :meth:`CanonicalLaunchReservationLease.record_process_started` records that
    identity.  Every failure path must call ``release``; the lease is intentionally
    not held during model execution.
    """

    try:
        ledger_lease = worktree_ledger.acquire_ledger_lease(repo_root)
    except worktree_ledger.LedgerError as exc:
        raise SupervisorWorkspaceError(exc.reason, exc.detail) from exc
    try:
        document = ledger_lease.document
        matches = [item for item in document["entries"]
                   if item.get("entry_id") == ledger_entry_id]
        if len(matches) != 1:
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ATTEMPT_FENCED")
        entry = matches[0]
        attempts = entry.get("supervisor_attempts")
        latest = attempts[-1] if isinstance(attempts, list) and attempts else None
        if (entry.get("platform") != "codex-supervisor"
                or entry.get("launch_intent_digest") != intent_digest
                or not isinstance(latest, dict) or latest.get("attempt_id") != attempt_id
                or latest.get("state") != "reserved"
                or latest.get("owner_pid") != owner_pid
                or latest.get("owner_start_token") != owner_start_token
                or latest.get("intent_digest") != intent_digest):
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ATTEMPT_FENCED")
        try:
            actual_owner_token = Path(f"/proc/{owner_pid}/stat").read_text(
                encoding="utf-8"
            )
            actual_owner_token = actual_owner_token[
                actual_owner_token.rfind(")") + 2:
            ].split()[19]
        except (OSError, IndexError) as exc:
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ATTEMPT_FENCED") from exc
        if actual_owner_token != owner_start_token:
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ATTEMPT_FENCED")
        facts = inspect_git_facts(workspace)
        if (facts.repository, facts.branch_name, facts.head_oid) != (
            repository, branch_name, expected_oid,
        ):
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_LAUNCH_GIT_FACT_MISMATCH")
        return CanonicalLaunchReservationLease(
            ledger_lease, ledger_entry_id=ledger_entry_id, attempt_id=attempt_id,
            owner_pid=owner_pid, owner_start_token=owner_start_token,
        )
    except BaseException:
        ledger_lease.release()
        raise


class CanonicalLaunchReservationLease:
    """Verified reservation whose ledger flock spans the process-start boundary."""

    def __init__(self, ledger_lease: worktree_ledger.LedgerLease, *,
                 ledger_entry_id: str, attempt_id: str, owner_pid: int,
                 owner_start_token: str) -> None:
        self._ledger_lease = ledger_lease
        self._ledger_entry_id = ledger_entry_id
        self._attempt_id = attempt_id
        self._owner_pid = owner_pid
        self._owner_start_token = owner_start_token

    @property
    def closed(self) -> bool:
        return self._ledger_lease.closed

    def record_process_started(self, pid: int, process_start_token: str,
                               *, now: datetime) -> None:
        """Append ``spawned`` while locked, commit, then release immediately."""

        try:
            if (not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0
                    or not isinstance(process_start_token, str)
                    or not process_start_token.isdigit()):
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_PROCESS_IDENTITY_INVALID")
            entry = next(
                (item for item in self._ledger_lease.document["entries"]
                 if item.get("entry_id") == self._ledger_entry_id),
                None,
            )
            attempts = entry.get("supervisor_attempts") if isinstance(entry, dict) else None
            latest = attempts[-1] if isinstance(attempts, list) and attempts else None
            if (not isinstance(latest, dict)
                    or latest.get("attempt_id") != self._attempt_id
                    or latest.get("state") != "reserved"
                    or latest.get("owner_pid") != self._owner_pid
                    or latest.get("owner_start_token") != self._owner_start_token):
                raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ATTEMPT_FENCED")
            attempts.append({
                "at": stamp(now), "attempt_id": self._attempt_id, "state": "spawned",
                "owner_pid": self._owner_pid,
                "owner_start_token": self._owner_start_token,
                "lease_expires_at": latest.get("lease_expires_at"),
                "transport_contract": latest.get("transport_contract"),
                "pid": pid, "process_start_token": process_start_token,
            })
            self._ledger_lease.commit()
        except worktree_ledger.LedgerError as exc:
            raise SupervisorWorkspaceError(exc.reason, exc.detail) from exc
        finally:
            self.release()

    def release(self) -> None:
        self._ledger_lease.release()


def bind_thread(*, repo_root: Path | str, task_key: str, workspace: Path | str,
                role: str, thread_id: str, now: datetime) -> dict[str, Any]:
    root, entry = one_by_task(repo_root, task_key)
    if entry.get("agent_type") != role or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", thread_id):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_THREAD_BINDING_INVALID")
    assert_live_entry(entry, workspace, allow_descendant=True)
    bound: dict[str, Any] = {}
    def mutate(document: dict[str, Any]) -> None:
        target = next(item for item in document["entries"] if item.get("entry_id") == entry["entry_id"])
        existing = target.get("agent_id")
        if existing not in (None, thread_id):
            raise SupervisorWorkspaceError("CODEX_SUPERVISOR_THREAD_MISMATCH")
        target["agent_id"] = thread_id
        target["bound_at"] = stamp(now)
        bound.update(target)
    worktree_ledger.update_ledger(root, mutate)
    return bound


def verify_active(*, repo_root: Path | str, task_key: str, workspace: Path | str,
                  role: str) -> dict[str, Any]:
    _root, entry = one_by_task(repo_root, task_key)
    if entry.get("agent_type") != role or not entry.get("agent_id"):
        raise SupervisorWorkspaceError("CODEX_SUPERVISOR_ACTIVE_MISSING")
    assert_live_entry(entry, workspace, allow_descendant=True)
    return dict(entry)
