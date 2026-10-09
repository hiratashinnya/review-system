"""台帳エントリの生存・訂正関係を都度導出して Markdown に描画する。"""

from __future__ import annotations

from . import schema as schema_module
from .store import Store


class RenderError(ValueError):
    """台帳の置換関係を一意に描画できない。"""


def _escape_markdown(value: str) -> str:
    reserved = set("\\*_{}[]()#+-.!|><&") | {chr(96)}
    return "".join(f"\\{char}" if char in reserved else char for char in value)


def _entry_block(entry, successors: dict[str, list[str]]) -> list[str]:
    data = entry.data
    entry_id = entry.document_id
    lines = [f'<a id="{entry_id.lower()}"></a>', f"### {_escape_markdown(data['topic'])}"]
    lines.extend((f"- ID: {entry_id}", f"- 発生日: {data['occurred_at'].isoformat()}"))
    lines.append(f"- テーマ: {data.get('theme', 'なし')}; 判断軸: {data['decision_point']}")
    lines.extend((
        f"- 上書き対象ロール: {data['overridden_role']}",
        f"- divergence: {data['divergence']}",
        f"- 推論信頼度: {data['confidence_of_inference']}",
        f"- 記録者: {_escape_markdown(data['recorded_by'])}",
        f"- 対象資産: {', '.join(_escape_markdown(path) for path in data['affected_assets'])}",
    ))
    source_items = []
    for item in data["source"]:
        findings = ", ".join(item["finding_ids"]) or "なし"
        source_items.append(
            f"#{item['issue']} (PR {item['pr']}; round {item['round']}; findings: {findings})"
        )
    lines.append(f"- 出典: {'; '.join(source_items)}")
    previous = data.get("supersedes", "")
    if previous:
        lines.append(f"- 訂正元: [{previous}](#{previous.lower()})")
    for replacement in successors[entry_id]:
        lines.append(f"- 訂正先: [{replacement}](#{replacement.lower()})")
    lines.append("")
    for key, label in (
        ("background", "背景"), ("recommendation", "推奨"),
        ("recommendation_reason", "推奨理由"), ("uncertainty", "不確実性"),
        ("owner_verbatim", "オーナー逐語"), ("inferred_reason", "推論"),
    ):
        narrative = _escape_markdown(data["narrative"][key]).replace("\n", " ")
        lines.append(f"- {label}: {narrative}")
    return lines


def _successors(entries: list) -> dict[str, list[str]]:
    by_id = {entry.document_id: entry for entry in entries}
    successors = {entry_id: [] for entry_id in by_id}
    for entry in entries:
        target = entry.data.get("supersedes", "")
        if target and target not in by_id:
            raise RenderError(f"{entry.document_id} が存在しない訂正元を指している: {target}")
        if target:
            successors[target].append(entry.document_id)
    for start in by_id:
        seen = set()
        current = start
        while current:
            if current in seen:
                raise RenderError(f"supersedes に循環がある: {current}")
            seen.add(current)
            current = by_id[current].data.get("supersedes", "")
    for replacements in successors.values():
        replacements.sort()
    return successors


def render_ledger(store: Store) -> str:
    """supersedes だけから状態を算出し、一覧・生存記録・訂正記録を返す。"""
    entries = store.of(schema_module.LEDGER)
    successors = _successors(entries)
    ordered = sorted(
        entries,
        key=lambda entry: (entry.data["occurred_at"], entry.document_id),
    )
    living = [entry for entry in ordered if not successors[entry.document_id]]
    corrected = [entry for entry in ordered if successors[entry.document_id]]
    lines = ["# オーナー決定台帳", "", "## 生存決定一覧"]
    lines.extend(
        f"- [{_escape_markdown(entry.data['topic'])}](#{entry.document_id.lower()}) "
        f"({entry.document_id}; テーマ: {entry.data.get('theme', 'なし')})"
        for entry in reversed(living)
    )
    if not living:
        lines.append("- 該当なし")
    lines.extend(("", "## 生存する決定", ""))
    for entry in reversed(living):
        lines.extend(_entry_block(entry, successors))
    lines.extend(("## 訂正済みの決定", ""))
    for entry in corrected:
        lines.extend(_entry_block(entry, successors))
    return "\n".join(lines).rstrip() + "\n"
