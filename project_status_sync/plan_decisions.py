"""評価結果と Project の Status から1 item の遷移・警告を決める。"""

from __future__ import annotations

from typing import Any

from .model import (
    ACTIVE_STATUSES,
    Abort,
    BLOCKABLE_STATUSES,
    BLOCKED,
    DONE,
    Plan,
    PlannedChange,
    ProjectItem,
    READY,
    SyncWarning,
)


def plan_from_findings(
    item: ProjectItem,
    findings: list[Any],
    seen_warnings: set[tuple[str, str, str]],
) -> Plan:
    if any(finding.code == "ISSUE_STATE_UNKNOWN" for finding in findings):
        return Plan(
            abort=Abort(
                "ISSUE_STATE_UNKNOWN",
                f"{item.issue_ref}: 依存グラフに状態不明の Issue がある",
            )
        )

    closure = [
        finding
        for finding in findings
        if finding.code == "CLOSURE_OPEN_DESCENDANT"
    ]
    if closure:
        warnings = []
        for finding in closure:
            key = ("CLOSURE_OPEN_DESCENDANT", finding.subject, "/".join(finding.path))
            if key in seen_warnings:
                continue
            seen_warnings.add(key)
            warnings.append(
                SyncWarning(
                    "CLOSURE_OPEN_DESCENDANT",
                    item.issue_ref,
                    f"closed の親 {finding.subject} に open の子孫がある"
                    f"（path: {' -> '.join(finding.path)}）",
                )
            )
        return Plan(warnings=tuple(warnings), considered=1)

    blocked = any(finding.code == "OPEN_BLOCKER" for finding in findings)
    if item.status in ACTIVE_STATUSES:
        warnings = ()
        if blocked:
            warnings = (
                SyncWarning(
                    "ACTIVE_ITEM_BLOCKED",
                    item.issue_ref,
                    f"Status={item.status} のままブロッカーが付いた（Status は変更しない）",
                ),
            )
        return Plan(warnings=warnings, considered=1)

    if item.status in BLOCKABLE_STATUSES and blocked:
        change = PlannedChange(
            item.item_id, item.issue_ref, item.status, BLOCKED, "OPEN_BLOCKER"
        )
        return Plan(changes=(change,), considered=1)
    if item.status == BLOCKED and not blocked:
        change = PlannedChange(
            item.item_id, item.issue_ref, item.status, READY, "BLOCKER_CLEARED"
        )
        return Plan(changes=(change,), considered=1)
    return Plan(considered=1)
