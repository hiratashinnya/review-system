"""slug 改題（v2）: yaml と同名本文の改名＋全 referrer の ``edges[].to`` 一括張替え。

改題（title 変更で slug が変わる）は稀だが、起きた場合に参照の一貫性を機械的に保つ。referrer は
meta.json から逆引きする。既定 dry-run。

依存仕様: doc-system-v2/FORMAT.md（§id/slug・改題は rename が全 referrer の to を meta.json 経由で
  一括張替え）・slugify.py（唯一の正規化実装）。
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path

from . import yamledit
from .gitutil import git_mv
from .meta import index_by_id


class RenameError(ValueError):
    """改名の前提が満たされないとき送出する。"""


@dataclass
class RenamePlan:
    old: str
    new: str
    moves: list[tuple[str, str]] = field(default_factory=list)  # (src_rel, dst_rel)
    referrers: list[str] = field(default_factory=list)  # 変更する referrer の yaml_path
    new_text: dict[str, str] = field(default_factory=dict)
    old_text: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def diff(self) -> str:
        chunks: list[str] = []
        for rel in sorted(self.new_text):
            old = self.old_text[rel].splitlines(keepends=True)
            new = self.new_text[rel].splitlines(keepends=True)
            chunks.extend(difflib.unified_diff(old, new, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
        return "".join(chunks)


def _rename_path(rel: str, new_stem: str) -> str:
    p = Path(rel)
    return str(p.with_name(new_stem + p.suffix)).replace("\\", "/")


def plan_rename(root: Path, meta: dict, old: str, new: str) -> RenamePlan:
    by_id = index_by_id(meta)
    node = by_id.get(old)
    if node is None:
        raise RenameError(f"{old}: ノードが見つからない")
    if new == old:
        raise RenameError("old と new が同一")
    if new in by_id:
        raise RenameError(f"{new}: 改名先 slug が既に存在する（衝突）")

    plan = RenamePlan(old=old, new=new)
    plan.moves = [(node["yaml_path"], _rename_path(node["yaml_path"], new))]
    same_stem_body = node.get("body_path") == _rename_path(node["yaml_path"], old).replace(".yaml", ".md")
    if same_stem_body:
        plan.moves.append((node["body_path"], _rename_path(node["body_path"], new)))

    for src in meta["nodes"]:
        if not any(e["to"] == old for e in src["edges"]):
            continue
        text = (root / src["yaml_path"]).read_text(encoding="utf-8")
        trailing = "\n" if text.endswith("\n") else ""
        new_lines, changed = yamledit.retarget_edges(text.splitlines(), old, new)
        if changed:
            plan.referrers.append(src["yaml_path"])
            plan.old_text[src["yaml_path"]] = text
            plan.new_text[src["yaml_path"]] = "\n".join(new_lines) + trailing

    if not plan.referrers:
        plan.notes.append(f"{old}: referrer なし（ファイル改名のみ）。")
    return plan


def apply_rename(root: Path, plan: RenamePlan) -> None:
    """referrer の to 張替えを書込み、対象 yaml と同名本文があれば git mv する。"""
    for rel, text in plan.new_text.items():
        (root / rel).write_text(text, encoding="utf-8")
    for src, dst in plan.moves:
        git_mv(root, src, dst)
