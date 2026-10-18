"""台帳エントリの生存・訂正関係を都度導出して Markdown に描画する。"""

from __future__ import annotations

from . import schema as schema_module
from .store import Store
from .render_entry import _entry_block, _escape_markdown, _fragment
from .render_history import history_lines


class RenderError(ValueError):
    """台帳の置換関係を一意に描画できない。"""


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
    lines = ["# オーナー決定台帳", "", "## 生存決定一覧", ""]
    try:
        history = history_lines(store)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise RenderError(str(exc)) from exc
    themes = sorted({entry.data.get("theme", "なし") for entry in living})
    for theme in themes:
        lines.extend((f"### {theme}", ""))
        lines.extend(
            f"- [{_escape_markdown(entry.data['topic'])}](#{_fragment(entry.document_id.lower())}) "
            f"({entry.document_id}; テーマ: {entry.data.get('theme', 'なし')}) "
            f"— {entry.data['occurred_at'].isoformat()}"
            + ("・暫定" if entry.data["narrative"]["uncertainty"].startswith("暫定。") else "")
            for entry in reversed(living) if entry.data.get("theme", "なし") == theme
        )
        lines.append("")
    if not living:
        lines.append("- 該当なし")
    lines.extend(("", "## 生存する決定", ""))
    for entry in reversed(living):
        lines.extend(_entry_block(entry, successors))
    lines.extend(("## 訂正済みの決定", ""))
    for entry in corrected:
        lines.extend(_entry_block(entry, successors))
    lines.extend(history)
    return "\n".join(lines).rstrip() + "\n"
