"""Pre-use decision のredacted永続audit。"""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, Mapping

from blocker_gate.closing import (
    DELIVERED_MESSAGE_FORMATTER_VERSION,
    SQUASH_COMMIT_MESSAGES_EVIDENCE,
    SQUASH_COMMIT_MESSAGES_EVIDENCE_FINGERPRINT,
)
from blocker_gate.model import fingerprint


_AUDIT_SCHEMA_VERSION = "pr-merge-audit/4"
_CORRELATED_BINDING_FIELDS = (
    "repository",
    "pr_number",
    "head_oid",
    "expected_commit_count",
    "base_ref_name",
    "default_branch",
    "merge_method",
    "transport",
    "intercepted_commit_title_fingerprint",
    "intercepted_commit_message_fingerprint",
    "message_source_fingerprint",
    "delivered_message_fingerprint",
    "repository_merge_settings_fingerprint",
    "operation_fingerprint",
    "snapshot_fingerprint",
    "attempt",
    "pr_state",
    "pr_is_draft",
)


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
    """安全なaudit appendを保証できない。

    `reason` は redaction安全な固定語彙（payload由来の文字列を含まない）で、失敗した
    audit経路を呼び出し側が識別するために持つ。message は人間向けの補助情報であって
    hook出力には載せない（Issue #414: 例外クラス名だけを出力していたため、
    構造的に別物の4経路が同じ `AuditError` として報告され原因を特定できなかった）。
    """

    def __init__(self, message: str, *, reason: str = "AUDIT_WRITE_FAILED") -> None:
        super().__init__(message)
        self.reason = reason


def audit_path(environ: Mapping[str, str] | None = None) -> Path:
    """XDG/HOME contractからaudit.jsonlを解決する。"""
    values = os.environ if environ is None else environ
    state = values.get("XDG_STATE_HOME")
    if state:
        root = Path(state)
    else:
        home = values.get("HOME")
        if not home:
            raise AuditError("HOME/XDG_STATE_HOME missing", reason="AUDIT_PATH_INVALID")
        root = Path(home) / ".local" / "state"
    if not root.is_absolute():
        raise AuditError("state path must be absolute", reason="AUDIT_PATH_INVALID")
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
        raise AuditError(str(exc), reason="HOOK_ASSET_UNREADABLE") from exc
    return "sha256:" + digest.hexdigest()


def _prepare_target(target: Path) -> None:
    directory = target.parent
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink():
        raise AuditError("audit directory symlink", reason="AUDIT_FILE_UNSAFE")
    directory.chmod(0o700)
    if target.exists():
        info = target.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise AuditError("unsafe audit file", reason="AUDIT_FILE_UNSAFE")


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
        raise AuditError(str(exc), reason="AUDIT_WRITE_FAILED") from exc


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
    blocker_record = blocker if isinstance(blocker, dict) else {}
    record = {
        "schema_version": _AUDIT_SCHEMA_VERSION,
        "record_type": "pre_use_decision",
        "policy_version": evidence.get("policy_version"),
        "classifier_version": evidence.get("classifier_version"),
        "hook_asset_hash": evidence.get("hook_asset_hash"),
        "hook_event_id": evidence.get("hook_event_id"),
        "result": evidence.get("result"),
        "reason": evidence.get("reason"),
        **{key: binding.get(key) for key in _CORRELATED_BINDING_FIELDS},
        "invocation_id": evidence.get("invocation_id"),
        "blocker_invocation_id": blocker_record.get("invocation_id"),
        "blocker_policy_version": blocker_record.get("policy_version"),
        "blocker_classifier_version": blocker_record.get("classifier_version"),
        "blocker_result": blocker_record.get("result"),
        "blocker_reasons": blocker_record.get("reasons", []),
        "blocker_completed_at": blocker_record.get("completed_at"),
        "pages_complete": blocker_record.get("pages_complete"),
        "fetched_at": evidence.get("fetched_at"),
        "delivered_message_formatter_version": DELIVERED_MESSAGE_FORMATTER_VERSION,
        "squash_commit_messages_evidence_version": SQUASH_COMMIT_MESSAGES_EVIDENCE["version"],
        "squash_commit_messages_evidence_fingerprint": (
            SQUASH_COMMIT_MESSAGES_EVIDENCE_FINGERPRINT
        ),
        "squash_commit_messages_verified": SQUASH_COMMIT_MESSAGES_EVIDENCE["verified"],
        "squash_commit_messages_decision": SQUASH_COMMIT_MESSAGES_EVIDENCE["decision"],
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
    """対応するpermitがあるtool responseだけをredacted completionとして追記する。

    走査はJSONとして読めない行を読み飛ばす。append-only の共有ログには別プロセスの
    interleaved write で壊れた行が混じり得るが、1行の破損でpost-use auditが恒久的に
    停止するのは監査証跡の可用性を落とすだけで安全性を上げない（読み飛ばしは permit を
    「見つけられない」方向にしか働かず、permit なしでcompletionを発行する経路は増えない）。

    相関に失敗したときのreason codeは2つに分ける（Issue #436）。どちらもfail-closeで
    completionを追記しない点は同じだが、原因も処置もまったく別物なので、Issue #414が
    `AuditError` のクラス名を reason code へ割った理由がそのまま一段下にも当てはまる。

    - `PERMIT_MISSING`: この `invocation_id` を持つ permit 済みpre-useレコードが1件も
      見つからない。auditファイル不在・pre-use hookが動かなかった・当該行が破損して
      読み飛ばされた、のいずれか。
    - `PERMIT_OPERATION_MISMATCH`: `invocation_id` の permit は在るが
      `operation_fingerprint` が食い違う。**許可した操作と実行された操作が別物**という
      意味で、相関鍵の欠落ではなく整合性違反そのものを指す。実測された発生源は、
      同じPreToolUseイベントに登録された別hookが `hookSpecificOutput.updatedInput` で
      `tool_input.command` を書き換え（例: `gh pr merge …` → `rtk gh pr merge …`）、
      本gateが分類した文字列と実際に実行された文字列がずれるケース（Issue #436）。
    """
    target = audit_path(environ) if path is None else path
    try:
        _prepare_target(target)
        if not target.exists():
            raise AuditError("pre-use permit missing", reason="PERMIT_MISSING")
        permit: Mapping[str, Any] | None = None
        invocation_permitted = False
        for line in target.read_text(encoding="utf-8").splitlines():
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not (
                isinstance(candidate, dict)
                and candidate.get("record_type") == "pre_use_decision"
                and candidate.get("invocation_id") == invocation_id
                and candidate.get("permit_issued") is True
            ):
                continue
            invocation_permitted = True
            if candidate.get("operation_fingerprint") == operation_fingerprint:
                permit = candidate
        if permit is None:
            if invocation_permitted:
                raise AuditError(
                    "permitted operation does not match dispatched operation",
                    reason="PERMIT_OPERATION_MISMATCH",
                )
            raise AuditError("pre-use permit missing", reason="PERMIT_MISSING")
    except AuditError:
        raise
    except (OSError, UnicodeDecodeError) as exc:
        raise AuditError(str(exc), reason="AUDIT_READ_FAILED") from exc
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
        "schema_version": _AUDIT_SCHEMA_VERSION,
        "record_type": "post_use_completion",
        "policy_version": permit.get("policy_version"),
        "classifier_version": classifier_version,
        "hook_asset_hash": asset_hash,
        "hook_event_id": hook_event_id,
        "invocation_id": invocation_id,
        **{key: permit.get(key) for key in _CORRELATED_BINDING_FIELDS},
        "operation_fingerprint": operation_fingerprint,
        "blocker_invocation_id": permit.get("blocker_invocation_id"),
        "blocker_policy_version": permit.get("blocker_policy_version"),
        "blocker_classifier_version": permit.get("blocker_classifier_version"),
        "blocker_result": permit.get("blocker_result"),
        "blocker_reasons": permit.get("blocker_reasons", []),
        "blocker_completed_at": permit.get("blocker_completed_at"),
        "pages_complete": permit.get("pages_complete"),
        "fetched_at": permit.get("fetched_at"),
        "graphql_closing_set": permit.get("graphql_closing_set", []),
        "delivered_message_closing_set": permit.get(
            "delivered_message_closing_set", []
        ),
        "closing_set": permit.get("closing_set", []),
        "findings": permit.get("findings", []),
        "dependency_paths": permit.get("dependency_paths", []),
        "delivered_message_formatter_version": permit.get(
            "delivered_message_formatter_version"
        ),
        "squash_commit_messages_evidence_version": permit.get(
            "squash_commit_messages_evidence_version"
        ),
        "squash_commit_messages_evidence_fingerprint": permit.get(
            "squash_commit_messages_evidence_fingerprint"
        ),
        "squash_commit_messages_verified": permit.get(
            "squash_commit_messages_verified"
        ),
        "squash_commit_messages_decision": permit.get(
            "squash_commit_messages_decision"
        ),
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
