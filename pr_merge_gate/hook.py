"""Claude/Codex 共通 PR merge PreToolUse hook。"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, TextIO

from blocker_gate.auth import resolve_github_token

from .audit import AuditError, append_decision
from .classifier import PreUseClassification, classify_pre_use
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


def run(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    cwd: Path | None = None,
    audit_file: Path | None = None,
) -> int:
    classification: PreUseClassification | None = None
    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload")
        classification = classify_pre_use(payload, cwd=cwd)
        if classification is None:
            return 0
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
    try:
        append_decision(evidence, path=audit_file)
    except AuditError:
        evidence = fail_closed(
            evidence["binding"]["operation_fingerprint"],
            "HOOK_INTEGRITY_ERROR",
            classification.operation if classification is not None else None,
        )
    if evidence["result"] != "ALLOW":
        json.dump(_deny(_reason(evidence)), stdout, ensure_ascii=False, separators=(",", ":"))
        stdout.write("\n")
        return 0
    stderr.write(json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


def main() -> int:
    return run(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
