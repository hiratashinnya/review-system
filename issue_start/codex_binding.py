"""Codex Issue dispatch を専用 worktree へ事前束縛する durable ledger。

``collaboration.spawn_agent`` の ``message`` は暗号化されるため、binding の入力には使わない。
主文脈が ``prepare`` で ownership ledger に記録した値は、spawn 前には非破壊で
検証するだけとする。``open -> running`` の不可逆遷移は、spawn 成功後に trusted
observer が actual agent identity と実効 workspace を同時に観測したときだけ行う。

``collaboration.spawn_agent`` transportはchild/effective workspace、actual agent identity、spawn成功の
いずれもtrusted payloadとして提供しないため、issue-start gateでfail-closeする。別経路のrepo supervisorは
Issue専用worktreeで別Codex CLI processを起動し、OS PID/start tokenとJSONL threadをtrusted observationとして
取得した場合だけ本moduleのbind/verify APIを使う。

状態は既存 :mod:`issue_start.worktree_ledger` の ``open -> running -> stopped ->
collected -> released`` を使う。spawn 前の失敗では ``open`` を削除・終端化せず、TTL 内はそのまま
再検証できる。TTL を越えた ``open`` は同一 canonical task と完全に同じ dispatch identity の場合だけ
同じ entry を原子的に refresh し、旧期限を ``refresh_history`` へ残す。Claude の
``.claude/worktrees`` lifecycle は既存 entry のまま分岐させず、Codex entry だけ
``platform: codex`` で識別する。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence, TextIO

from . import worktree_ledger


TARGET_ROLES = frozenset({"issue-implementer", "issue-fixer"})
DEFAULT_TTL_SECONDS = 900
MIN_TTL_SECONDS = 30
MAX_TTL_SECONDS = 3600
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_OID = re.compile(r"^[0-9a-f]{40}$")
_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_TASK_KEY = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_IMPLEMENTER_TASK = re.compile(r"^issue_([1-9][0-9]*)$")
_FIXER_TASK = re.compile(r"^issue_([1-9][0-9]*)_fix_r([1-9][0-9]*)$")
_HTTPS_REMOTE = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$")
_SSH_REMOTE = re.compile(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$")
_HANDOFF_SUFFIX = re.compile(r"^[A-Za-z0-9._-]*$")
_PROTECTED_PLAN_ROOTS = (".codex/", ".agents/", ".ai/agents/")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CodexBindingError(RuntimeError):
    """machine-readable reason と最小 detail を持つ fail-close 例外。"""

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


def _stamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CodexBindingError("CODEX_BINDING_TIME_NAIVE")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_stamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CodexBindingError("CODEX_BINDING_LEDGER_CORRUPT", "expires_at")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CodexBindingError("CODEX_BINDING_LEDGER_CORRUPT", "expires_at") from exc


def _run_git(
    argv: Sequence[str],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    allow_nonzero: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        result = runner(
            list(argv), cwd=str(cwd), text=True, capture_output=True, check=False, timeout=10
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CodexBindingError("CODEX_BINDING_GIT_UNAVAILABLE", " ".join(argv)) from exc
    if result.returncode != 0 and not allow_nonzero:
        detail = (result.stderr or result.stdout or "").strip()[:300]
        raise CodexBindingError("CODEX_BINDING_GIT_FAILED", detail)
    return result


def _git_output(
    argv: Sequence[str],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    value = _run_git(argv, cwd=cwd, runner=runner).stdout.strip()
    if not value:
        raise CodexBindingError("CODEX_BINDING_GIT_OUTPUT_EMPTY", " ".join(argv))
    return value


def _canonical_repository(remote: str) -> str:
    match = _HTTPS_REMOTE.fullmatch(remote) or _SSH_REMOTE.fullmatch(remote)
    if match is None:
        raise CodexBindingError("CODEX_BINDING_ORIGIN_INVALID", remote)
    value = f"{match.group(1)}/{match.group(2)}"
    if not _REPOSITORY.fullmatch(value):
        raise CodexBindingError("CODEX_BINDING_REPOSITORY_INVALID", value)
    return value


def _registered_worktrees(
    main_root: Path, runner: Callable[..., subprocess.CompletedProcess[str]]
) -> set[str]:
    output = _git_output(
        ["git", "worktree", "list", "--porcelain"], cwd=main_root, runner=runner
    )
    paths: set[str] = set()
    for line in output.splitlines():
        if not line.startswith("worktree "):
            continue
        try:
            paths.add(str(Path(line[9:]).resolve(strict=True)))
        except (OSError, RuntimeError) as exc:
            raise CodexBindingError("CODEX_BINDING_WORKTREE_UNRESOLVED", line[9:]) from exc
    return paths


def inspect_git_facts(
    workspace: Path | str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> GitFacts:
    """workspace の root/origin/branch/OID/登録状態を Git から再導出する。"""

    path = Path(workspace)
    if not path.is_absolute():
        raise CodexBindingError("CODEX_BINDING_WORKSPACE_NOT_ABSOLUTE", str(path))
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CodexBindingError("CODEX_BINDING_WORKSPACE_MISSING", str(path)) from exc
    if not resolved.is_dir():
        raise CodexBindingError("CODEX_BINDING_WORKSPACE_NOT_DIRECTORY", str(resolved))
    top = Path(
        _git_output(["git", "rev-parse", "--show-toplevel"], cwd=resolved, runner=runner)
    ).resolve(strict=True)
    if top != resolved:
        raise CodexBindingError("CODEX_BINDING_WORKSPACE_NOT_ROOT", str(top))
    try:
        main_root = worktree_ledger.main_worktree_root(resolved).resolve(strict=True)
        relative = resolved.relative_to(main_root)
    except (OSError, RuntimeError, ValueError, worktree_ledger.LedgerError) as exc:
        raise CodexBindingError("CODEX_BINDING_MAIN_ROOT_INVALID", str(resolved)) from exc
    if len(relative.parts) != 2 or relative.parts[0] != ".worktrees":
        raise CodexBindingError("CODEX_BINDING_WORKSPACE_NOT_DEDICATED", relative.as_posix())
    if str(resolved) not in _registered_worktrees(main_root, runner):
        raise CodexBindingError("CODEX_BINDING_WORKTREE_UNREGISTERED", str(resolved))
    repository = _canonical_repository(
        _git_output(["git", "remote", "get-url", "origin"], cwd=resolved, runner=runner)
    )
    branch_name = _git_output(
        ["git", "symbolic-ref", "--quiet", "--short", "HEAD"], cwd=resolved, runner=runner
    )
    head_oid = _git_output(["git", "rev-parse", "HEAD"], cwd=resolved, runner=runner)
    if not _BRANCH.fullmatch(branch_name) or ".." in branch_name or branch_name.endswith("/"):
        raise CodexBindingError("CODEX_BINDING_BRANCH_INVALID", branch_name)
    if not _OID.fullmatch(head_oid):
        raise CodexBindingError("CODEX_BINDING_OID_INVALID", head_oid)
    return GitFacts(
        workspace=str(resolved),
        main_root=str(main_root),
        worktree_path=relative.as_posix(),
        repository=repository,
        branch_name=branch_name,
        head_oid=head_oid,
    )


def _validate_task(role: str, task_key: str, issue: int, round_number: int) -> None:
    if role not in TARGET_ROLES:
        raise CodexBindingError("CODEX_BINDING_ROLE_INVALID", role)
    if not _TASK_KEY.fullmatch(task_key):
        raise CodexBindingError("CODEX_BINDING_TASK_KEY_INVALID", task_key)
    pattern = _IMPLEMENTER_TASK if role == "issue-implementer" else _FIXER_TASK
    match = pattern.fullmatch(task_key)
    if match is None or int(match.group(1)) != issue:
        raise CodexBindingError("CODEX_BINDING_TASK_KEY_MISMATCH", task_key)
    if role == "issue-implementer":
        if round_number != 1:
            raise CodexBindingError("CODEX_BINDING_ROUND_INVALID", str(round_number))
    elif int(match.group(2)) != round_number:
        raise CodexBindingError("CODEX_BINDING_TASK_KEY_MISMATCH", task_key)


def _validate_handoff(role: str, issue: int, round_number: int, value: str) -> str:
    if not isinstance(value, str) or not value:
        raise CodexBindingError("CODEX_BINDING_HANDOFF_MISSING")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or len(path.parts) != 3:
        raise CodexBindingError("CODEX_BINDING_HANDOFF_INVALID", value)
    if path.parts[:2] != ("tmp", "_handoff") or path.suffix != ".yaml":
        raise CodexBindingError("CODEX_BINDING_HANDOFF_INVALID", value)
    prefix = (
        f"issue-implementer--issue-{issue}"
        if role == "issue-implementer"
        else f"issue-fixer--issue-{issue}-r{round_number}"
    )
    stem = path.name[:-5]
    if not stem.startswith(prefix):
        raise CodexBindingError("CODEX_BINDING_HANDOFF_MISMATCH", value)
    suffix = stem[len(prefix):]
    if suffix and not suffix.startswith("-"):
        raise CodexBindingError("CODEX_BINDING_HANDOFF_MISMATCH", value)
    if not _HANDOFF_SUFFIX.fullmatch(suffix):
        raise CodexBindingError("CODEX_BINDING_HANDOFF_INVALID", value)
    return path.as_posix()


def _assert_no_symlink_components(workspace: Path, handoff_path: str) -> None:
    current = workspace
    for part in Path(handoff_path).parts:
        current = current / part
        if current.is_symlink():
            raise CodexBindingError("CODEX_BINDING_HANDOFF_SYMLINK", str(current))
        if not current.exists():
            break


def _validate_scalar_binding(
    *,
    issue: int,
    round_number: int,
    repository: str,
    branch_name: str,
    expected_oid: str,
    role: str,
    task_key: str,
    handoff_path: str,
) -> str:
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        raise CodexBindingError("CODEX_BINDING_ISSUE_INVALID", repr(issue))
    if not isinstance(round_number, int) or isinstance(round_number, bool) or round_number < 1:
        raise CodexBindingError("CODEX_BINDING_ROUND_INVALID", repr(round_number))
    if not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
        raise CodexBindingError("CODEX_BINDING_REPOSITORY_INVALID", repr(repository))
    if not isinstance(branch_name, str) or not _BRANCH.fullmatch(branch_name):
        raise CodexBindingError("CODEX_BINDING_BRANCH_INVALID", repr(branch_name))
    if not isinstance(expected_oid, str) or not _OID.fullmatch(expected_oid):
        raise CodexBindingError("CODEX_BINDING_OID_INVALID", repr(expected_oid))
    _validate_task(role, task_key, issue, round_number)
    return _validate_handoff(role, issue, round_number, handoff_path)


def prepare_binding(
    *,
    issue: int,
    round_number: int,
    repository: str,
    workspace: Path | str,
    branch_name: str,
    expected_oid: str,
    handoff_path: str,
    role: str,
    task_key: str,
    now: datetime,
    protected_paths: Sequence[str] = (),
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """検証済み Git facts と dispatch identity を ``open`` entry として事前記録する。"""

    handoff = _validate_scalar_binding(
        issue=issue,
        round_number=round_number,
        repository=repository,
        branch_name=branch_name,
        expected_oid=expected_oid,
        role=role,
        task_key=task_key,
        handoff_path=handoff_path,
    )
    approved_plan: list[dict[str, str]] = []
    if isinstance(protected_paths, (str, bytes)):
        raise CodexBindingError("CODEX_BINDING_PROTECTED_PATH_INVALID")
    for value in protected_paths:
        if not isinstance(value, str):
            raise CodexBindingError("CODEX_BINDING_PROTECTED_PATH_INVALID", repr(value))
        relative, separator, base_digest = value.rpartition("=")
        parsed = PurePosixPath(relative)
        if (
            separator != "="
            or not relative
            or parsed.is_absolute()
            or str(parsed) != relative
            or any(part in {"", ".", ".."} for part in parsed.parts)
            or not relative.startswith(_PROTECTED_PLAN_ROOTS)
            or _SHA256.fullmatch(base_digest) is None
        ):
            raise CodexBindingError("CODEX_BINDING_PROTECTED_PATH_INVALID", value)
        approved_plan.append({"path": relative, "base_sha256": base_digest})
    if len({item["path"] for item in approved_plan}) != len(approved_plan):
        raise CodexBindingError("CODEX_BINDING_PROTECTED_PATH_INVALID", "duplicate")
    approved_plan.sort(key=lambda item: item["path"])
    if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or not (
        MIN_TTL_SECONDS <= ttl_seconds <= MAX_TTL_SECONDS
    ):
        raise CodexBindingError("CODEX_BINDING_TTL_INVALID", repr(ttl_seconds))
    facts = inspect_git_facts(workspace, runner=runner)
    expected = (repository, branch_name, expected_oid)
    actual = (facts.repository, facts.branch_name, facts.head_oid)
    if actual != expected:
        labels = ("repository", "branch", "oid")
        mismatches = [
            f"{label}: expected={want} actual={got}"
            for label, want, got in zip(labels, expected, actual)
            if want != got
        ]
        raise CodexBindingError("CODEX_BINDING_GIT_FACT_MISMATCH", "; ".join(mismatches))
    _assert_no_symlink_components(Path(facts.workspace), handoff)
    prepared_at = _stamp(now)
    expires_at = _stamp(now + timedelta(seconds=ttl_seconds))
    created: dict[str, Any] = {}

    def mutate(document: dict) -> None:
        entries = document["entries"]
        same_task = [
            item for item in entries
            if item.get("platform") == "codex" and item.get("task_key") == task_key
        ]
        if same_task:
            if len(same_task) != 1:
                raise CodexBindingError("CODEX_BINDING_DUPLICATE", task_key)
            target = same_task[0]
            _assert_entry_shape(target)
            if target.get("status") != "open":
                raise CodexBindingError("CODEX_BINDING_TASK_REUSED", task_key)
            if now.astimezone(timezone.utc) < _parse_stamp(target["expires_at"]):
                raise CodexBindingError("CODEX_BINDING_TASK_REUSED", task_key)
            identity = {
                "issue": issue,
                "round": round_number,
                "repository": repository,
                "workspace": facts.workspace,
                "worktree_path": facts.worktree_path,
                "branch_name": branch_name,
                "expected_oid": expected_oid,
                "handoff_path": handoff,
                "agent_type": role,
                "task_key": task_key,
                "protected_plan": approved_plan,
            }
            mismatches = [
                key for key, value in identity.items() if target.get(key) != value
            ]
            if mismatches:
                raise CodexBindingError(
                    "CODEX_BINDING_REFRESH_IDENTITY_MISMATCH", ",".join(mismatches)
                )
            if target.get("agent_id") is not None or target.get("bound_at") is not None:
                raise CodexBindingError("CODEX_BINDING_LEDGER_CORRUPT", "open identity")
            history = target.setdefault("refresh_history", [])
            notes = target.setdefault("notes", [])
            if not isinstance(history, list) or not isinstance(notes, list):
                raise CodexBindingError("CODEX_BINDING_LEDGER_CORRUPT", "refresh audit")
            history.append({
                "refreshed_at": prepared_at,
                "previous_prepared_at": target.get("prepared_at"),
                "previous_expires_at": target["expires_at"],
                "new_expires_at": expires_at,
            })
            notes.append({
                "at": prepared_at,
                "note": "codex expired open binding refreshed for retry",
            })
            target["prepared_at"] = prepared_at
            target["expires_at"] = expires_at
            created.update(target)
            return
        active_workspace = [
            item for item in entries
            if item.get("platform") == "codex"
            and item.get("workspace") == facts.workspace
            and item.get("status") not in worktree_ledger.TERMINAL_STATUSES
        ]
        if active_workspace:
            raise CodexBindingError("CODEX_BINDING_WORKSPACE_OWNED", facts.workspace)
        existing = {item.get("entry_id") for item in entries}
        entry = {
            "entry_id": worktree_ledger._new_entry_id(existing),
            "issue": issue,
            "agent_type": role,
            "round": round_number,
            "branch_name": branch_name,
            "handoff_path": handoff,
            "dispatched_at": prepared_at,
            "agent_id": None,
            "worktree_path": facts.worktree_path,
            "status": "open",
            "collected_to": None,
            "closed_at": None,
            "notes": [],
            "platform": "codex",
            "repository": repository,
            "workspace": facts.workspace,
            "expected_oid": expected_oid,
            "task_key": task_key,
            "prepared_at": prepared_at,
            "expires_at": expires_at,
            "consumed_at": None,
            "bound_at": None,
            "refresh_history": [],
            "protected_plan": approved_plan,
        }
        entries.append(entry)
        created.update(entry)

    try:
        worktree_ledger.update_ledger(facts.main_root, mutate)
    except worktree_ledger.LedgerError as exc:
        raise CodexBindingError(exc.reason, exc.detail) from exc
    return dict(created)


def _codex_entries(repo_root: Path | str) -> tuple[Path, list[dict[str, Any]]]:
    try:
        root = worktree_ledger.main_worktree_root(repo_root)
        entries = worktree_ledger.read_ledger(root)["entries"]
    except worktree_ledger.LedgerError as exc:
        raise CodexBindingError(exc.reason, exc.detail) from exc
    return root, [item for item in entries if item.get("platform") == "codex"]


def _one_by_task(repo_root: Path | str, task_key: str) -> tuple[Path, dict[str, Any]]:
    root, entries = _codex_entries(repo_root)
    matches = [item for item in entries if item.get("task_key") == task_key]
    if not matches:
        raise CodexBindingError("CODEX_BINDING_MISSING", task_key)
    if len(matches) != 1:
        raise CodexBindingError("CODEX_BINDING_DUPLICATE", task_key)
    return root, matches[0]


def _assert_entry_shape(entry: Mapping[str, Any]) -> None:
    required = {
        "entry_id", "issue", "agent_type", "round", "branch_name", "handoff_path",
        "repository", "workspace", "expected_oid", "task_key", "expires_at", "status",
    }
    if any(key not in entry for key in required):
        raise CodexBindingError("CODEX_BINDING_LEDGER_CORRUPT", "missing field")
    _validate_scalar_binding(
        issue=entry["issue"],
        round_number=entry["round"],
        repository=entry["repository"],
        branch_name=entry["branch_name"],
        expected_oid=entry["expected_oid"],
        role=entry["agent_type"],
        task_key=entry["task_key"],
        handoff_path=entry["handoff_path"],
    )
    _parse_stamp(entry["expires_at"])


def _assert_live_facts(
    entry: Mapping[str, Any],
    *,
    workspace: Path | str,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    allow_descendant: bool,
) -> GitFacts:
    _assert_entry_shape(entry)
    facts = inspect_git_facts(workspace, runner=runner)
    if facts.workspace != entry["workspace"]:
        raise CodexBindingError("CODEX_BINDING_CWD_MISMATCH", facts.workspace)
    if facts.repository != entry["repository"]:
        raise CodexBindingError("CODEX_BINDING_ORIGIN_MISMATCH", facts.repository)
    if facts.branch_name != entry["branch_name"]:
        raise CodexBindingError("CODEX_BINDING_BRANCH_MISMATCH", facts.branch_name)
    expected_oid = entry["expected_oid"]
    if facts.head_oid != expected_oid:
        if not allow_descendant:
            raise CodexBindingError("CODEX_BINDING_STALE_OID", facts.head_oid)
        result = _run_git(
            ["git", "merge-base", "--is-ancestor", expected_oid, facts.head_oid],
            cwd=Path(facts.workspace), runner=runner, allow_nonzero=True,
        )
        if result.returncode != 0:
            raise CodexBindingError("CODEX_BINDING_STALE_OID", facts.head_oid)
    _assert_no_symlink_components(Path(facts.workspace), entry["handoff_path"])
    return facts


def validate_spawn_binding(
    *,
    repo_root: Path | str,
    role: str,
    task_key: str,
    now: datetime,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """spawn 前に prepared binding を非破壊で再検証する。

    PreToolUse 通過後に residue/blocker/API/router が失敗しても ``open`` を保つ。
    spawn 成功はこの層で観測できないため、``agent_id`` や ``status`` を書き込まない。
    """

    _root, entry = _one_by_task(repo_root, task_key)
    _assert_entry_shape(entry)
    if entry["agent_type"] != role:
        raise CodexBindingError("CODEX_BINDING_ROLE_MISMATCH", role)
    if entry["status"] != "open":
        raise CodexBindingError("CODEX_BINDING_TASK_REUSED", task_key)
    if now.astimezone(timezone.utc) >= _parse_stamp(entry["expires_at"]):
        raise CodexBindingError("CODEX_BINDING_EXPIRED", task_key)
    _assert_live_facts(
        entry, workspace=entry["workspace"], runner=runner, allow_descendant=False
    )
    return dict(entry)


def bind_agent_identity(
    *,
    repo_root: Path | str,
    workspace: Path | str,
    role: str,
    task_key: str,
    agent_id: str,
    now: datetime,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """trusted start observer が actual identity を1度だけ ``running`` へ束縛する。

    ``workspace`` と ``agent_id`` は transport の trusted observation でなければならない。
    ``collaboration.spawn_agent``経路からは呼ばない。repo supervisorが別processのPID/start tokenを
    先に記録し、同一processのJSONL threadを観測した場合だけ呼ぶ。同一identityの再通知だけを
    冪等に扱い、別identityの上書きは拒否する。
    """

    if not isinstance(agent_id, str) or not worktree_ledger.AGENT_ID_RE.fullmatch(agent_id):
        raise CodexBindingError("CODEX_BINDING_AGENT_ID_INVALID", repr(agent_id))
    root, entry = _one_by_task(repo_root, task_key)
    _assert_entry_shape(entry)
    if entry["agent_type"] != role:
        raise CodexBindingError("CODEX_BINDING_ROLE_MISMATCH", role)
    if entry["status"] == "running":
        if entry.get("agent_id") != agent_id:
            raise CodexBindingError("CODEX_BINDING_AGENT_MISMATCH", agent_id)
        _assert_live_facts(entry, workspace=workspace, runner=runner, allow_descendant=True)
        return dict(entry)
    if entry["status"] != "open":
        raise CodexBindingError("CODEX_BINDING_TASK_REUSED", task_key)
    if now.astimezone(timezone.utc) >= _parse_stamp(entry["expires_at"]):
        raise CodexBindingError("CODEX_BINDING_EXPIRED", task_key)
    _assert_live_facts(entry, workspace=workspace, runner=runner, allow_descendant=False)
    bound_at = _stamp(now)
    bound: dict[str, Any] = {}

    def mutate(document: dict) -> None:
        matches = [
            item for item in document["entries"]
            if item.get("platform") == "codex" and item.get("task_key") == task_key
        ]
        if len(matches) != 1:
            reason = "CODEX_BINDING_MISSING" if not matches else "CODEX_BINDING_DUPLICATE"
            raise CodexBindingError(reason, task_key)
        target = matches[0]
        if target.get("status") == "running":
            if target.get("agent_id") == agent_id:
                bound.update(target)
                return
            raise CodexBindingError("CODEX_BINDING_AGENT_MISMATCH", agent_id)
        if target.get("status") != "open":
            raise CodexBindingError("CODEX_BINDING_TASK_REUSED", task_key)
        target["status"] = "running"
        target["agent_id"] = agent_id
        target["bound_at"] = bound_at
        bound.update(target)

    try:
        worktree_ledger.update_ledger(root, mutate)
    except worktree_ledger.LedgerError as exc:
        raise CodexBindingError(exc.reason, exc.detail) from exc
    return dict(bound)


def verify_command_binding(
    *,
    repo_root: Path | str,
    workspace: Path | str,
    role: str,
    agent_id: str,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """全 tool command 前に actual identity/workspace/role と live Git facts を照合する。"""

    if role not in TARGET_ROLES:
        raise CodexBindingError("CODEX_BINDING_ROLE_INVALID", role)
    if not isinstance(agent_id, str) or not worktree_ledger.AGENT_ID_RE.fullmatch(agent_id):
        raise CodexBindingError("CODEX_BINDING_AGENT_ID_INVALID", repr(agent_id))
    resolved = str(Path(workspace).resolve(strict=True))
    _root, entries = _codex_entries(repo_root)
    matches = [
        item for item in entries
        if item.get("agent_type") == role
        and item.get("workspace") == resolved
        and item.get("status") == "running"
    ]
    if not matches:
        raise CodexBindingError("CODEX_BINDING_ACTIVE_MISSING", f"{role}:{resolved}")
    if len(matches) != 1:
        raise CodexBindingError("CODEX_BINDING_ACTIVE_DUPLICATE", f"{role}:{resolved}")
    entry = matches[0]
    if entry.get("agent_id") != agent_id:
        raise CodexBindingError("CODEX_BINDING_AGENT_MISMATCH", agent_id)
    _assert_live_facts(entry, workspace=workspace, runner=runner, allow_descendant=True)
    return dict(entry)


def _safe_copy_handoff(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise CodexBindingError("CODEX_BINDING_HANDOFF_NOT_REGULAR", str(source))
    for parent in (destination.parent.parent, destination.parent):
        if parent.is_symlink():
            raise CodexBindingError("CODEX_BINDING_HANDOFF_SYMLINK", str(parent))
        parent.mkdir(mode=0o700, exist_ok=True)
    if destination.is_symlink():
        raise CodexBindingError("CODEX_BINDING_HANDOFF_SYMLINK", str(destination))
    if destination.exists():
        if not destination.is_file() or source.read_bytes() != destination.read_bytes():
            raise CodexBindingError("CODEX_BINDING_COLLECT_CONFLICT", str(destination))
        return
    temporary = destination.with_name(destination.name + ".new")
    if temporary.exists() or temporary.is_symlink():
        raise CodexBindingError("CODEX_BINDING_COLLECT_TEMP_EXISTS", str(temporary))
    try:
        with source.open("rb") as src, temporary.open("xb") as dst:
            shutil.copyfileobj(src, dst)
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(temporary, destination)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def collect_binding(
    *, task_key: str, repo_root: Path | str, now: datetime
) -> dict[str, Any]:
    """handoff を main worktree へ回収し entry を ``collected`` にする。"""

    root, entry = _one_by_task(repo_root, task_key)
    _assert_entry_shape(entry)
    if entry["status"] == "collected":
        return dict(entry)
    if entry["status"] not in {"running", "stopped"}:
        raise CodexBindingError("CODEX_BINDING_COLLECT_STATUS_INVALID", entry["status"])
    source = Path(entry["workspace"]) / entry["handoff_path"]
    destination = root / entry["handoff_path"]
    _assert_no_symlink_components(Path(entry["workspace"]), entry["handoff_path"])
    _safe_copy_handoff(source, destination)
    stamp = _stamp(now)
    collected: dict[str, Any] = {}

    def mutate(document: dict) -> None:
        target = next(
            (item for item in document["entries"] if item.get("entry_id") == entry["entry_id"]),
            None,
        )
        if target is None:
            raise CodexBindingError("CODEX_BINDING_MISSING", task_key)
        if target.get("status") not in {"running", "stopped", "collected"}:
            raise CodexBindingError("CODEX_BINDING_COLLECT_STATUS_INVALID", str(target.get("status")))
        target["status"] = "collected"
        target["collected_to"] = entry["handoff_path"]
        target.setdefault("notes", []).append({"at": stamp, "note": "codex handoff collected"})
        collected.update(target)

    try:
        worktree_ledger.update_ledger(root, mutate)
    except worktree_ledger.LedgerError as exc:
        raise CodexBindingError(exc.reason, exc.detail) from exc
    return dict(collected)


def release_binding(
    *, task_key: str, repo_root: Path | str, now: datetime
) -> dict[str, Any]:
    """回収済み ownership を ``released`` にする（worktree 自体は削除しない）。"""

    root, entry = _one_by_task(repo_root, task_key)
    _assert_entry_shape(entry)
    if entry["status"] == "released":
        return dict(entry)
    if entry["status"] != "collected" or not entry.get("collected_to"):
        raise CodexBindingError("CODEX_BINDING_RELEASE_STATUS_INVALID", str(entry["status"]))
    try:
        worktree_ledger.mark(
            root, entry["entry_id"], "released", now=now,
            note="codex workspace ownership released", collected_to=entry["collected_to"],
        )
    except worktree_ledger.LedgerError as exc:
        raise CodexBindingError(exc.reason, exc.detail) from exc
    return _one_by_task(root, task_key)[1]


def _deny(reason: str) -> dict[str, Any]:
    return {
        "decision": "block",
        "reason": "codex-workspace-binding-gate: " + reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }


def run_hook(
    *, stdin: TextIO, stdout: TextIO, stderr: TextIO, cwd: Path | None = None
) -> int:
    """Codex 全 tool PreToolUse adapter。対象外 role は無出力で素通しする。

    現行 payload の ``cwd`` は turn/session cwd であり ``exec_command.workdir`` ではなく、
    actual ``agent_id`` も提供されない。存在しない観測値を推測しないため、
    対象 role は常に fail-close する。
    """

    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            raise CodexBindingError("CODEX_BINDING_PAYLOAD_INVALID")
        role = payload.get("agent_type")
        if role not in TARGET_ROLES:
            return 0
        raise CodexBindingError(
            "CODEX_BINDING_TRANSPORT_UNAVAILABLE",
            "trusted child/effective workspace, actual agent_id, and spawn-success observation are absent",
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        exc = CodexBindingError("CODEX_BINDING_PAYLOAD_INVALID")
        json.dump(_deny(exc.reason), stdout, ensure_ascii=False, separators=(",", ":"))
        stdout.write("\n")
    except CodexBindingError as exc:
        reason = exc.reason + (f" detail={exc.detail}" if exc.detail else "")
        json.dump(_deny(reason), stdout, ensure_ascii=False, separators=(",", ":"))
        stdout.write("\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m issue_start.codex_binding")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--issue", type=int, required=True)
    prepare.add_argument("--round", dest="round_number", type=int, required=True)
    prepare.add_argument("--repository", required=True)
    prepare.add_argument("--workspace", type=Path, required=True)
    prepare.add_argument("--branch", dest="branch_name", required=True)
    prepare.add_argument("--expected-oid", required=True)
    prepare.add_argument("--handoff", dest="handoff_path", required=True)
    prepare.add_argument("--role", choices=sorted(TARGET_ROLES), required=True)
    prepare.add_argument("--task-key", required=True)
    prepare.add_argument(
        "--protected-path", dest="protected_paths", action="append", default=[],
        metavar="PATH=BASE_SHA256",
    )
    prepare.add_argument("--ttl-seconds", type=int, default=DEFAULT_TTL_SECONDS)
    for name in ("collect", "release"):
        action = sub.add_parser(name)
        action.add_argument("--task-key", required=True)
        action.add_argument("--repo-root", type=Path, default=Path.cwd())
    sub.add_parser("hook")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.command == "hook":
        return run_hook(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
    now = datetime.now(timezone.utc)
    try:
        if args.command == "prepare":
            result = prepare_binding(
                issue=args.issue, round_number=args.round_number,
                repository=args.repository, workspace=args.workspace,
                branch_name=args.branch_name, expected_oid=args.expected_oid,
                handoff_path=args.handoff_path, role=args.role, task_key=args.task_key,
                protected_paths=args.protected_paths,
                ttl_seconds=args.ttl_seconds, now=now,
            )
        elif args.command == "collect":
            result = collect_binding(task_key=args.task_key, repo_root=args.repo_root, now=now)
        else:
            result = release_binding(task_key=args.task_key, repo_root=args.repo_root, now=now)
    except CodexBindingError as exc:
        json.dump({"result": "DENY", "reason": exc.reason, "detail": exc.detail}, sys.stdout,
                  ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
        return 4
    json.dump({"result": "OK", "binding": result}, sys.stdout,
              ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
