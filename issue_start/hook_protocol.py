"""PreToolUse hook の protocol 応答を組み立てる。"""

from __future__ import annotations

import json
from typing import Any, Mapping, TextIO


def deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def deny_reason(evidence: Mapping[str, Any]) -> str:
    reason = (
        f"issue-start-gate: {evidence['result']} {evidence['reason']} "
        f"policy={evidence['policy_version']}"
    )
    # detail は fail-close の修正情報を持つ唯一の項目なので deny 理由に含める。
    detail = evidence.get("detail")
    if isinstance(detail, str) and detail:
        reason += f" detail={detail}"
    blockers = evidence.get("blockers")
    if isinstance(blockers, list) and blockers:
        reason += " blockers=" + json.dumps(
            blockers, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    return reason


def write_deny(stdout: TextIO, evidence: Mapping[str, Any]) -> int:
    json.dump(
        deny(deny_reason(evidence)), stdout, ensure_ascii=False, separators=(",", ":")
    )
    stdout.write("\n")
    return 0


def write_evidence(stderr: TextIO, evidence: Mapping[str, Any]) -> None:
    stderr.write(
        json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )
