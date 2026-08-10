"""Pre-use decision のredacted永続audit。"""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, Mapping

from blocker_gate.model import fingerprint


_HOOK_ASSETS = (
    ".codex/hooks.json",
    ".codex/hooks/pr-merge-gate.sh",
    ".claude/settings.json",
    ".claude/hooks/pr-merge-gate.sh",
    "pr_merge_gate/audit.py",
    "pr_merge_gate/classifier.py",
    "pr_merge_gate/gate.py",
    "pr_merge_gate/hook.py",
)


class AuditError(OSError):
    """安全なaudit appendを保証できない。"""


def audit_path(environ: Mapping[str, str] | None = None) -> Path:
    """XDG/HOME contractからaudit.jsonlを解決する。"""
    values = os.environ if environ is None else environ
    state = values.get("XDG_STATE_HOME")
    if state:
        root = Path(state)
    else:
        home = values.get("HOME")
        if not home:
            raise AuditError("HOME/XDG_STATE_HOME missing")
        root = Path(home) / ".local" / "state"
    if not root.is_absolute():
        raise AuditError("state path must be absolute")
    return root / "review-system" / "blocker-gate" / "audit.jsonl"


def hook_asset_hash(root: Path | None = None) -> str:
    """実行中hook一式を同一のredacted asset hashへ束縛する。"""
    project_root = Path(__file__).resolve().parents[1] if root is None else root.resolve()
    digest = hashlib.sha256()
    try:
        for relative in _HOOK_ASSETS:
            digest.update(relative.encode("utf-8") + b"\0")
            digest.update((project_root / relative).read_bytes())
            digest.update(b"\0")
    except OSError as exc:
        raise AuditError(str(exc)) from exc
    return "sha256:" + digest.hexdigest()


def _prepare_target(target: Path) -> None:
    directory = target.parent
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink():
        raise AuditError("audit directory symlink")
    directory.chmod(0o700)
    if target.exists():
        info = target.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise AuditError("unsafe audit file")


def _append_record(record: Mapping[str, Any], target: Path) -> None:
    try:
        _prepare_target(target)
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(target, flags, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            payload = json.dumps(
                record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8") + b"\n"
            remaining = memoryview(payload)
            while remaining:
                written = os.write(descriptor, remaining)
                if written < 1:
                    raise OSError("short audit write")
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except AuditError:
        raise
    except OSError as exc:
        raise AuditError(str(exc)) from exc


def append_decision(
    evidence: Mapping[str, Any], *, path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> None:
    """raw command/body/tokenを含まないpre-use decisionを0600 JSONLへappend+fsyncする。"""
    target = audit_path(environ) if path is None else path
    raw_binding = evidence.get("binding")
    binding: Mapping[str, Any] = raw_binding if isinstance(raw_binding, dict) else {}
    blocker = evidence.get("blocker_evidence")
    findings = evidence.get("findings")
    safe_findings = findings if isinstance(findings, list) else []
    record = {
        "schema_version": "pr-merge-audit/3",
        "record_type": "pre_use_decision",
        "policy_version": evidence.get("policy_version"),
        "classifier_version": evidence.get("classifier_version"),
        "hook_asset_hash": evidence.get("hook_asset_hash"),
        "hook_event_id": evidence.get("hook_event_id"),
        "result": evidence.get("result"),
        "reason": evidence.get("reason"),
        "repository": binding.get("repository"),
        "pr_number": binding.get("pr_number"),
        "head_oid": binding.get("head_oid"),
        "base_ref_name": binding.get("base_ref_name"),
        "default_branch": binding.get("default_branch"),
        "merge_method": binding.get("merge_method"),
        "transport": binding.get("transport"),
        "operation_fingerprint": binding.get("operation_fingerprint"),
        "invocation_id": evidence.get("invocation_id"),
        "blocker_invocation_id": blocker.get("invocation_id") if isinstance(blocker, dict) else None,
        "fetched_at": evidence.get("fetched_at"),
        "graphql_closing_set": evidence.get("graphql_closing_set", []),
        "delivered_message_closing_set": evidence.get("delivered_message_closing_set", []),
        "closing_set": evidence.get("closing_set", []),
        "findings": safe_findings,
        "dependency_paths": [
            item.get("path") for item in safe_findings
            if isinstance(item, dict) and isinstance(item.get("path"), list)
        ],
        "permit_issued": evidence.get("permit_issued") is True,
        "operation_dispatched": False,
        "merge_api_called": False,
        "next_action": evidence.get("next_action"),
    }
    _append_record(record, target)


def append_completion(
    *, invocation_id: str, hook_event_id: str, operation_fingerprint: str,
    classifier_version: str, asset_hash: str, tool_name: str, tool_response: Any,
    path: Path | None = None, environ: Mapping[str, str] | None = None,
) -> None:
    """対応するpermitがあるtool responseだけをredacted completionとして追記する。"""
    target = audit_path(environ) if path is None else path
    try:
        _prepare_target(target)
        if not target.exists():
            raise AuditError("pre-use permit missing")
        permit: Mapping[str, Any] | None = None
        for line in target.read_text(encoding="utf-8").splitlines():
            candidate = json.loads(line)
            if (
                isinstance(candidate, dict)
                and candidate.get("record_type") == "pre_use_decision"
                and candidate.get("invocation_id") == invocation_id
                and candidate.get("operation_fingerprint") == operation_fingerprint
                and candidate.get("permit_issued") is True
            ):
                permit = candidate
        if permit is None:
            raise AuditError("pre-use permit missing")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(str(exc)) from exc
    outcome = "unknown"
    explicit_merged: bool | None = None
    if isinstance(tool_response, dict):
        response_is_error = tool_response.get("isError") is True
        if response_is_error:
            outcome = "failure"
        elif isinstance(tool_response.get("exit_code"), int):
            outcome = "success" if tool_response["exit_code"] == 0 else "failure"
        result = tool_response.get("result")
        structured = tool_response.get("structuredContent")
        candidates = [tool_response]
        if isinstance(result, dict):
            candidates.append(result)
        if isinstance(structured, dict):
            candidates.append(structured)
            nested = structured.get("result")
            if isinstance(nested, dict):
                candidates.append(nested)
        if not response_is_error:
            for candidate in candidates:
                if isinstance(candidate.get("merged"), bool):
                    explicit_merged = candidate["merged"]
                    outcome = "success" if explicit_merged else "failure"
                    break
    api_called = (
        True
        if permit.get("transport") == "connector" and explicit_merged is True
        else None
    )
    record = {
        "schema_version": "pr-merge-audit/3",
        "record_type": "post_use_completion",
        "policy_version": permit.get("policy_version"),
        "classifier_version": classifier_version,
        "hook_asset_hash": asset_hash,
        "hook_event_id": hook_event_id,
        "invocation_id": invocation_id,
        "repository": permit.get("repository"),
        "pr_number": permit.get("pr_number"),
        "merge_method": permit.get("merge_method"),
        "transport": permit.get("transport"),
        "operation_fingerprint": operation_fingerprint,
        "tool_name": tool_name,
        "response_fingerprint": fingerprint({"tool_response": tool_response}),
        "response_outcome": outcome,
        "permit_issued": True,
        "operation_dispatched": True,
        "merge_api_called": api_called,
        "merge_api_call_evidence": (
            "CONNECTOR_MERGED_TRUE" if api_called is True else "NOT_PROVEN"
        ),
        "next_action": "MERGE_RESPONSE_RECORDED",
    }
    _append_record(record, target)
