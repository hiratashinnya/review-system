"""`report.json` の組み立てと `$GITHUB_STEP_SUMMARY` 用 markdown の描画。

依存仕様: Issue #460 Scope §2（report.json を孤立ブランチへ publish・
`$GITHUB_STEP_SUMMARY` に変更差分と警告と skipped の件数/対象を出す）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .model import REPORT_SCHEMA, Plan, PlannedChange, ProjectView


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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


def render_summary(report: Mapping[str, Any]) -> str:
    counts = report.get("counts") or {}
    lines = [
        "## Project Status sync",
        "",
        f"- mode: `{report.get('mode')}`",
        f"- snapshot generated_at: `{(report.get('snapshot') or {}).get('generated_at')}`",
        (
            "- counts: considered="
            f"{counts.get('considered')} planned={counts.get('planned')} "
            f"applied={counts.get('applied')} skipped={counts.get('skipped')} "
            f"warnings={counts.get('warnings')}"
        ),
        "",
    ]

    abort = report.get("abort")
    if abort:
        lines += [
            f"### 中断（1件も書いていない）: `{abort.get('code')}`",
            "",
            f"{abort.get('detail')}",
            "",
        ]

    changes = report.get("applied") if report.get("mode") == "apply" else report.get("planned")
    heading = "適用した変更" if report.get("mode") == "apply" else "変更計画（dry-run・未適用）"
    lines += [f"### {heading}（{len(changes or [])}件）", ""]
    if changes:
        lines += ["| Issue | from | to | reason |", "|---|---|---|---|"]
        lines += [
            f"| {row.get('issue_ref')} | {row.get('from')} | {row.get('to')} | {row.get('reason')} |"
            for row in changes
        ]
    else:
        lines.append("差分なし。")
    lines.append("")

    warnings = report.get("warnings") or []
    lines += [f"### 警告（{len(warnings)}件・CI を赤くする）", ""]
    if warnings:
        lines += ["| code | Issue | detail |", "|---|---|---|"]
        lines += [
            f"| {row.get('code')} | {row.get('issue_ref')} | {row.get('detail')} |"
            for row in warnings
        ]
    else:
        lines.append("なし。")
    lines.append("")

    skipped = report.get("skipped") or []
    lines += [f"### skipped（{len(skipped)}件・CI は赤くしない）", ""]
    if skipped:
        lines += ["| code | Issue | detail |", "|---|---|---|"]
        lines += [
            f"| {row.get('code')} | {row.get('issue_ref')} | {row.get('detail')} |"
            for row in skipped
        ]
    else:
        lines.append("なし。")
    lines.append("")
    return "\n".join(lines)
