"""FND 辺逆転（v2）: forward 削除＋backward 付与＋DD-3 本文記録＋z バンプ＋git mv。

CLAUDE.md / DD-3 / DD-16 / FORMAT.md §status 遷移 を v2 レイアウトで機械化する:
  1. FND サイドカーの forward 辺（FND→対象）を ``edges: []`` にし、``version`` を z バンプ。
  2. 各処置対象（通常ノード）のサイドカーへ backward 辺 ``対象→FND``（ref=FND の x.y）を付与し z バンプ。
  3. provenance（FND/DD/Q/PEND 宛）は backref を張らず本文記録のみ。削除済み対象は「付与先なし」を記録。
  4. DD-3: 消える前に ``**指摘時 ref_version**:`` を FND 本文 ``.md`` へ凍結記録。
  5. FND の md/yaml を ``fnd/open/`` → ``fnd/resolved/`` へ ``git mv``（id=slug 不変ゆえ参照は壊れない）。

計画（plan）→適用（apply）の2フェーズ。既定 dry-run（差分表示のみ）。冪等: 対象に既に ``→FND`` が
あれば付与・z バンプをスキップする。

依存仕様: doc-system-v2/FORMAT.md（§status 遷移・§edges・§版）・config.yml（fnd_lifecycle）。
  DD-3（指摘時 ref_version 本文凍結）・DD-16（FND ライフサイクル）・DD-8（backref/lifecycle＝z バンプ）。
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path

from . import yamledit
from .gitutil import git_mv
from .meta import index_by_id
from .query import _xy

PROVENANCE_TYPES = {"fnd", "dd", "q", "pend"}
DD3_MARKER = "**指摘時 ref_version**:"


class ReverseError(ValueError):
    """辺逆転の前提が満たされないとき送出する。"""


@dataclass(frozen=True)
class TargetAction:
    to: str
    ref_version: str
    kind: str  # "normal" | "provenance" | "missing"
    yaml_path: str | None
    skipped_idempotent: bool = False


@dataclass
class ReversePlan:
    fnd_id: str
    fnd_yaml: str
    fnd_md: str
    fnd_yaml_new: str  # resolved/ 側の相対パス
    fnd_md_new: str
    actions: list[TargetAction] = field(default_factory=list)
    dd3_line: str = ""
    notarget_line: str = ""
    notes: list[str] = field(default_factory=list)
    noop: bool = False
    # 相対パス -> 適用後テキスト（内容変更分のみ。移動のみのファイルは含まない）
    new_text: dict[str, str] = field(default_factory=dict)
    old_text: dict[str, str] = field(default_factory=dict)
    # (src_rel, dst_rel) の移動ペア（FND md/yaml）
    moves: list[tuple[str, str]] = field(default_factory=list)

    def diff(self) -> str:
        chunks: list[str] = []
        for rel in sorted(self.new_text):
            old = self.old_text[rel].splitlines(keepends=True)
            new = self.new_text[rel].splitlines(keepends=True)
            chunks.extend(difflib.unified_diff(old, new, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
        return "".join(chunks)


def _read_lines(root: Path, rel: str) -> tuple[list[str], str]:
    text = (root / rel).read_text(encoding="utf-8")
    return text.splitlines(), ("\n" if text.endswith("\n") else "")


def _record(plan: ReversePlan, root: Path, rel: str, new_lines: list[str], trailing: str) -> None:
    orig = (root / rel).read_text(encoding="utf-8")
    plan.old_text[rel] = orig
    plan.new_text[rel] = "\n".join(new_lines) + trailing


def plan_reverse(root: Path, meta: dict, fnd_id: str) -> ReversePlan:
    by_id = index_by_id(meta)
    node = by_id.get(fnd_id)
    if node is None:
        raise ReverseError(f"{fnd_id}: ノードが見つからない")
    if node["type"] != "fnd":
        raise ReverseError(f"{fnd_id}: 型が fnd でない（type={node['type']!r}）")
    if node.get("status") == "resolved":
        raise ReverseError(f"{fnd_id}: 既に resolved（fnd/resolved/ 配下）")

    fnd_yaml = node["yaml_path"]
    fnd_md = node["body_path"]
    new_yaml = fnd_yaml.replace("/fnd/open/", "/fnd/resolved/")
    new_md = fnd_md.replace("/fnd/open/", "/fnd/resolved/")
    plan = ReversePlan(fnd_id=fnd_id, fnd_yaml=fnd_yaml, fnd_md=fnd_md,
                       fnd_yaml_new=new_yaml, fnd_md_new=new_md)

    forward = node["edges"]
    if not forward:
        plan.noop = True
        plan.notes.append(f"{fnd_id}: forward 辺が無いため逆転対象なし。")
        return plan

    fnd_xy = _xy(node["version"])
    dd3_parts: list[str] = []

    for e in forward:
        to = e["to"]
        ref = e.get("ref_version", "")
        target = by_id.get(to)
        if target is None:
            plan.actions.append(TargetAction(to, ref, "missing", None))
            dd3_parts.append(f'{to} "{ref}"（v{ref} 時点・当該ノードはその後削除済み）')
            plan.notes.append(f"{fnd_id}→{to}: 対象が存在しない（付与先なし）。本文記録のみ。")
            continue
        if target["type"] in PROVENANCE_TYPES:
            plan.actions.append(TargetAction(to, ref, "provenance", target["yaml_path"]))
            dd3_parts.append(f'{to} "{ref}"（{target["yaml_path"]} v{ref} 時点・provenance）')
            continue
        # 通常対象: backward 辺付与＋z バンプ（冪等）
        t_lines, t_trail = _read_lines(root, target["yaml_path"])
        new_lines, skipped = yamledit.add_edge(t_lines, fnd_id, fnd_xy)
        if not skipped:
            new_lines = yamledit.bump_version_z(new_lines)
            _record(plan, root, target["yaml_path"], new_lines, t_trail)
        else:
            plan.notes.append(f"{fnd_id}→{to}: 既に →{fnd_id} backref あり。付与省略（冪等）。")
        plan.actions.append(
            TargetAction(to, ref, "normal", target["yaml_path"], skipped))
        dd3_parts.append(f'{to} "{ref}"（{target["yaml_path"]} v{ref} 時点）')

    plan.dd3_line = f"{DD3_MARKER} " + "／".join(dd3_parts)
    plan.notarget_line = _notarget_line(plan.actions)

    # --- FND サイドカー: edges→[] + version z バンプ ---
    f_lines, f_trail = _read_lines(root, fnd_yaml)
    f_lines = yamledit.set_edges_empty(f_lines)
    f_lines = yamledit.bump_version_z(f_lines)
    # 内容変更は resolved/ 側の new パスに記録（move 後に書く）
    plan.old_text[fnd_yaml] = (root / fnd_yaml).read_text(encoding="utf-8")
    plan.new_text[fnd_yaml] = "\n".join(f_lines) + f_trail

    # --- FND 本文: DD-3 / 付与先なし を追記 ---
    md_lines, md_trail = _read_lines(root, fnd_md)
    md_lines = _append_body_records(md_lines, plan.dd3_line, plan.notarget_line)
    plan.old_text[fnd_md] = (root / fnd_md).read_text(encoding="utf-8")
    plan.new_text[fnd_md] = "\n".join(md_lines) + md_trail

    plan.moves = [(fnd_yaml, new_yaml), (fnd_md, new_md)]
    return plan


def _notarget_line(actions: list[TargetAction]) -> str:
    missing = [a.to for a in actions if a.kind == "missing"]
    provenance = [a.to for a in actions if a.kind == "provenance"]
    has_normal = any(a.kind == "normal" for a in actions)
    segs: list[str] = []
    if missing:
        segs.append(f"{'・'.join(missing)}（削除済みのため付与先ノードなし）")
    if not has_normal and provenance:
        segs.append(f"{'・'.join(provenance)}（provenance のため backref 非付与）")
    if not segs:
        return ""
    return "**付与先なし**: " + "／".join(segs)


def _append_body_records(lines: list[str], dd3_line: str, notarget_line: str) -> list[str]:
    """DD-3 行・付与先なし行を本文末尾へ冪等追記する（既存 DD-3 は上書きしない＝PR8）。"""
    body = "\n".join(lines)
    append: list[str] = []
    if not any(ln.lstrip().startswith(DD3_MARKER) for ln in lines):
        append.append(dd3_line)
    if notarget_line and "付与先なし" not in body:
        append.append(notarget_line)
    if not append:
        return list(lines)
    out = list(lines)
    while out and out[-1].strip() == "":
        out.pop()
    return out + ["", *append]


def apply_reverse(root: Path, plan: ReversePlan) -> None:
    """計画を正本へ適用する（対象 yaml 書込 → FND を git mv → 移動後に FND 内容を書込）。"""
    if plan.noop:
        return
    # 1. 通常対象サイドカー（移動しない）
    for rel, text in plan.new_text.items():
        if rel in (plan.fnd_yaml, plan.fnd_md):
            continue
        (root / rel).write_text(text, encoding="utf-8")
    # 2. FND md/yaml を open → resolved へ git mv
    for src, dst in plan.moves:
        git_mv(root, src, dst)
    # 3. 移動後の new パスへ FND 内容を書込
    (root / plan.fnd_yaml_new).write_text(plan.new_text[plan.fnd_yaml], encoding="utf-8")
    (root / plan.fnd_md_new).write_text(plan.new_text[plan.fnd_md], encoding="utf-8")
