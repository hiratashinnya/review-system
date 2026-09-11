"""Host control-plane issuer for Codex supervisor change plans.

This command consumes already captured, structured source files.  It does not
contact GitHub, create a worktree, launch a model, or prove the identity of the
approving owner.  ``approved_by`` is an auditable operational record.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import secrets
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence, TextIO

from . import codex_launch_intent, worktree_ledger
from .codex_supervisor_workspace import GitFacts, inspect_git_facts, validate_launch_identity


class LaunchControlError(RuntimeError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class IssueRequest:
    issue: int
    role: str
    change_plan_id: str
    workspace: Path
    issue_snapshot_file: Path
    approved_by: str
    fixer_round: int | None = None
    karte_snapshot_file: Path | None = None
    protected_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class _DirectoryHandle:
    tree: "_ControlTree"
    index: int
    name: str

    @property
    def fd(self) -> int:
        return self.tree.fds[self.index]


@dataclass
class _ControlTree:
    """Verified directory identities retained for the full publication transaction."""
    fds: list[int]
    links: list[tuple[int, str] | None]
    sources_index: int
    plans_index: int

    def assert_attached(self) -> None:
        for index, link in enumerate(self.links):
            if link is None:
                continue
            parent_index, name = link
            try:
                path_info = os.stat(name, dir_fd=self.fds[parent_index],
                                    follow_symlinks=False)
                fd_info = os.fstat(self.fds[index])
            except OSError as exc:
                raise LaunchControlError("CONTROL_ROOT_CHANGED", type(exc).__name__) from exc
            if (not stat.S_ISDIR(path_info.st_mode)
                    or (path_info.st_dev, path_info.st_ino)
                    != (fd_info.st_dev, fd_info.st_ino)):
                _fail("CONTROL_ROOT_CHANGED", name)

    @property
    def sources(self) -> _DirectoryHandle:
        return _DirectoryHandle(self, self.sources_index, "sources")

    @property
    def plans(self) -> _DirectoryHandle:
        return _DirectoryHandle(self, self.plans_index, "change-plans")

    def close(self) -> None:
        for fd in reversed(self.fds):
            try:
                os.close(fd)
            except OSError:
                pass
        self.fds.clear()

    def __enter__(self) -> "_ControlTree":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


_CONTROL_REL = PurePosixPath("tmp/_codex_control")
_SOURCES_REL = _CONTROL_REL / "sources"
_PLANS_REL = _CONTROL_REL / "change-plans"
_MANIFEST_REL = PurePosixPath("issue_start/managed-entrypoints-v2.json")
_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_CHANGE_PLAN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_FINDING_ID = re.compile(r"^F-([1-9][0-9]*)-([0-9]{2,})$")
_MAX_SOURCE = 2 * 1024 * 1024
_PROTECTED_ROOTS = (".codex/", ".agents/", ".ai/agents/")


def _fail(reason: str, detail: object = "") -> None:
    raise LaunchControlError(reason, str(detail))


def _stamp(now: datetime) -> str:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        _fail("CONTROL_TIME_INVALID")
    return now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _capture(value: object, *, kind: str, issued_at: str, reason: str) -> Mapping[str, str]:
    try:
        capture = codex_launch_intent._capture_record(value, kind=kind, reason=reason)
        captured_time = datetime.strptime(capture["captured_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
        issuance_time = datetime.strptime(issued_at, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
    except codex_launch_intent.LaunchIntentError as exc:
        raise LaunchControlError(reason, exc.detail or exc.reason) from exc
    if captured_time > issuance_time:
        _fail(reason, "capture is later than approval record")
    return capture


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _validate_request(request: IssueRequest) -> int:
    if not isinstance(request.issue, int) or isinstance(request.issue, bool) or request.issue < 1:
        _fail("CONTROL_ISSUE_INVALID")
    if request.role not in {"issue-implementer", "issue-fixer"}:
        _fail("CONTROL_ROLE_INVALID")
    if not isinstance(request.change_plan_id, str) or not _CHANGE_PLAN_ID.fullmatch(request.change_plan_id):
        _fail("CONTROL_CHANGE_PLAN_ID_INVALID")
    if not isinstance(request.approved_by, str) or not _LOGIN.fullmatch(request.approved_by):
        _fail("CONTROL_APPROVER_INVALID")
    for value, reason in ((request.workspace, "CONTROL_WORKSPACE_INVALID"),
                          (request.issue_snapshot_file, "CONTROL_ISSUE_FILE_INVALID")):
        if not isinstance(value, Path) or not value.is_absolute():
            _fail(reason, value)
    if request.role == "issue-implementer":
        if request.fixer_round is not None or request.karte_snapshot_file is not None:
            _fail("CONTROL_FIXER_INPUT_FORBIDDEN")
        return 1
    if (not isinstance(request.fixer_round, int) or isinstance(request.fixer_round, bool)
            or request.fixer_round < 1):
        _fail("CONTROL_FIXER_ROUND_INVALID")
    if not isinstance(request.karte_snapshot_file, Path) or not request.karte_snapshot_file.is_absolute():
        _fail("CONTROL_KARTE_FILE_INVALID")
    return request.fixer_round


def _read_absolute_same_fd(path: Path, *, reason: str) -> bytes:
    """Read a host input through one verified FD and reject mutable aliases."""
    if not path.is_absolute():
        _fail(reason, "not absolute")
    opened: list[int] = []
    try:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        opened.append(fd)
        for part in path.parts[1:-1]:
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                         dir_fd=fd)
            opened.append(fd)
            codex_launch_intent._check_directory(os.fstat(fd), private=False, reason=reason)
        leaf = os.open(path.parts[-1], os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
        opened.append(leaf)
        info = os.fstat(leaf)
        mode = stat.S_IMODE(info.st_mode)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or mode != 0o600):
            _fail(reason, "source must be current-user regular 0600 with one link")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(leaf, min(65536, _MAX_SOURCE + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > _MAX_SOURCE:
                _fail(reason, "source too large")
            chunks.append(chunk)
        return b"".join(chunks)
    except LaunchControlError:
        raise
    except codex_launch_intent.LaunchIntentError as exc:
        raise LaunchControlError(reason, exc.detail or exc.reason) from exc
    except OSError as exc:
        raise LaunchControlError(reason, type(exc).__name__) from exc
    finally:
        for handle in reversed(opened):
            try:
                os.close(handle)
            except OSError:
                pass


def _json_object(raw: bytes, *, reason: str) -> Mapping[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LaunchControlError(reason, "invalid JSON") from exc
    if not isinstance(value, Mapping):
        _fail(reason, "not an object")
    return value


def _validate_issue(raw: bytes, *, facts: GitFacts, request: IssueRequest,
                    issued_at: str) -> Mapping[str, str]:
    descriptor = {"sha256": _sha(raw)}
    launch_request = codex_launch_intent.LaunchRequest(
        request.issue, request.role, request.change_plan_id, request.fixer_round,
    )
    try:
        _rendered, envelope = codex_launch_intent._issue_snapshot(
            raw.decode("utf-8"), descriptor=descriptor, request=launch_request,
            repository=facts.repository,
        )
    except (UnicodeDecodeError, codex_launch_intent.LaunchIntentError) as exc:
        raise LaunchControlError("CONTROL_ISSUE_SOURCE_INVALID", str(exc)) from exc
    return _capture(envelope["capture"], kind="ISSUE", issued_at=issued_at,
                    reason="CONTROL_ISSUE_SOURCE_INVALID")


def _validate_karte(raw: bytes, *, request: IssueRequest, round_number: int,
                    issued_at: str) -> tuple[tuple[str, ...], Mapping[str, str]]:
    value = _json_object(raw, reason="CONTROL_KARTE_SOURCE_INVALID")
    if set(value) != {"schema_version", "issue", "round", "open_findings", "capture"}:
        _fail("CONTROL_KARTE_SOURCE_INVALID", "unexpected fields")
    findings = value.get("open_findings")
    if (value.get("schema_version") != "codex-karte-snapshot/2"
            or value.get("issue") != request.issue or value.get("round") != round_number
            or not isinstance(findings, list) or not findings):
        _fail("CONTROL_KARTE_SOURCE_INVALID", "issue/round semantics")
    result: list[str] = []
    for item in findings:
        if not isinstance(item, Mapping) or set(item) != {"id", "status", "summary"}:
            _fail("CONTROL_KARTE_SOURCE_INVALID", "finding shape")
        finding_id = item.get("id")
        match = _FINDING_ID.fullmatch(finding_id) if isinstance(finding_id, str) else None
        if (match is None or int(match.group(1)) != request.issue or item.get("status") != "open"
                or not isinstance(item.get("summary"), str) or not item["summary"].strip()):
            _fail("CONTROL_KARTE_SOURCE_INVALID", "finding semantics")
        result.append(finding_id)
    if len(result) != len(set(result)):
        _fail("CONTROL_KARTE_SOURCE_INVALID", "duplicate finding")
    capture = _capture(value["capture"], kind="KARTE", issued_at=issued_at,
                       reason="CONTROL_KARTE_SOURCE_INVALID")
    return tuple(result), capture


def _manifest(main: Path) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    try:
        value = codex_launch_intent._secure_json(
            main, _MANIFEST_REL, reason="CONTROL_MANIFEST_INVALID", leaf_private=False,
        )
    except codex_launch_intent.LaunchIntentError as exc:
        raise LaunchControlError("CONTROL_MANIFEST_INVALID", str(exc)) from exc
    launch = value.get("codex_supervisor_launch")
    try:
        validated, _bwrap, _codex, _evidence = codex_launch_intent._validate_manifest(value)
    except codex_launch_intent.LaunchIntentError as exc:
        raise LaunchControlError("CONTROL_MANIFEST_INVALID", str(exc)) from exc
    issuer = validated.get("issuer_contract")
    expected = {
        "schema_version": "codex-change-plan-issuance/1",
        "command": "python3 -m issue_start.codex_launch_control issue",
        "sources_root": str(_SOURCES_REL),
    }
    if issuer != expected:
        _fail("CONTROL_MANIFEST_INVALID", "issuer contract")
    return value, launch


def _role_values(launch: Mapping[str, Any], request: IssueRequest,
                 round_number: int) -> tuple[str, str]:
    role = launch["roles"][request.role]
    values = {"issue": request.issue, "round": round_number}
    try:
        task = role["task_key_template"].format_map(values)
        handoff = role["handoff_template"].format_map(values)
    except (KeyError, ValueError) as exc:
        raise LaunchControlError("CONTROL_MANIFEST_INVALID", "template") from exc
    return task, handoff


def _protected(main: Path, paths: Sequence[str]) -> list[dict[str, str]]:
    if len(paths) != len(set(paths)):
        _fail("CONTROL_PROTECTED_PATH_INVALID", "duplicate")
    result: list[dict[str, str]] = []
    for value in paths:
        if not isinstance(value, str):
            _fail("CONTROL_PROTECTED_PATH_INVALID")
        parsed = PurePosixPath(value)
        if (parsed.is_absolute() or str(parsed) != value
                or any(part in {"", ".", ".."} for part in parsed.parts)
                or not value.startswith(_PROTECTED_ROOTS)):
            _fail("CONTROL_PROTECTED_PATH_INVALID", value)
        try:
            raw = codex_launch_intent._read_same_fd(
                main, parsed, reason="CONTROL_PROTECTED_PATH_INVALID", leaf_private=False,
            )
        except codex_launch_intent.LaunchIntentError as exc:
            raise LaunchControlError("CONTROL_PROTECTED_PATH_INVALID", str(exc)) from exc
        result.append({"path": value, "base_sha256": _sha(raw)})
    return sorted(result, key=lambda item: item["path"])


def _open_child(parent_fd: int, name: str, *, private: bool,
                create_mode: int | None) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        return os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        if create_mode is None:
            raise
        try:
            os.mkdir(name, create_mode, dir_fd=parent_fd)
        except FileExistsError:
            pass
        return os.open(name, flags, dir_fd=parent_fd)


def _open_control_tree(main: Path) -> _ControlTree:
    """Open and retain the trusted root-to-publication directory identities."""
    if not main.is_absolute() or any(part in {"", ".", ".."} for part in main.parts[1:]):
        _fail("CONTROL_ROOT_INVALID", "main path")
    fds: list[int] = []
    links: list[tuple[int, str] | None] = []
    try:
        root_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        fds.append(root_fd)
        links.append(None)
        codex_launch_intent._check_directory(
            os.fstat(root_fd), private=False, reason="CONTROL_ROOT_INVALID")
        current_index = 0
        for part in main.parts[1:]:
            child = _open_child(fds[current_index], part, private=False, create_mode=None)
            codex_launch_intent._check_directory(
                os.fstat(child), private=False, reason="CONTROL_ROOT_INVALID")
            fds.append(child)
            links.append((current_index, part))
            current_index = len(fds) - 1
        for name, private, create_mode in (
                ("tmp", False, 0o755), ("_codex_control", True, 0o700),
                ("sources", True, 0o700)):
            child = _open_child(fds[current_index], name, private=private,
                                create_mode=create_mode)
            codex_launch_intent._check_directory(
                os.fstat(child), private=private, reason="CONTROL_ROOT_INVALID")
            fds.append(child)
            links.append((current_index, name))
            current_index = len(fds) - 1
        sources_index = current_index
        control_index = links[sources_index][0]
        assert control_index is not None
        plans = _open_child(fds[control_index], "change-plans", private=True,
                            create_mode=0o700)
        codex_launch_intent._check_directory(
            os.fstat(plans), private=True, reason="CONTROL_ROOT_INVALID")
        fds.append(plans)
        links.append((control_index, "change-plans"))
        tree = _ControlTree(fds, links, sources_index, len(fds) - 1)
        tree.assert_attached()
        return tree
    except LaunchControlError:
        for fd in reversed(fds):
            try:
                os.close(fd)
            except OSError:
                pass
        raise
    except codex_launch_intent.LaunchIntentError as exc:
        for fd in reversed(fds):
            try:
                os.close(fd)
            except OSError:
                pass
        raise LaunchControlError("CONTROL_ROOT_INVALID", exc.detail or exc.reason) from exc
    except OSError as exc:
        for fd in reversed(fds):
            try:
                os.close(fd)
            except OSError:
                pass
        raise LaunchControlError("CONTROL_ROOT_INVALID", type(exc).__name__) from exc


def _read_published(directory: _DirectoryHandle, name: str, *, reason: str) -> bytes | None:
    try:
        fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                     dir_fd=directory.fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise LaunchControlError(reason, type(exc).__name__) from exc
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
            _fail(reason, "published leaf owner/type/link/mode")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(fd, min(65536, _MAX_SOURCE + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > _MAX_SOURCE:
                _fail(reason, "published leaf too large")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _write_once_or_exact(directory: _DirectoryHandle, name: str, raw: bytes,
                         *, reason: str) -> None:
    """Publish within one retained dirfd, atomically and without overwriting."""
    if not isinstance(name, str) or not name or "/" in name or name in {".", ".."}:
        _fail(reason, "invalid leaf name")
    directory.tree.assert_attached()
    existing = _read_published(directory, name, reason=reason)
    if existing is not None:
        if existing != raw:
            _fail(reason, "existing content differs")
        directory.tree.assert_attached()
        try:
            os.fsync(directory.fd)
        except OSError as exc:
            raise LaunchControlError(reason, type(exc).__name__) from exc
        directory.tree.assert_attached()
        return
    temp = f".{name}.new.{os.getpid()}.{secrets.token_hex(8)}"
    temp_created = False
    target_created = False
    published_identity: tuple[int, int] | None = None
    fd: int | None = None
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=directory.fd)
        temp_created = True
        offset = 0
        while offset < len(raw):
            offset += os.write(fd, raw[offset:])
        os.fsync(fd)
        info = os.fstat(fd)
        if (info.st_uid != os.getuid() or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o600):
            _fail(reason, "temporary leaf owner/link/mode")
        published_identity = (info.st_dev, info.st_ino)
        directory.tree.assert_attached()
        os.link(temp, name, src_dir_fd=directory.fd, dst_dir_fd=directory.fd,
                follow_symlinks=False)
        target_created = True
        target_info = os.stat(name, dir_fd=directory.fd, follow_symlinks=False)
        if ((target_info.st_dev, target_info.st_ino) != published_identity
                or not stat.S_ISREG(target_info.st_mode)):
            _fail(reason, "published leaf identity")
        directory.tree.assert_attached()
        os.unlink(temp, dir_fd=directory.fd)
        temp_created = False
        if os.fstat(fd).st_nlink != 1:
            _fail(reason, "published leaf link count")
        os.fsync(directory.fd)
        directory.tree.assert_attached()
    except LaunchControlError:
        raise
    except OSError as exc:
        detail = "leaf collision" if exc.errno == errno.EEXIST else type(exc).__name__
        raise LaunchControlError(reason, detail) from exc
    finally:
        if temp_created:
            try:
                os.unlink(temp, dir_fd=directory.fd)
            except OSError:
                pass
        # A path-identity failure after publication must not leave an artifact in
        # a directory that was renamed away from the canonical tree.
        if target_created:
            try:
                directory.tree.assert_attached()
            except LaunchControlError:
                try:
                    target_info = os.stat(name, dir_fd=directory.fd, follow_symlinks=False)
                    if (target_info.st_dev, target_info.st_ino) == published_identity:
                        os.unlink(name, dir_fd=directory.fd)
                        os.fsync(directory.fd)
                except OSError:
                    pass
        if fd is not None:
            os.close(fd)


def issue(request: IssueRequest, *, now: datetime) -> Mapping[str, Any]:
    """Issue an approved plan.  Retrying an identical request repairs partial state."""
    round_number = _validate_request(request)
    recorded_at = _stamp(now)
    try:
        facts = inspect_git_facts(request.workspace)
    except Exception as exc:
        raise LaunchControlError("CONTROL_GIT_FACTS_INVALID", getattr(exc, "reason", str(exc))) from exc
    main = Path(facts.main_root)
    manifest, launch = _manifest(main)
    task_key, handoff = _role_values(launch, request, round_number)
    issue_raw = _read_absolute_same_fd(request.issue_snapshot_file,
                                       reason="CONTROL_ISSUE_FILE_INVALID")
    issue_capture = _validate_issue(
        issue_raw, facts=facts, request=request, issued_at=recorded_at)
    karte_raw: bytes | None = None
    karte_capture: Mapping[str, str] | None = None
    findings: tuple[str, ...] = ()
    if request.role == "issue-fixer":
        assert request.karte_snapshot_file is not None
        karte_raw = _read_absolute_same_fd(request.karte_snapshot_file,
                                           reason="CONTROL_KARTE_FILE_INVALID")
        findings, karte_capture = _validate_karte(
            karte_raw, request=request, round_number=round_number, issued_at=recorded_at)
    protected = _protected(main, request.protected_paths)
    protected_args = tuple(f"{item['path']}={item['base_sha256']}" for item in protected)
    try:
        validate_launch_identity(
            issue=request.issue, round_number=round_number, repository=facts.repository,
            role=request.role, task_key=task_key, handoff_path=handoff,
            branch_name=facts.branch_name, expected_oid=facts.head_oid,
            protected_paths=protected_args,
        )
    except Exception as exc:
        raise LaunchControlError("CONTROL_DERIVED_IDENTITY_INVALID",
                                 getattr(exc, "reason", str(exc))) from exc

    issue_name = f"{request.change_plan_id}-issue.json"
    karte_name = f"{request.change_plan_id}-karte.json"
    identity = {
        "issue": request.issue, "role": request.role, "round": request.fixer_round,
        "change_plan_id": request.change_plan_id, "repository": facts.repository,
        "workspace": facts.workspace, "worktree_path": facts.worktree_path,
        "branch_name": facts.branch_name, "initial_oid": facts.head_oid,
        "task_key": task_key, "handoff_path": handoff, "protected_plan": protected,
        "issue_source": {"path": str(_SOURCES_REL / issue_name), "sha256": _sha(issue_raw)},
        "karte_source": None if karte_raw is None else {
            "path": str(_SOURCES_REL / karte_name), "sha256": _sha(karte_raw)},
        "finding_ids": list(findings), "approved_by": request.approved_by,
    }
    issuance_digest = _sha(_canonical_bytes(identity))
    plan: dict[str, Any]
    with _open_control_tree(main) as control_tree, \
            worktree_ledger.acquire_ledger_lease(main) as lease:
        sources_dir = control_tree.sources
        plans_dir = control_tree.plans
        control_tree.assert_attached()
        try:
            locked_facts = inspect_git_facts(request.workspace)
        except Exception as exc:
            raise LaunchControlError("CONTROL_GIT_FACTS_INVALID",
                                     getattr(exc, "reason", str(exc))) from exc
        if locked_facts != facts:
            _fail("CONTROL_GIT_FACTS_CHANGED")
        if _protected(main, request.protected_paths) != protected:
            _fail("CONTROL_PROTECTED_PATH_CHANGED")
        entries = lease.document["entries"]
        requested_identity = {
            "platform": "codex-supervisor", "issue": request.issue,
            "agent_type": request.role, "round": request.fixer_round,
            "repository": facts.repository, "workspace": facts.workspace,
            "worktree_path": facts.worktree_path, "branch_name": facts.branch_name,
            "initial_oid": facts.head_oid, "task_key": task_key,
            "handoff_path": handoff, "protected_plan": protected,
            "change_plan_id": request.change_plan_id,
            "issuance_spec_digest": issuance_digest, "approved_by": request.approved_by,
        }

        def collides(item: Mapping[str, Any]) -> bool:
            if item.get("platform") != "codex-supervisor":
                return False
            if item.get("change_plan_id") == request.change_plan_id:
                return True
            if item.get("status") in worktree_ledger.TERMINAL_STATUSES:
                return False
            same_issue_role_round = (
                item.get("issue") == request.issue
                and item.get("agent_type") == request.role
                and item.get("round") == request.fixer_round
            )
            return (same_issue_role_round or item.get("task_key") == task_key
                    or item.get("workspace") == facts.workspace)

        candidates = [item for item in entries if collides(item)]
        exact = [item for item in candidates
                 if item.get("change_plan_id") == request.change_plan_id
                 and item.get("issuance_spec_digest") == issuance_digest]
        if candidates and (len(candidates) != 1 or len(exact) != 1):
            _fail("CONTROL_LEDGER_COLLISION", "ambiguous or conflicting canonical entry")
        if exact:
            entry = exact[0]
            if any(entry.get(key) != value for key, value in requested_identity.items()):
                _fail("CONTROL_LEDGER_COLLISION", "canonical entry fields changed")
            if entry.get("issuance_status") not in {"pending", "complete"}:
                _fail("CONTROL_LEDGER_COLLISION", "invalid issuance status")
            recorded_at = entry.get("approval_recorded_at")
            if not isinstance(recorded_at, str):
                _fail("CONTROL_LEDGER_COLLISION", "approval timestamp missing")
        else:
            entry = {
                "entry_id": worktree_ledger._new_entry_id(
                    {item.get("entry_id") for item in entries}),
                **requested_identity, "issuance_status": "pending",
                "approval_recorded_at": recorded_at,
                "status": "open", "agent_id": None, "supervisor_attempts": [],
                "publish_attempts": [], "notes": [],
            }
            entries.append(entry)
            lease.commit()
        issue_descriptor = {
            "path": str(_SOURCES_REL / issue_name), "sha256": _sha(issue_raw),
            "provenance": {"source_type": "github-issue-snapshot", **issue_capture},
        }
        karte_descriptor = None if karte_raw is None else {
            "path": str(_SOURCES_REL / karte_name), "sha256": _sha(karte_raw),
            "provenance": {"source_type": "finding-karte-snapshot", **karte_capture},
        }
        plan = {
            "schema_version": launch["change_plan_schema"],
            "change_plan_id": request.change_plan_id,
            "owner_approval": {"status": "approved", "actor": request.approved_by,
                               "recorded_at": recorded_at},
            "issue": request.issue, "role": request.role,
            "fixer_round": request.fixer_round, "ledger_entry_id": entry["entry_id"],
            "issue_source": issue_descriptor, "finding_ids": list(findings),
            "karte_source": karte_descriptor, "protected_plan": protected,
        }
        _write_once_or_exact(sources_dir, issue_name, issue_raw,
                             reason="CONTROL_ISSUE_PUBLICATION_INVALID")
        if karte_raw is not None:
            _write_once_or_exact(sources_dir, karte_name, karte_raw,
                                 reason="CONTROL_KARTE_PUBLICATION_INVALID")
        entry["issuance_status"] = "complete"
        lease.commit()
        _write_once_or_exact(plans_dir, f"{request.change_plan_id}.json",
                             _canonical_bytes(plan), reason="CONTROL_PLAN_PUBLICATION_INVALID")
    return plan


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m issue_start.codex_launch_control")
    sub = parser.add_subparsers(dest="command", required=True)
    issue_parser = sub.add_parser("issue")
    issue_parser.add_argument("--issue", required=True, type=int)
    issue_parser.add_argument("--role", required=True)
    issue_parser.add_argument("--change-plan-id", required=True)
    issue_parser.add_argument("--workspace", required=True, type=Path)
    issue_parser.add_argument("--issue-snapshot-file", required=True, type=Path)
    issue_parser.add_argument("--approved-by", required=True)
    issue_parser.add_argument("--fixer-round", type=int)
    issue_parser.add_argument("--karte-snapshot-file", type=Path)
    issue_parser.add_argument("--protected-path", action="append", default=[])
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO = sys.stdout,
         stderr: TextIO = sys.stderr) -> int:
    args = _parser().parse_args(argv)
    try:
        plan = issue(IssueRequest(
            issue=args.issue, role=args.role, change_plan_id=args.change_plan_id,
            workspace=args.workspace, issue_snapshot_file=args.issue_snapshot_file,
            approved_by=args.approved_by, fixer_round=args.fixer_round,
            karte_snapshot_file=args.karte_snapshot_file,
            protected_paths=tuple(args.protected_path),
        ), now=datetime.now(timezone.utc))
    except (LaunchControlError, worktree_ledger.LedgerError) as exc:
        print(getattr(exc, "reason", "CONTROL_ERROR"), file=stderr)
        return 2
    json.dump({"status": "issued", "change_plan_id": plan["change_plan_id"],
               "ledger_entry_id": plan["ledger_entry_id"]}, stdout, sort_keys=True)
    stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
