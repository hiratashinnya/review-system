"""Markdown formatting of immutable ledger entries."""

import html
from urllib.parse import quote


def _fragment(value: str) -> str:
    return "".join(quote(c, safe="-._~") if ord(c) < 128 else c for c in value)


def _escape_markdown(value: str) -> str:
    reserved = set("\\*_{}[]()#+-.!|><&") | {chr(96)}
    return "".join(f"\\{char}" if char in reserved else char for char in value)


def _entry_block(entry, successors: dict[str, list[str]]) -> list[str]:
    data = entry.data
    entry_id = entry.document_id
    anchor = html.escape(entry_id.lower(), quote=True)
    lines = [f'<a id="{anchor}"></a>', f"### {_escape_markdown(data['topic'])}"]
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
        lines.append(f"- 訂正元: [{previous}](#{_fragment(previous.lower())})")
    for replacement in successors[entry_id]:
        lines.append(f"- 訂正先: [{replacement}](#{_fragment(replacement.lower())})")
    lines.append("")
    for key, label in (
        ("background", "背景"), ("recommendation", "推奨"),
        ("recommendation_reason", "推奨理由"), ("uncertainty", "不確実性"),
        ("owner_verbatim", "オーナー逐語"), ("inferred_reason", "推論"),
    ):
        narrative = _escape_markdown(data["narrative"][key]).replace("\n", " ")
        lines.append(f"- {label}: {narrative}".rstrip())
    return lines
