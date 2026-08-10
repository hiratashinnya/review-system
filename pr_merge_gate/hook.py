"""Claude/Codex 共通 PR merge PreToolUse hook。"""

from __future__ import annotations

import io
import json
from pathlib import Path
import sys
from typing import Any, TextIO
import uuid

from blocker_gate.auth import resolve_github_token

from .audit import AuditError, append_completion, append_decision, hook_asset_hash
from .classifier import CLASSIFIER_VERSION, PreUseClassification, classify_pre_use
from .gate import PrMergeGateError, evaluate_merge_operation, fail_closed


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _reason(evidence: dict[str, Any]) -> str:
    return (
        "Codex AI agent PR merge gate: "
        f"{evidence['result']}/{evidence['reason']} (policy {evidence['policy_version']}); "
        "元のmerge操作は送信しません。blocker/API/hook状態を解消後に再実行してください。"
    )


def _hook_context(payload: dict[str, Any], event: str) -> tuple[str, str]:
    if payload.get("hook_event_name") != event:
        raise ValueError("hook_event_name")
    session_id = payload.get("session_id")
    turn_id = payload.get("turn_id")
    tool_use_id = payload.get("tool_use_id")
    if not (
        isinstance(session_id, str) and session_id
        and isinstance(turn_id, str) and turn_id
        and isinstance(tool_use_id, str) and tool_use_id
    ):
        raise ValueError("hook invocation identity")
    invocation_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, "\0".join((session_id, turn_id, tool_use_id)))
    )
    return invocation_id, tool_use_id


def run(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    cwd: Path | None = None,
    audit_file: Path | None = None,
) -> int:
    classification: PreUseClassification | None = None
    payload: dict[str, Any] | None = None
    invocation_id: str | None = None
    hook_event_id: str | None = None
    asset_hash: str | None = None
    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload")
        classification = classify_pre_use(payload, cwd=cwd)
        if classification is None:
            return 0
        invocation_id, hook_event_id = _hook_context(payload, "PreToolUse")
        asset_hash = hook_asset_hash()
        if classification.kind == "merge" and classification.operation is not None:
            evidence = evaluate_merge_operation(
                classification.operation, token=resolve_github_token()
            )
        else:
            evidence = fail_closed(
                classification.operation_fingerprint,
                classification.reason,
                classification.operation,
            )
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        fingerprint_value = (
            classification.operation_fingerprint if classification is not None else "sha256:" + "0" * 64
        )
        evidence = fail_closed(fingerprint_value, "CLASSIFIER_UNKNOWN")
    except PrMergeGateError as exc:
        fingerprint_value = (
            classification.operation_fingerprint if classification is not None else "sha256:" + "0" * 64
        )
        operation = classification.operation if classification is not None else None
        evidence = fail_closed(fingerprint_value, exc.reason, operation)
    except AuditError:
        fingerprint_value = (
            classification.operation_fingerprint if classification is not None else "sha256:" + "0" * 64
        )
        operation = classification.operation if classification is not None else None
        evidence = fail_closed(fingerprint_value, "HOOK_INTEGRITY_ERROR", operation)
    evidence["classifier_version"] = CLASSIFIER_VERSION
    evidence["invocation_id"] = invocation_id
    evidence["hook_event_id"] = hook_event_id
    evidence["hook_asset_hash"] = asset_hash
    try:
        append_decision(evidence, path=audit_file)
    except AuditError:
        evidence = fail_closed(
            evidence["binding"]["operation_fingerprint"],
            "HOOK_INTEGRITY_ERROR",
            classification.operation if classification is not None else None,
        )
        evidence.update(
            classifier_version=CLASSIFIER_VERSION,
            invocation_id=invocation_id,
            hook_event_id=hook_event_id,
            hook_asset_hash=asset_hash,
        )
    if evidence["result"] != "ALLOW":
        json.dump(_deny(_reason(evidence)), stdout, ensure_ascii=False, separators=(",", ":"))
        stdout.write("\n")
        return 0
    stderr.write(json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


def post_run(
    *, stdin: TextIO, stdout: TextIO, stderr: TextIO, cwd: Path | None = None,
    audit_file: Path | None = None,
) -> int:
    """PostToolUse responseを同じpre-use permitへ相関して監査する。"""
    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload")
        classification = classify_pre_use(payload, cwd=cwd)
        if classification is None:
            return 0
        if classification.kind != "merge" or classification.operation is None:
            raise AuditError("blocked operation reached PostToolUse")
        invocation_id, hook_event_id = _hook_context(payload, "PostToolUse")
        tool_name = payload.get("tool_name")
        if not isinstance(tool_name, str) or "tool_response" not in payload:
            raise ValueError("post payload")
        append_completion(
            invocation_id=invocation_id,
            hook_event_id=hook_event_id,
            operation_fingerprint=classification.operation.operation_fingerprint,
            classifier_version=CLASSIFIER_VERSION,
            asset_hash=hook_asset_hash(),
            tool_name=tool_name,
            tool_response=payload["tool_response"],
            path=audit_file,
        )
        return 0
    except (AuditError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        reason = "Codex AI agent PR merge gate: POST_AUDIT_INTEGRITY_ERROR/" + type(exc).__name__
        json.dump({"decision": "block", "reason": reason}, stdout, ensure_ascii=False)
        stdout.write("\n")
        stderr.write(reason + "\n")
        return 0


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}
    selected = post_run if isinstance(payload, dict) and payload.get("hook_event_name") == "PostToolUse" else run
    return selected(stdin=io.StringIO(raw), stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
