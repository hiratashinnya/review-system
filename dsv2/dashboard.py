"""doc-system v2 dashboard 用の機械集計。

``00-dashboard.md`` は手書きの運用ハブとして残し、本モジュールは ``nodes/**`` から検算可能な
Markdown スナップショットを生成する。対象は全体の stage/type 件数と、判断待ちとして扱う
FND/Q/DD/PEND の lifecycle status である。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


ATTENTION_STATUSES = {
    "fnd": {"open"},
    "q": {"open"},
    "dd": {"decided"},
    "pend": {"open", "deferred"},
}


@dataclass(frozen=True)
class DashboardSummary:
    """dashboard snapshot の集計結果。"""

    total: int
    stage_counts: list[tuple[str, int]]
    type_counts: list[tuple[str, int]]
    status_counts: list[tuple[str, str, int]]
    attention_nodes: list[dict]


def build_summary(meta: dict) -> DashboardSummary:
    """meta.json 互換 dict から dashboard 集計を作る。"""
    nodes = list(meta.get("nodes", []))
    stage_counter = Counter(str(n.get("stage", "")) for n in nodes)
    type_counter = Counter(str(n.get("type", "")) for n in nodes)
    status_counter = Counter(
        (str(n.get("type", "")), str(n.get("status", "")))
        for n in nodes
        if n.get("status")
    )
    attention_nodes = sorted(
        (
            n
            for n in nodes
            if n.get("type") in ATTENTION_STATUSES
            and n.get("status") in ATTENTION_STATUSES[str(n.get("type"))]
        ),
        key=lambda n: (
            str(n.get("type", "")),
            str(n.get("status", "")),
            str(n.get("scheduled", "")),
            str(n.get("title", "")),
        ),
    )
    return DashboardSummary(
        total=len(nodes),
        stage_counts=sorted(stage_counter.items()),
        type_counts=sorted(type_counter.items()),
        status_counts=sorted((typ, status, count) for (typ, status), count in status_counter.items()),
        attention_nodes=attention_nodes,
    )


def _cell(value: object) -> str:
    """Markdown table cell 用の最小 escape。"""
    text = str(value or "").replace("\n", " ").strip()
    return text.replace("|", "\\|") or "-"


def render_markdown(summary: DashboardSummary) -> str:
    """dashboard 集計を Markdown スナップショットとして描画する。"""
    lines = [
        "# doc-system-v2 dashboard snapshot",
        "",
        f"- total nodes: {summary.total}",
        f"- attention nodes: {len(summary.attention_nodes)}",
        "",
        "## Stage Counts",
        "",
        "| stage | count |",
        "|---|---:|",
    ]
    lines.extend(f"| `{_cell(stage)}` | {count} |" for stage, count in summary.stage_counts)
    lines.extend([
        "",
        "## Type Counts",
        "",
        "| type | count |",
        "|---|---:|",
    ])
    lines.extend(f"| `{_cell(typ)}` | {count} |" for typ, count in summary.type_counts)
    lines.extend([
        "",
        "## Lifecycle Status Counts",
        "",
        "| type | status | count |",
        "|---|---|---:|",
    ])
    lines.extend(
        f"| `{_cell(typ)}` | `{_cell(status)}` | {count} |"
        for typ, status, count in summary.status_counts
    )
    lines.extend([
        "",
        "## Attention Nodes",
        "",
        "| type | status | title | scheduled | path |",
        "|---|---|---|---|---|",
    ])
    if summary.attention_nodes:
        for node in summary.attention_nodes:
            lines.append(
                "| "
                f"`{_cell(node.get('type'))}` | "
                f"`{_cell(node.get('status'))}` | "
                f"{_cell(node.get('title'))} | "
                f"{_cell(node.get('scheduled'))} | "
                f"`{_cell(node.get('yaml_path'))}` |"
            )
    else:
        lines.append("| - | - | - | - | - |")
    return "\n".join(lines) + "\n"
