"""Render repository-configured provenance links and historical anchor aliases."""

import html
import json
import os
from pathlib import Path
from urllib.parse import quote


def _repository_file(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"render の参照先がリポジトリ内のファイルではない: {name}")
    return path


def history_lines(store) -> list[str]:
    config_path = Path(store.root) / ".ai/feedback/render.json"
    if not config_path.exists():
        return []
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if set(config) != {"output", "history", "migration"}:
        raise ValueError("render設定のキーが契約と一致しない")
    root = Path(store.root)
    output = (root / config["output"]).resolve()
    if not output.is_relative_to(root.resolve()):
        raise ValueError("render出力の配置先がリポジトリ外")
    history = _repository_file(root, config["history"])
    migration = _repository_file(root, config["migration"])
    items = json.loads(migration.read_text(encoding="utf-8"))["items"]
    relative_history = quote(os.path.relpath(history, output.parent))
    relative_migration = quote(os.path.relpath(migration, output.parent))
    lines = [
        "このビューは `python3 -m feedback_ledger render` の生成物です。",
        f"[移行前の原文・実測・未決事項（史料）]({relative_history}) / "
        f"[全項目の移行対応表]({relative_migration})。",
        "史料の当時の生存・無効表示は現行の判断状態を表しません。", "",
        "## 旧参照の移行先", "",
    ]
    current_ids = store.ids("ledger")
    aliases = set()
    for item in items:
        old_anchor, entry_id = item["old_anchor"], item["entry_id"]
        if not isinstance(old_anchor, str) or not isinstance(entry_id, str):
            raise ValueError("移行元アンカーと台帳IDは文字列が必須")
        if old_anchor in aliases or not old_anchor.startswith("fbk-"):
            raise ValueError(f"旧アンカーが重複または不正: {old_anchor}")
        aliases.add(old_anchor)
        if entry_id not in current_ids:
            raise ValueError(f"移行先の台帳エントリが存在しない: {entry_id}")
        if old_anchor != entry_id.lower():
            lines.append(f'<a id="{html.escape(old_anchor, quote=True)}"></a>')
            lines.append(
                f"- 旧 `{html.escape(item['old_id'])}` → "
                f"[{entry_id}](#{quote(entry_id.lower())}) / "
                f"[原文]({relative_history}#{quote(old_anchor)})"
            )
    lines.append("")
    return lines
