"""snapshot と Project item の状態遷移計画を組み立てる。"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .model import Abort, Plan, PlannedChange, ProjectItem, SkippedItem, SyncWarning
from .plan_item import plan_item


def build_plan(
    snapshot: Mapping[str, Any],
    items: Sequence[ProjectItem],
    repository: str,
) -> Plan:
    """遷移表を適用して計画を返す。書き込みは行わない。"""
    if snapshot.get("repository") != repository:
        return Plan(
            abort=Abort(
                "SNAPSHOT_INVALID",
                f"repository mismatch: snapshot={snapshot.get('repository')!r} request={repository!r}",
            )
        )

    changes: list[PlannedChange] = []
    skipped: list[SkippedItem] = []
    warnings: list[SyncWarning] = []
    seen_warnings: set[tuple[str, str, str]] = set()
    considered = 0
    out_of_scope = 0
    ordered = sorted(items, key=lambda item: (item.issue_ref or "", item.item_id))
    for item in ordered:
        result = plan_item(snapshot, item, repository, seen_warnings)
        if result.abort is not None:
            return result
        changes.extend(result.changes)
        skipped.extend(result.skipped)
        warnings.extend(result.warnings)
        considered += result.considered
        out_of_scope += result.out_of_scope

    return Plan(
        changes=tuple(changes),
        skipped=tuple(skipped),
        warnings=tuple(warnings),
        abort=None,
        considered=considered,
        out_of_scope=out_of_scope,
    )
