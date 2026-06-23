"""出力レンダリング（JSON 主・テーブル補助）。"""

from __future__ import annotations

import json
from typing import Any

from .model import Node


def to_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _truncate(s: str, width: int) -> str:
    s = s.replace("\n", " ")
    return s if len(s) <= width else s[: width - 1] + "…"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "(該当なし)"
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep = "  ".join("-" * widths[i] for i in range(len(headers)))
    body = "\n".join(
        "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) for row in rows
    )
    return f"{line}\n{sep}\n{body}"


def index_table(nodes: list[Node]) -> str:
    rows = [
        [n.id, n.type, n.version, str(n.line), _truncate(n.heading, 60)]
        for n in nodes
    ]
    return _table(["id", "type", "ver", "line", "heading"], rows)


def search_table(nodes: list[Node]) -> str:
    rows = [
        [n.id, n.type, n.version, n.file, _truncate(n.heading, 50)]
        for n in nodes
    ]
    return _table(["id", "type", "ver", "file", "heading"], rows)


def show_text(node: Node) -> str:
    lines = [
        f"# {node.id} ({node.type}) v{node.version}",
        f"{node.heading}",
        f"@ {node.file}:{node.line}",
    ]
    if node.labels:
        lines.append(f"labels: {list(node.labels)}")
    if node.scheduled:
        lines.append(f"scheduled: {node.scheduled}")
    if node.condition:
        lines.append(f"condition: {node.condition}")
    for k, v in node.fields.items():
        lines.append(f"{k}: {v}")
    if node.edges:
        lines.append("edges:")
        for e in node.edges:
            note = f"  # {e.note}" if e.note else ""
            lines.append(f"  - {e.to} (ref {e.ref_version}){note}")
    if node.parse_error:
        lines.append(f"parse_error: {node.parse_error}")
    lines.append("")
    lines.append(node.body)
    return "\n".join(lines)


def _drift_mark(drift: object) -> str:
    if drift is True:
        return "DRIFT"
    if drift is False:
        return "ok"
    return "?"


def deps_table(node_id: str, rows: list[dict]) -> str:
    trows = [
        [
            r["to"],
            str(r["ref_version"]),
            str(r["target_version"]) if r["target_version"] is not None else "-",
            "yes" if r["exists"] else "MISSING",
            _drift_mark(r["drift"]),
        ]
        for r in rows
    ]
    head = f"{node_id} の依存先 (出辺):"
    return f"{head}\n" + _table(["to", "ref", "target", "exists", "drift"], trows)


def dependents_table(node_id: str, rows: list[dict]) -> str:
    trows = [
        [
            r["from"],
            r["type"],
            str(r["ref_version"]),
            _drift_mark(r["drift"]),
            _truncate(r["heading"], 45),
        ]
        for r in rows
    ]
    head = f"{node_id} の依存元 (入辺):"
    return f"{head}\n" + _table(["from", "type", "ref", "drift", "heading"], trows)
