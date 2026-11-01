"""JSON report を GitHub Step Summary 用 Markdown に描画する。"""

from __future__ import annotations

from typing import Any, Mapping


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
