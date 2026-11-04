"""Plan と実行結果から schema 付き JSON report を構築する。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .model import REPORT_SCHEMA, Plan, PlannedChange, ProjectView


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def build_report(
    *,
    repository: str,
    project_id: str,
    project: ProjectView | None,
    snapshot: Mapping[str, Any] | None,
    plan: Plan,
    applied: Sequence[PlannedChange],
    apply_mode: bool,
    now: datetime,
) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": _timestamp(now),
        "repository": repository,
        "mode": "apply" if apply_mode else "dry-run",
        "project": {
            "id": project_id,
            "number": project.number if project is not None else None,
            "title": project.title if project is not None else None,
        },
        "snapshot": {
            "generated_at": snapshot.get("generated_at") if snapshot else None,
            "pages_complete": snapshot.get("pages_complete") if snapshot else None,
            "errors": list(snapshot.get("errors") or []) if snapshot else [],
        },
        "abort": plan.abort.to_dict() if plan.abort is not None else None,
        "counts": {
            "considered": plan.considered,
            "out_of_scope": plan.out_of_scope,
            "planned": len(plan.changes),
            "applied": len(applied),
            "skipped": len(plan.skipped),
            "warnings": len(plan.warnings),
        },
        "planned": [change.to_dict() for change in plan.changes],
        "applied": [change.to_dict() for change in applied],
        "skipped": [item.to_dict() for item in plan.skipped],
        "warnings": [item.to_dict() for item in plan.warnings],
    }


def is_red(report: Mapping[str, Any]) -> bool:
    """CI を赤くすべきか。skipped は赤にしない（故障ではないため）。"""
    return bool(report.get("abort")) or bool(report.get("warnings"))
