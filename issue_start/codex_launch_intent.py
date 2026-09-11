"""Trusted host launch-intent derivation for the Codex issue supervisor.

Only :class:`LaunchRequest` is supplied by the parent AI.  Every execution fact is
read from host-owned canonical state and revalidated; an inner Codex process is
never an authority for this state.  ``owner_approval`` is an operational record,
not a cryptographic proof of a person's identity.
"""

from __future__ import annotations

import argparse
import grp
import hashlib
import json
import os
import pwd
import re
import shutil
import shlex
import stat
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence, TextIO

from . import worktree_ledger
from .codex_supervisor_workspace import GitFacts, inspect_git_facts


class LaunchIntentError(RuntimeError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class LaunchRequest:
    issue: int
    role: str
    change_plan_id: str
    fixer_round: int | None = None


@dataclass(frozen=True)
class LaunchIntent:
    schema_version: str
    issue: int
    role: str
    round_number: int
    change_plan_id: str
    repository: str
    workspace: str
    branch_name: str
    expected_oid: str
    task_key: str
    handoff_path: str
    model: str
    reasoning_effort: str
    bwrap_executable: str
    codex_executable: str
    executable_evidence: Mapping[str, Mapping[str, Any]]
    permission_profile: str
    runtime_root: str
    protected_paths: tuple[str, ...]
    finding_ids: tuple[str, ...]
    source_provenance: Mapping[str, Mapping[str, Any]]
    prompt: str
    ledger_entry_id: str = ""
    plan_digest: str = ""
    manifest_digest: str = ""
    canonical_entry_digest: str = ""
    role_contract_digest: str = ""


_ROLES = frozenset({"issue-implementer", "issue-fixer"})
_CHANGE_PLAN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_ENTRY_ID = re.compile(r"^wl-[0-9a-f]{12}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FINDING_ID = re.compile(r"^F-([1-9][0-9]*)-([0-9]{2,})$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_OID = re.compile(r"^[0-9a-f]{40}$")
_MAX_JSON = 2 * 1024 * 1024
_CONTROL_ROOT = PurePosixPath("tmp/_codex_control")
_PLAN_ROOT = _CONTROL_ROOT / "change-plans"
_EXPECTED_ROLE_CONFIG = {
    "issue-implementer": {
        "model": "gpt-5.6-sol", "reasoning_effort": "xhigh",
        "task_key_template": "issue_{issue}",
        "handoff_template": "tmp/_handoff/issue-implementer--issue-{issue}.yaml",
        "prompt_template": (
            "Implement Issue #{issue} under owner-approved change plan {change_plan_id}. "
            "Verified Issue and Acceptance Criteria snapshot follows:\n\n{issue_snapshot}"
        ),
    },
    "issue-fixer": {
        "model": "gpt-5.6-sol", "reasoning_effort": "xhigh",
        "task_key_template": "issue_{issue}_fix_r{round}",
        "handoff_template": "tmp/_handoff/issue-fixer--issue-{issue}-r{round}.yaml",
        "prompt_template": (
            "Fix findings {finding_ids} for Issue #{issue} under owner-approved change plan "
            "{change_plan_id}. Verified Issue and Acceptance Criteria snapshot follows:\n\n"
            "{issue_snapshot}\n\nVerified finding karte ({karte_path}) follows:\n\n"
            "{karte_snapshot}"
        ),
    },
}


def _fail(reason: str, detail: object = "") -> None:
    raise LaunchIntentError(reason, str(detail))


def _validate_request(request: LaunchRequest) -> int:
    if not isinstance(request.issue, int) or isinstance(request.issue, bool) or request.issue < 1:
        _fail("ISSUE_INVALID")
    if request.role not in _ROLES:
        _fail("ROLE_INVALID")
    if not isinstance(request.change_plan_id, str) or not _CHANGE_PLAN_ID.fullmatch(request.change_plan_id):
        _fail("CHANGE_PLAN_ID_INVALID")
    if request.role == "issue-implementer":
        if request.fixer_round is not None:
            _fail("FIXER_ROUND_FORBIDDEN")
        return 1
    if (not isinstance(request.fixer_round, int) or isinstance(request.fixer_round, bool)
            or request.fixer_round < 1):
        _fail("FIXER_ROUND_INVALID")
    return request.fixer_round


def _exact_keys(value: object, expected: set[str], reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        _fail(reason, "unexpected object fields")
    return value


def _safe_relative(value: object, *, root: PurePosixPath | None = None,
                   reason: str) -> PurePosixPath:
    if not isinstance(value, str):
        _fail(reason)
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(p in {"", ".", ".."} for p in path.parts):
        _fail(reason, value)
    if root is not None and tuple(path.parts[:len(root.parts)]) != root.parts:
        _fail(reason, value)
    return path


def _group_is_exclusive_to_current_uid(gid: int) -> bool:
    """Return whether NSS shows exactly the executing uid as a group principal."""
    try:
        current_uid = os.getuid()
        current = pwd.getpwuid(current_uid)
        group = grp.getgrgid(gid)
        accounts = pwd.getpwall()
        explicit_uids = {pwd.getpwnam(name).pw_uid for name in group.gr_mem}
    except (KeyError, OSError, RuntimeError):
        return False
    primary_uids = {account.pw_uid for account in accounts if account.pw_gid == gid}
    principals = primary_uids | explicit_uids
    current_is_member = current.pw_gid == gid or current.pw_name in group.gr_mem
    return current_is_member and principals == {current_uid}


def _trusted_host_owner_uids() -> set[int]:
    """Include the uid through which a user namespace exposes host root."""
    try:
        namespace_root_uid = os.stat("/").st_uid
    except OSError:
        namespace_root_uid = 0
    return {0, os.getuid(), namespace_root_uid}


def _check_directory(st: os.stat_result, *, private: bool, reason: str) -> None:
    sticky_shared_ancestor = (not private and bool(st.st_mode & stat.S_ISVTX)
                              and stat.S_IMODE(st.st_mode) == 0o1777)
    if not stat.S_ISDIR(st.st_mode) or (st.st_uid not in _trusted_host_owner_uids()
                                       and not sticky_shared_ancestor):
        _fail(reason, "directory owner/type")
    if st.st_mode & 0o002 and not sticky_shared_ancestor:
        _fail(reason, "unsafe writable directory")
    if (st.st_mode & 0o020 and not sticky_shared_ancestor
            and (st.st_uid != os.getuid()
                 or not _group_is_exclusive_to_current_uid(st.st_gid))):
        _fail(reason, "unsafe group-writable directory")
    if private and (st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != 0o700):
        _fail(reason, "private directory must be current-user 0700")


def _check_resolved_path_ancestors(path: Path, *, reason: str) -> None:
    """Check every directory of an already-resolved absolute executable path."""
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    opened = [fd]
    try:
        for part in path.parts[1:-1]:
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                         dir_fd=fd)
            opened.append(fd)
            _check_directory(os.fstat(fd), private=False, reason=reason)
    except LaunchIntentError:
        raise
    except OSError as exc:
        _fail(reason, type(exc).__name__)
    finally:
        for handle in reversed(opened):
            try:
                os.close(handle)
            except OSError:
                pass


def _read_same_fd(root: Path, relative: PurePosixPath, *, reason: str,
                  private_from: PurePosixPath | None = None,
                  leaf_private: bool = True) -> bytes:
    """Traverse with openat/O_NOFOLLOW and read the already-fstat'ed leaf FD."""
    try:
        absolute = root.resolve(strict=True)
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        opened = [fd]
        components = list(absolute.parts[1:]) + list(relative.parts)
        private_at = len(absolute.parts[1:]) + (
            len(private_from.parts) if private_from is not None else len(relative.parts) + 1
        )
        for index, part in enumerate(components[:-1]):
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                            dir_fd=fd)
            opened.append(child)
            fd = child
            _check_directory(os.fstat(fd), private=index + 1 >= private_at, reason=reason)
        leaf = os.open(components[-1], os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
        opened.append(leaf)
        info = os.fstat(leaf)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            _fail(reason, "leaf owner/type/link count")
        mode = stat.S_IMODE(info.st_mode)
        unsafe_group_write = bool(mode & 0o020) and (
            leaf_private or info.st_uid != os.getuid()
            or not _group_is_exclusive_to_current_uid(info.st_gid)
        )
        if (mode & 0o002 or unsafe_group_write
                or (leaf_private and mode != 0o600)):
            _fail(reason, "leaf mode")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(leaf, min(65536, _MAX_JSON + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > _MAX_JSON:
                _fail(reason, "file too large")
        return b"".join(chunks)
    except LaunchIntentError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        _fail(reason, type(exc).__name__)
    finally:
        for handle in reversed(locals().get("opened", [])):
            try:
                os.close(handle)
            except OSError:
                pass


def _secure_json(root: Path, relative: PurePosixPath, *, reason: str,
                 private_from: PurePosixPath | None = None,
                 leaf_private: bool = True) -> Mapping[str, Any]:
    raw = _read_same_fd(root, relative, reason=reason, private_from=private_from,
                        leaf_private=leaf_private)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LaunchIntentError(reason, "invalid JSON") from exc
    if not isinstance(value, Mapping):
        _fail(reason, "not an object")
    return value


def _secure_text(root: Path, relative: PurePosixPath, *, reason: str,
                 private_from: PurePosixPath) -> str:
    raw = _read_same_fd(root, relative, reason=reason, private_from=private_from)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LaunchIntentError(reason, "invalid UTF-8") from exc


def _sha(raw: str | bytes) -> str:
    value = raw.encode("utf-8") if isinstance(raw, str) else raw
    return hashlib.sha256(value).hexdigest()


def _canonical_digest(value: object) -> str:
    return _sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")))


def intent_digest(intent: LaunchIntent) -> str:
    """Return the immutable digest persisted with a launch reservation."""

    return _canonical_digest(asdict(intent))


def _role_contract_digest(main_root: Path, workspace: Path, role: str) -> str:
    """Bind launch authority to the main role contract and its worktree copy."""

    digests: list[str] = []
    for root in (main_root, workspace):
        current: list[bytes] = []
        for relative in (f".codex/agents/{role}.toml", f".ai/agents/{role}.md"):
            current.append(_read_same_fd(
                root, PurePosixPath(relative), reason="ROLE_CONTRACT_INVALID",
                leaf_private=False,
            ))
        digests.append(hashlib.sha256(
            role.encode("utf-8") + b"\0" + current[0] + b"\0" + current[1]
        ).hexdigest())
    if digests[0] != digests[1]:
        _fail("ROLE_CONTRACT_DIGEST_MISMATCH", role)
    return digests[0]


def _executable_evidence(value: str, *, reason: str) -> tuple[str, Mapping[str, Any]]:
    resolved_name = shutil.which(value) if not Path(value).is_absolute() else value
    if not resolved_name:
        _fail(reason, "not found")
    try:
        path = Path(resolved_name).resolve(strict=True)
        if path.name == "codex.js" and (path.parent.parent / "package.json").is_file():
            candidates = tuple(candidate.resolve(strict=True) for candidate in
                               (path.parent.parent).glob(
                                   "node_modules/@openai/codex-*/vendor/*/bin/codex")
                               if candidate.is_file() and os.access(candidate, os.X_OK))
            if len(candidates) != 1:
                _fail(reason, "native executable not unique")
            path = candidates[0]
        _check_resolved_path_ancestors(path, reason=reason)
        info = path.stat()
        if (not path.is_absolute() or not stat.S_ISREG(info.st_mode)
                or info.st_uid not in _trusted_host_owner_uids()
                or info.st_mode & 0o002
                or (info.st_mode & 0o020
                    and (info.st_uid != os.getuid()
                         or not _group_is_exclusive_to_current_uid(info.st_gid)))
                or not os.access(path, os.X_OK)):
            _fail(reason, "unsafe executable")
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        result = subprocess.run([str(path), "--version"], text=True, capture_output=True,
                                check=False, timeout=10)
        version = (result.stdout or result.stderr).strip()
        if result.returncode != 0 or not version or "\n" in version:
            _fail(reason, "version unavailable")
    except LaunchIntentError:
        raise
    except (OSError, subprocess.SubprocessError) as exc:
        _fail(reason, type(exc).__name__)
    return str(path), {"path": str(path), "sha256": digest, "version": version,
                       "uid": info.st_uid, "mode": f"{stat.S_IMODE(info.st_mode):04o}"}


def _stable_executable_evidence(value: str, *, reason: str) -> tuple[str, Mapping[str, Any]]:
    """Resolve and measure an executable twice before accepting it as authority data.

    The second lookup catches a PATH replacement as well as path, digest, version,
    owner, or mode changes made while launch intent is being derived.
    """
    first_path, first = _executable_evidence(value, reason=reason)
    second_path, second = _executable_evidence(value, reason=reason)
    if first_path != second_path or first != second:
        _fail(reason, "executable evidence changed during validation")
    return first_path, first


def _validate_manifest(manifest: Mapping[str, Any]) -> tuple[Mapping[str, Any], str, str,
                                                              Mapping[str, Any]]:
    launch = _exact_keys(manifest.get("codex_supervisor_launch"), {
        "schema_version", "change_plan_schema", "change_plan_root", "roles",
        "executables", "runtime_root_template", "permission_profile",
        "canonical_ledger_platform", "reservation_contract", "issuer_contract",
    }, "MANIFEST_INVALID")
    if (launch["schema_version"] != "codex-launch-intent/1"
            or launch["change_plan_schema"] != "codex-change-plan/2"
            or launch["change_plan_root"] != str(_PLAN_ROOT)
            or launch["canonical_ledger_platform"] != "codex-supervisor"
            or launch["reservation_contract"] != "same-entry/intent-digest-v1"
            or launch["runtime_root_template"] != "tmp/_codex_sessions/{task_key}/runtime-home"
            or launch["permission_profile"] != "issue-supervised"
            or launch["issuer_contract"] != {
                "schema_version": "codex-change-plan-issuance/1",
                "command": "python3 -m issue_start.codex_launch_control issue",
                "sources_root": "tmp/_codex_control/sources",
            }
            or launch["roles"] != _EXPECTED_ROLE_CONFIG):
        _fail("MANIFEST_INVALID", "semantic value mismatch")
    executables = _exact_keys(launch["executables"], {"bwrap", "codex"}, "MANIFEST_INVALID")
    codex = _exact_keys(executables["codex"], {"lookup_name", "sandbox_alias"},
                        "MANIFEST_INVALID")
    if (executables["bwrap"] != "/usr/bin/bwrap" or codex != {
        "lookup_name": "codex", "sandbox_alias": "/run/issue-supervised/codex"
    }):
        _fail("MANIFEST_INVALID", "executable policy mismatch")
    bwrap_path, bwrap_evidence = _stable_executable_evidence(
        executables["bwrap"], reason="BWRAP_EXECUTABLE_INVALID",
    )
    codex_path, codex_evidence = _stable_executable_evidence(
        codex["lookup_name"], reason="CODEX_EXECUTABLE_INVALID",
    )
    return launch, bwrap_path, codex_path, {"bwrap": bwrap_evidence, "codex": codex_evidence}


def _source_descriptor(value: object, *, kind: str) -> Mapping[str, Any]:
    fields = {"path", "sha256", "provenance"}
    descriptor = _exact_keys(value, fields, f"{kind}_SOURCE_INVALID")
    path = _safe_relative(descriptor["path"], root=_CONTROL_ROOT,
                          reason=f"{kind}_SOURCE_INVALID")
    digest = descriptor["sha256"]
    provenance = _exact_keys(descriptor["provenance"], {
        "source_type", "captured_at", "captured_by", "capture_method",
    }, f"{kind}_SOURCE_INVALID")
    expected_type = "github-issue-snapshot" if kind == "ISSUE" else "finding-karte-snapshot"
    if (not isinstance(digest, str) or not _SHA256.fullmatch(digest)
            or provenance["source_type"] != expected_type):
        _fail(f"{kind}_SOURCE_INVALID")
    _capture_record({
        "captured_at": provenance["captured_at"],
        "captured_by": provenance["captured_by"],
        "capture_method": provenance["capture_method"],
    }, kind=kind, reason=f"{kind}_SOURCE_INVALID")
    return {**descriptor, "path": str(path)}


def _capture_record(value: object, *, kind: str, reason: str) -> Mapping[str, str]:
    """Validate caller-observed capture facts without claiming identity proof."""
    capture = _exact_keys(value, {
        "captured_at", "captured_by", "capture_method",
    }, reason)
    expected_method = "github-api" if kind == "ISSUE" else "karte-cli"
    timestamp = capture["captured_at"]
    if (not isinstance(timestamp, str)
            or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]{8}Z", timestamp)
            or not isinstance(capture["captured_by"], str)
            or not capture["captured_by"].strip()
            or len(capture["captured_by"]) > 128
            or any(ord(character) < 0x20 for character in capture["captured_by"])
            or capture["capture_method"] != expected_method):
        _fail(reason, "capture provenance")
    try:
        datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise LaunchIntentError(reason, "capture timestamp") from exc
    return capture


def _issue_snapshot(raw: str, *, descriptor: Mapping[str, Any], request: LaunchRequest,
                    repository: str) -> tuple[str, Mapping[str, Any]]:
    if _sha(raw) != descriptor["sha256"]:
        _fail("ISSUE_SOURCE_INVALID", "digest")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LaunchIntentError("ISSUE_SOURCE_INVALID", "invalid JSON") from exc
    envelope = _exact_keys(value, {
        "schema_version", "repository", "issue", "url", "title", "body",
        "acceptance_criteria", "capture",
    }, "ISSUE_SOURCE_INVALID")
    criteria = envelope["acceptance_criteria"]
    if (envelope["schema_version"] != "codex-issue-snapshot/2"
            or envelope["repository"] != repository or envelope["issue"] != request.issue
            or envelope["url"] != f"https://github.com/{repository}/issues/{request.issue}"
            or not isinstance(envelope["title"], str) or not envelope["title"].strip()
            or not isinstance(envelope["body"], str) or not envelope["body"].strip()
            or not isinstance(criteria, list) or not criteria
            or any(not isinstance(item, str) or not item.strip() for item in criteria)):
        _fail("ISSUE_SOURCE_INVALID", "issue/AC semantics")
    _capture_record(envelope["capture"], kind="ISSUE", reason="ISSUE_SOURCE_INVALID")
    rendered = (f"# {envelope['title']}\n\n{envelope['body']}\n\n"
                "## Acceptance criteria\n\n" + "\n".join(f"- {item}" for item in criteria))
    return rendered, envelope


def _karte_snapshot(raw: str, *, descriptor: Mapping[str, Any], request: LaunchRequest,
                    finding_ids: tuple[str, ...], round_number: int) -> tuple[str, Mapping[str, Any]]:
    if _sha(raw) != descriptor["sha256"]:
        _fail("KARTE_SOURCE_INVALID", "digest")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LaunchIntentError("KARTE_SOURCE_INVALID", "invalid JSON") from exc
    envelope = _exact_keys(value, {
        "schema_version", "issue", "round", "open_findings", "capture",
    }, "KARTE_SOURCE_INVALID")
    findings = envelope["open_findings"]
    if (envelope["schema_version"] != "codex-karte-snapshot/2"
            or envelope["issue"] != request.issue or envelope["round"] != round_number
            or not isinstance(findings, list) or not findings):
        _fail("KARTE_SOURCE_INVALID", "issue/round semantics")
    _capture_record(envelope["capture"], kind="KARTE", reason="KARTE_SOURCE_INVALID")
    actual: list[str] = []
    rendered: list[str] = []
    for item in findings:
        finding = _exact_keys(item, {"id", "status", "summary"}, "KARTE_SOURCE_INVALID")
        if (not isinstance(finding["id"], str)
                or _FINDING_ID.fullmatch(finding["id"]) is None
                or finding["status"] != "open"
                or not isinstance(finding["summary"], str) or not finding["summary"].strip()):
            _fail("KARTE_SOURCE_INVALID", "finding semantics")
        actual.append(finding["id"])
        rendered.append(f"- {finding['id']}: {finding['summary']}")
    if tuple(actual) != finding_ids or len(set(actual)) != len(actual):
        _fail("KARTE_SOURCE_INVALID", "open finding IDs do not exact-match plan")
    return (f"# Karte: issue-{request.issue}; round {round_number}\n\n" + "\n".join(rendered),
            envelope)


def _canonical_entry(value: Mapping[str, Any], *, request: LaunchRequest,
                     round_number: int, facts: GitFacts) -> None:
    expected_round = None if request.role == "issue-implementer" else round_number
    oid = value.get("initial_oid", value.get("expected_oid"))
    if (value.get("platform") != "codex-supervisor"
            or value.get("issue") != request.issue or value.get("agent_type") != request.role
            or value.get("round") != expected_round
            or value.get("repository") != facts.repository
            or value.get("workspace") != facts.workspace
            or value.get("branch_name") != facts.branch_name
            or oid != facts.head_oid
            or value.get("change_plan_id") != request.change_plan_id
            or value.get("issuance_status") != "complete"
            or value.get("status") not in {"open", "running"}):
        _fail("CANONICAL_LEDGER_MISMATCH")


def _protected_paths(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        _fail("PROTECTED_PLAN_INVALID")
    result: list[str] = []
    for raw in value:
        item = _exact_keys(raw, {"path", "base_sha256"}, "PROTECTED_PLAN_INVALID")
        path = _safe_relative(item["path"], reason="PROTECTED_PLAN_INVALID")
        digest = item["base_sha256"]
        if (not str(path).startswith((".codex/", ".agents/", ".ai/agents/"))
                or not isinstance(digest, str) or not _SHA256.fullmatch(digest)):
            _fail("PROTECTED_PLAN_INVALID")
        result.append(f"{path}={digest}")
    if len(result) != len(set(result)) or len({item.rpartition("=")[0] for item in result}) != len(result):
        _fail("PROTECTED_PLAN_INVALID", "duplicate")
    return tuple(sorted(result))


def generate_launch_intent(
    request: LaunchRequest, *, plan: Mapping[str, Any], manifest: Mapping[str, Any],
    repo_root: Path, source_material: Mapping[str, str],
    canonical_facts: GitFacts | None = None,
    canonical_entry: Mapping[str, Any] | None = None,
) -> LaunchIntent:
    """Pure derivation core; production callers must pass host-derived facts."""
    round_number = _validate_request(request)
    if canonical_facts is None or canonical_entry is None:
        _fail("CANONICAL_FACTS_REQUIRED")
    facts = canonical_facts
    if (not _REPOSITORY.fullmatch(facts.repository) or not Path(facts.workspace).is_absolute()
            or not _OID.fullmatch(facts.head_oid)):
        _fail("CANONICAL_FACTS_INVALID")
    _canonical_entry(canonical_entry, request=request, round_number=round_number, facts=facts)
    launch, bwrap, codex, executable_evidence = _validate_manifest(manifest)
    plan = _exact_keys(plan, {
        "schema_version", "change_plan_id", "owner_approval", "issue", "role",
        "fixer_round", "ledger_entry_id", "issue_source", "finding_ids", "karte_source",
        "protected_plan",
    }, "CHANGE_PLAN_INVALID")
    approval = _exact_keys(plan["owner_approval"], {"status", "actor", "recorded_at"},
                           "APPROVAL_INVALID")
    if (plan["schema_version"] != launch["change_plan_schema"]
            or plan["change_plan_id"] != request.change_plan_id
            or plan["issue"] != request.issue or plan["role"] != request.role
            or plan["fixer_round"] != request.fixer_round
            or approval["status"] != "approved"
            or not isinstance(approval["actor"], str) or not approval["actor"].strip()
            or not isinstance(approval["recorded_at"], str)
            or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]{8}Z", approval["recorded_at"])
            or plan["ledger_entry_id"] != canonical_entry.get("entry_id")
            or approval["actor"] != canonical_entry.get("approved_by")
            or approval["recorded_at"] != canonical_entry.get("approval_recorded_at")):
        _fail("CHANGE_PLAN_MISMATCH")

    issue_descriptor = _source_descriptor(plan["issue_source"], kind="ISSUE")
    issue_raw = source_material.get("issue")
    if not isinstance(issue_raw, str):
        _fail("ISSUE_SOURCE_INVALID")
    issue_text, issue_envelope = _issue_snapshot(
        issue_raw, descriptor=issue_descriptor, request=request, repository=facts.repository,
    )
    finding_raw = plan["finding_ids"]
    if not isinstance(finding_raw, list) or any(not isinstance(item, str) for item in finding_raw):
        _fail("FINDINGS_INVALID")
    finding_ids = tuple(finding_raw)
    karte_descriptor: Mapping[str, Any] | None = None
    karte_text = ""
    if request.role == "issue-implementer":
        if finding_ids or plan["karte_source"] is not None:
            _fail("IMPLEMENTER_SOURCE_INVALID")
    else:
        if (not finding_ids or any((_FINDING_ID.fullmatch(item) is None
                                    or int(_FINDING_ID.fullmatch(item).group(1)) != request.issue)
                                   for item in finding_ids)
                or len(set(finding_ids)) != len(finding_ids)):
            _fail("FINDINGS_INVALID")
        karte_descriptor = _source_descriptor(plan["karte_source"], kind="KARTE")
        karte_raw = source_material.get("karte")
        if not isinstance(karte_raw, str):
            _fail("KARTE_SOURCE_INVALID")
        karte_text, karte_envelope = _karte_snapshot(
            karte_raw, descriptor=karte_descriptor, request=request,
            finding_ids=finding_ids, round_number=round_number,
        )
        if any(karte_descriptor["provenance"][key] != karte_envelope["capture"][key]
               for key in ("captured_at", "captured_by", "capture_method")):
            _fail("KARTE_SOURCE_INVALID", "capture provenance mismatch")

    if any(issue_descriptor["provenance"][key] != issue_envelope["capture"][key]
           for key in ("captured_at", "captured_by", "capture_method")):
        _fail("ISSUE_SOURCE_INVALID", "capture provenance mismatch")

    role_config = launch["roles"][request.role]
    values = {"issue": request.issue, "round": round_number,
              "change_plan_id": request.change_plan_id,
              "finding_ids": ", ".join(finding_ids), "issue_snapshot": issue_text,
              "karte_path": "" if karte_descriptor is None else karte_descriptor["path"],
              "karte_snapshot": karte_text}
    task_key = role_config["task_key_template"].format_map(values)
    handoff = role_config["handoff_template"].format_map(values)
    runtime = launch["runtime_root_template"].format(task_key=task_key)
    for candidate, reason, root in (
        (handoff, "HANDOFF_INVALID", PurePosixPath("tmp/_handoff")),
        (runtime, "RUNTIME_ROOT_INVALID", PurePosixPath("tmp/_codex_sessions")),
    ):
        _safe_relative(candidate, root=root, reason=reason)
    prompt = role_config["prompt_template"].format_map(values)
    protected_values = _protected_paths(plan["protected_plan"])
    canonical_protected = canonical_entry.get("protected_plan")
    if (canonical_entry.get("task_key") != task_key
            or canonical_entry.get("handoff_path") != handoff
            or canonical_protected != plan["protected_plan"]):
        _fail("CANONICAL_LEDGER_MISMATCH", "derived launch fields")
    provenance: dict[str, Mapping[str, Any]] = {
        "issue": {"url": issue_envelope["url"], "sha256": issue_descriptor["sha256"],
                  **issue_descriptor["provenance"]},
    }
    if karte_descriptor is not None:
        provenance["karte"] = {"path": karte_descriptor["path"],
                               "sha256": karte_descriptor["sha256"],
                               **karte_descriptor["provenance"]}
    return LaunchIntent(
        schema_version=launch["schema_version"], issue=request.issue, role=request.role,
        round_number=round_number, change_plan_id=request.change_plan_id,
        repository=facts.repository, workspace=facts.workspace, branch_name=facts.branch_name,
        expected_oid=facts.head_oid, task_key=task_key, handoff_path=handoff,
        model=role_config["model"], reasoning_effort=role_config["reasoning_effort"],
        bwrap_executable=bwrap, codex_executable=codex,
        executable_evidence=executable_evidence,
        permission_profile=launch["permission_profile"], runtime_root=runtime,
        protected_paths=protected_values, finding_ids=finding_ids,
        source_provenance=provenance, prompt=prompt,
        ledger_entry_id=str(canonical_entry["entry_id"]),
        plan_digest=_canonical_digest(plan), manifest_digest=_canonical_digest(manifest),
        canonical_entry_digest=_canonical_digest({
            key: canonical_entry.get(key) for key in (
                "entry_id", "platform", "issue", "agent_type", "round", "repository",
                "workspace", "branch_name", "initial_oid", "task_key", "handoff_path",
                "protected_plan", "change_plan_id", "issuance_status",
            )
        }),
    )


def load_launch_intent(request: LaunchRequest, *, cwd: Path | None = None) -> LaunchIntent:
    _validate_request(request)
    candidate = Path.cwd() if cwd is None else Path(cwd)
    try:
        main_root = worktree_ledger.main_worktree_root(candidate).resolve(strict=True)
    except (OSError, worktree_ledger.LedgerError) as exc:
        raise LaunchIntentError("CONTROL_ROOT_INVALID", type(exc).__name__) from exc
    manifest = _secure_json(
        main_root, PurePosixPath("issue_start/managed-entrypoints-v2.json"),
        reason="MANIFEST_INVALID", leaf_private=False,
    )
    launch = manifest.get("codex_supervisor_launch")
    plan_root = launch.get("change_plan_root") if isinstance(launch, Mapping) else None
    if plan_root != str(_PLAN_ROOT):
        _fail("MANIFEST_INVALID", "change plan root")
    plan_path = _PLAN_ROOT / f"{request.change_plan_id}.json"
    plan = _secure_json(main_root, plan_path, reason="CHANGE_PLAN_MISSING",
                        private_from=_CONTROL_ROOT)
    ledger_id = plan.get("ledger_entry_id")
    if not isinstance(ledger_id, str) or not _ENTRY_ID.fullmatch(ledger_id):
        _fail("CHANGE_PLAN_INVALID", "ledger_entry_id")
    ledger = _secure_json(
        main_root, PurePosixPath("tmp/_worktree/ledger.json"), reason="CANONICAL_LEDGER_INVALID",
        leaf_private=False,
    )
    if ledger.get("schema_version") != "worktree-ledger/1" or not isinstance(ledger.get("entries"), list):
        _fail("CANONICAL_LEDGER_INVALID")
    entries = [item for item in ledger["entries"]
               if isinstance(item, Mapping) and item.get("entry_id") == ledger_id]
    if len(entries) != 1:
        _fail("CANONICAL_LEDGER_MISSING" if not entries else "CANONICAL_LEDGER_DUPLICATE")
    entry = entries[0]
    workspace = entry.get("workspace")
    if not isinstance(workspace, str):
        _fail("CANONICAL_LEDGER_MISMATCH", "workspace")
    try:
        facts = inspect_git_facts(workspace)
    except Exception as exc:
        raise LaunchIntentError("LIVE_GIT_FACTS_INVALID", getattr(exc, "reason", type(exc).__name__)) from exc

    issue_descriptor = _source_descriptor(plan.get("issue_source"), kind="ISSUE")
    issue_raw = _secure_text(
        main_root, PurePosixPath(issue_descriptor["path"]), reason="ISSUE_SOURCE_INVALID",
        private_from=_CONTROL_ROOT,
    )
    materials = {"issue": issue_raw}
    if request.role == "issue-fixer":
        karte_descriptor = _source_descriptor(plan.get("karte_source"), kind="KARTE")
        materials["karte"] = _secure_text(
            main_root, PurePosixPath(karte_descriptor["path"]), reason="KARTE_SOURCE_INVALID",
            private_from=_CONTROL_ROOT,
        )
    intent = generate_launch_intent(
        request, plan=plan, manifest=manifest, repo_root=main_root,
        source_material=materials, canonical_facts=facts, canonical_entry=entry,
    )
    return replace(intent, role_contract_digest=_role_contract_digest(
        main_root, Path(facts.workspace), request.role,
    ))


def _deny(stdout: TextIO, reason: str) -> None:
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}, stdout, sort_keys=True)
    stdout.write("\n")


def _command_tokens(command: str) -> tuple[list[str], bool]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|\n")
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        _fail("COMMAND_INVALID")
    return tokens, any(_is_shell_separator(token) for token in tokens)


def _is_shell_separator(token: str) -> bool:
    return bool(token) and all(character in ";&|\n" for character in token)


def _parse_launch_command(command: str) -> LaunchRequest | None:
    """Recognise only the documented supervisor spelling.

    This hook is an early typo/shape guard, not a general shell parser or the
    launch authority.  A direct ``codex exec`` hidden behind another wrapper is
    deliberately outside this boundary; the four-input supervisor remains the
    security boundary.
    """

    tokens, compound = _command_tokens(command)
    if not tokens:
        return None
    related = "issue_start.codex_supervisor" in tokens and any(
        item in {"run", "resume"} for item in tokens
    )
    if not related:
        return None
    if compound:
        _fail("COMMAND_INVALID", "compound launch")
    if tokens[0] == "rtk":
        tokens = tokens[1:]
    prefix = ["python3", "-m", "issue_start.codex_supervisor"]
    if tokens[:3] != prefix or len(tokens) < 4 or tokens[3] not in {"run", "resume"}:
        _fail("COMMAND_INVALID", "non-canonical launch prefix")
    verb = tokens[3]
    fields = tokens[4:]
    expected_names = ["--issue", "--role", "--change-plan-id"]
    if len(fields) not in {6, 8}:
        _fail("COMMAND_INVALID", "field count")
    names = fields[::2]
    values = fields[1::2]
    if names[:3] != expected_names or any(value.startswith("--") for value in values):
        _fail("COMMAND_INVALID", "field order")
    fixer_round: int | None = None
    if len(fields) == 8:
        if names != expected_names + ["--fixer-round"]:
            _fail("COMMAND_INVALID", "field order")
        if not re.fullmatch(r"[1-9][0-9]*", values[3]):
            _fail("COMMAND_INVALID", "fixer round")
        fixer_round = int(values[3])
    if not re.fullmatch(r"[1-9][0-9]*", values[0]):
        _fail("COMMAND_INVALID", "issue")
    request = LaunchRequest(int(values[0]), values[1], values[2], fixer_round)
    _validate_request(request)
    return request


def run_hook(*, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout,
             cwd: Path | None = None) -> int:
    try:
        payload = json.load(stdin)
        if not isinstance(payload, Mapping):
            _fail("HOOK_PAYLOAD_INVALID")
        tool_input = payload.get("tool_input")
        if payload.get("tool_name") != "Bash" or not isinstance(tool_input, Mapping):
            return 0
        command = tool_input.get("command")
        if not isinstance(command, str):
            _fail("HOOK_PAYLOAD_INVALID")
        request = _parse_launch_command(command)
        if request is not None:
            load_launch_intent(request, cwd=cwd)
    except (LaunchIntentError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        reason = exc.reason if isinstance(exc, LaunchIntentError) else "HOOK_PAYLOAD_INVALID"
        _deny(stdout, reason)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode", required=True)
    subparsers.add_parser("hook")
    render = subparsers.add_parser("render")
    render.add_argument("--issue", required=True, type=int)
    render.add_argument("--role", required=True)
    render.add_argument("--change-plan-id", required=True)
    render.add_argument("--fixer-round", type=int)
    args = parser.parse_args(argv)
    if args.mode == "hook":
        return run_hook()
    try:
        intent = load_launch_intent(
            LaunchRequest(args.issue, args.role, args.change_plan_id, args.fixer_round)
        )
    except LaunchIntentError as exc:
        print(exc, file=sys.stderr)
        return 20
    json.dump(asdict(intent), sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
