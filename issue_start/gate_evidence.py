from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from .gate_blocker_report import _blocker_report
from .gate_support import ISSUE_START_POLICY_VERSION, IssueStartError, IssueStartRequest



def _error_evidence(request: IssueStartRequest | None, reason: str, detail: str = "") -> dict[str, Any]:
    return {
        "schema_version": "issue-start-evidence/1",
        "policy_version": ISSUE_START_POLICY_VERSION,
        "result": "ERROR",
        "exit_code": 20,
        "reason": reason,
        "detail": detail,
        "binding": asdict(request) if request is not None else None,
        "blocker_evidence": None,
        "blockers": [],
        # 判定へ到達していないので取得経路も確定していない。
        "source": None,
        "snapshot_generated_at": None,
    }


def fail_closed(request: IssueStartRequest | None, exc: IssueStartError) -> dict[str, Any]:
    return _error_evidence(request, exc.reason, exc.detail)


def _result_evidence(
    request: IssueStartRequest,
    blocker: Mapping[str, Any],
    *,
    source: str,
    snapshot_generated_at: str | None,
    report_provider: Any,
) -> dict[str, Any]:
    if blocker["result"] != "ALLOW":
        blockers = (
            _blocker_report(report_provider, blocker)
            if blocker["result"] == "BLOCK"
            else []
        )
        return {
            "schema_version": "issue-start-evidence/1",
            "policy_version": ISSUE_START_POLICY_VERSION,
            "result": blocker["result"],
            "exit_code": blocker["exit_code"],
            "reason": blocker["primary_reason"],
            "fetched_at": blocker["fetched_at"],
            "binding": asdict(request),
            "blocker_evidence": blocker,
            "blockers": blockers,
            "source": source,
            "snapshot_generated_at": snapshot_generated_at,
        }
    return {
        "schema_version": "issue-start-evidence/1",
        "policy_version": ISSUE_START_POLICY_VERSION,
        "result": "ALLOW",
        "exit_code": 0,
        "reason": "ISSUE_START_ALLOWED",
        "fetched_at": blocker["fetched_at"],
        "binding": asdict(request),
        "blocker_evidence": blocker,
        "blockers": [],
        "source": source,
        "snapshot_generated_at": snapshot_generated_at,
    }
