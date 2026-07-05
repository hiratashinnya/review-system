"""FND 辺逆転の計画（plan）と適用（apply）。

CLAUDE.md L27–29 / DD-3 / DD-16 / DD-8 §4 の手順を機械化する:
  1. FND の forward 辺を削除し ``edges: []``・``resolved: true`` を付与（＋FND バッジ z バンプ）
  2. 各処置対象（通常ノード）に ``→FND-x`` backward 辺を付与（ref=FND の x.y）＋対象バッジ z バンプ
  3. provenance（FND/DD/Q/PEND 宛）は backref を張らず本文記録のみ
  4. 削除済み対象は「付与先なし」を本文記録
  5. DD-3: 消える前に ``**指摘時 ref_version**:`` を FND 本文へ凍結記録

2 フェーズ（plan→apply）で、全ファイルの変更をメモリ上に算出してから書く（途中失敗で部分破壊しない）。
冪等: 対象に既に ``→FND-x`` があれば付与・バッジ更新をスキップする。

依存仕様: DD-16 v0.1.0（FND ライフサイクル＝forward/backward 義務・provenance）・DD-3 v0.1.0（指摘時
  ref_version 本文凍結）・DD-8 v0.1.1／DD-21 v0.1.1（backref 追加＝z バンプ）・SPEC-1 v0.3.0／
  SPEC-1-1 v0.1.1／SPEC-2 v0.3.0（パース・docidx 再利用）。補助（out-of-graph・版なし）:
  config.yaml fnd_lifecycle・CLAUDE.md（バックリファレンス規約）。
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path

from docidx import scan
from docidx.model import NodeIndex

from . import edit, locate
from .edit import Edit
from .errors import BackrefError

# provenance 扱いする宛先型（backref を張らず本文記録のみ・DD-16）
PROVENANCE_TYPES = {"FND", "DD", "Q", "PEND"}

DD3_MARKER = "**指摘時 ref_version**:"


@dataclass(frozen=True)
class TargetAction:
    """forward 辺 1 本に対する処置。"""

    to: str
    ref_version: str  # forward 辺の ref_version（凍結記録する値）
    kind: str  # "normal" | "provenance" | "missing"
    target_file: str | None  # 通常/provenance のとき相対パス
    skipped_idempotent: bool = False  # 通常で既に backref があり付与省略


@dataclass
class FndPlan:
    """1 FND の辺逆転計画。"""

    fnd_id: str
    fnd_file: str
    actions: list[TargetAction] = field(default_factory=list)
    dd3_line: str = ""
    notarget_line: str = ""  # 付与先（backref 辺）が無いときの本文記録（空＝不要）
    revision_note: str = ""  # 推奨改訂理由（書込はせず提示する）
    notes: list[str] = field(default_factory=list)  # 警告/スキップ理由
    noop: bool = False  # 反転すべき forward 辺が無く何もしない
    # path(相対) -> 適用後テキスト
    new_text: dict[str, str] = field(default_factory=dict)
    # path(相対) -> 元テキスト（diff 用）
    old_text: dict[str, str] = field(default_factory=dict)

    def diff(self) -> str:
        chunks: list[str] = []
        for rel in sorted(self.new_text):
            old = self.old_text[rel].splitlines(keepends=True)
            new = self.new_text[rel].splitlines(keepends=True)
            chunks.extend(
                difflib.unified_diff(old, new, fromfile=f"a/{rel}", tofile=f"b/{rel}")
            )
        return "".join(chunks)


class _Planner:
    def __init__(self, index: NodeIndex, root: Path) -> None:
        self.index = index
        self.root = root
        self._cache: dict[str, list[str]] = {}
        self._edits: dict[str, list[Edit]] = {}

    def _lines(self, rel: str) -> list[str]:
        if rel not in self._cache:
            text = (self.root / rel).read_text(encoding="utf-8")
            self._cache[rel] = text.splitlines()
        return self._cache[rel]

    def _add_edit(self, rel: str, e: Edit) -> None:
        self._edits.setdefault(rel, []).append(e)

    def plan(self, fnd_id: str) -> FndPlan:
        node = self.index.by_id.get(fnd_id)
        if node is None:
            raise BackrefError(f"{fnd_id}: ノードが見つからない")
        if node.type != "FND":
            raise BackrefError(f"{fnd_id}: 型が FND でない（type={node.type!r}）")

        plan = FndPlan(fnd_id=fnd_id, fnd_file=node.file)
        resolved = node.fields.get("resolved") is True
        forward = list(node.edges)

        if not forward:
            plan.noop = True
            if resolved:
                plan.notes.append(f"{fnd_id}: 既に resolved・forward 辺なし（処置済み）。")
            else:
                plan.notes.append(f"{fnd_id}: forward 辺が無いため逆転対象なし。")
            return plan

        fnd_lines = self._lines(node.file)
        fnd_block = locate.find_yaml_block(fnd_lines, node.line - 1, fnd_id)
        fnd_xy = edit.xy(node.version)

        # --- 各 forward 辺を分類し、通常対象には backref を計画 ---
        dd3_parts: list[str] = []
        for e in forward:
            target = self.index.by_id.get(e.to)
            if target is None:
                plan.actions.append(
                    TargetAction(e.to, e.ref_version, "missing", None)
                )
                dd3_parts.append(
                    f'{e.to} "{e.ref_version}"（v{e.ref_version} 時点・当該ノードはその後削除済み）'
                )
                plan.notes.append(
                    f"{fnd_id}→{e.to}: 対象が存在しない（付与先なし）。本文に記録のみ。"
                )
                continue
            if target.type in PROVENANCE_TYPES:
                plan.actions.append(
                    TargetAction(e.to, e.ref_version, "provenance", target.file)
                )
                dd3_parts.append(
                    f'{e.to} "{e.ref_version}"（{target.file} v{e.ref_version} 時点・provenance）'
                )
                continue
            # 通常対象: backref 付与（冪等チェック）＋バッジ z バンプ
            skipped = self._plan_backref(target, fnd_id, fnd_xy)
            plan.actions.append(
                TargetAction(e.to, e.ref_version, "normal", target.file, skipped)
            )
            dd3_parts.append(
                f'{e.to} "{e.ref_version}"（{target.file} v{e.ref_version} 時点）'
            )
            if skipped:
                plan.notes.append(
                    f"{fnd_id}→{e.to}: 既に →{fnd_id} backref あり。付与省略（冪等）。"
                )

        # --- FND 側: edges→[] + resolved:true + バッジ z + DD-3／付与先なし 本文 ---
        plan.dd3_line = f"{DD3_MARKER} " + "／".join(dd3_parts)
        plan.notarget_line = self._notarget_line(plan.actions)
        self._plan_fnd_yaml(fnd_lines, fnd_block, fnd_id)
        self._plan_fnd_badge(fnd_lines, fnd_block)
        body_note = self._plan_body_records(
            fnd_lines, node.line - 1, plan.dd3_line, plan.notarget_line)
        if body_note:
            plan.notes.append(body_note)
        plan.revision_note = (
            f"**改訂理由（z バンプ・DD-16 辺逆転完了。辺逆転は downstream 無影響の "
            f"provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠）**: "
            f"forward 辺を削除し edges: []・resolved: true を付与。指摘時 ref_version は本文に記録（DD-3）。"
        )

        self._materialize(plan)
        return plan

    def _plan_backref(self, target, fnd_id: str, fnd_xy: str) -> bool:
        """通常対象へ ``→FND-x`` を付与する編集を計画。既存なら True（スキップ）を返す。"""
        tlines = self._lines(target.file)
        tblock = locate.find_yaml_block(tlines, target.line - 1, target.id)
        tspan = locate.find_edges_span(tlines, tblock)
        if tspan is None:
            raise BackrefError(
                f"{target.id}: edges: が無く backref を付与できない（想定外）"
            )
        if fnd_id in locate.edge_targets(tlines, tspan):
            return True  # 冪等: 既に付与済み
        if tspan.inline and not tspan.inline_empty:
            # 非空 inline ``edges: [..]`` は、行全体を block 形へ置換すると既存辺を黙って捨てる。
            # 現コーパスは block 形のみだが、保証の穴を塞ぐため fail-close で停止する。
            raise BackrefError(
                f"{target.id}: 非空 inline edges（`{tlines[tspan.start].strip()}`）への backref 付与は未対応。"
                "block 形（`edges:` ＋ `- to:`）へ直してから再実行すること"
            )
        indent = len(tlines[tspan.start]) - len(tlines[tspan.start].lstrip(" "))
        if tspan.inline:
            # ``edges: []`` を block 形へ変換して 1 項目を持たせる
            new = [f"{' ' * indent}edges:"] + edit.render_edge_entry(fnd_id, fnd_xy)
            self._add_edit(
                target.file,
                Edit(tspan.start, tspan.end, new, f"{target.id}: edges[] → backref"),
            )
        else:
            entry = edit.render_edge_entry(fnd_id, fnd_xy, tspan.entry_indent)
            # 末尾 entry の直後に挿入（範囲 [end+1, end] の空置換）
            self._add_edit(
                target.file,
                Edit(tspan.end + 1, tspan.end, entry, f"{target.id}: append backref"),
            )
        # 対象バッジ z バンプ
        self._add_edit(
            target.file,
            Edit(
                tblock.summary_idx,
                tblock.summary_idx,
                [edit.bump_summary_z(tlines[tblock.summary_idx])],
                f"{target.id}: badge z bump",
            ),
        )
        return False

    def _plan_fnd_yaml(self, lines, block, fnd_id: str) -> None:
        span = locate.find_edges_span(lines, block)
        if span is None:
            raise BackrefError(f"{fnd_id}: edges: が無い（想定外）")
        indent = len(lines[span.start]) - len(lines[span.start].lstrip(" "))
        pad = " " * indent
        resolved_idx = locate.find_key_line(lines, block, "resolved")
        if resolved_idx is None:
            # resolved 行が無い → edges 直前に resolved: true を差し込む（同一 edit で）
            self._add_edit(
                self._rel_of(lines),
                Edit(span.start, span.end, [f"{pad}resolved: true", f"{pad}edges: []"],
                     f"{fnd_id}: resolved+edges[]"),
            )
        else:
            self._add_edit(
                self._rel_of(lines),
                Edit(span.start, span.end, [f"{pad}edges: []"], f"{fnd_id}: edges[]"),
            )
            self._add_edit(
                self._rel_of(lines),
                Edit(resolved_idx, resolved_idx,
                     [edit.set_resolved_true_line(lines[resolved_idx])],
                     f"{fnd_id}: resolved=true"),
            )

    def _plan_fnd_badge(self, lines, block) -> None:
        self._add_edit(
            self._rel_of(lines),
            Edit(block.summary_idx, block.summary_idx,
                 [edit.bump_summary_z(lines[block.summary_idx])], "FND badge z bump"),
        )

    @staticmethod
    def _notarget_line(actions: list[TargetAction]) -> str:
        """backref の付与先が無い対象（削除済み／全 provenance）の本文記録行を組み立てる。

        CLAUDE.md L28・README「削除済みノードは FND 本文に『付与先なし』と明記」を満たす。
        付与先が一つでも残る通常対象があり、かつ削除済みも無ければ空文字（記録不要）。
        """
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

    def _plan_body_records(self, lines, summary_idx: int, dd3_line: str,
                           notarget_line: str) -> str | None:
        """DD-3 ``指摘時 ref_version`` 行と「付与先なし」行を本文へ記録する編集を計画。

        **既存の DD-3 行は上書きしない**（PR8「消さない」。人手の凍結記録を破壊しないため）。
        既存があり内容が辺由来と食い違う場合は警告メッセージを返し、人手の照合に委ねる。
        付与先なし行も既に本文にあれば再挿入しない（冪等）。新規分のみ本文末尾へ一括挿入する。
        """
        region = locate.find_body_region(lines, summary_idx)
        rel = self._rel_of(lines)
        body = "\n".join(lines[region.start : region.end + 1]) if region.end >= region.start else ""
        warn: str | None = None
        append: list[str] = []

        existing_dd3 = next(
            (lines[i].strip() for i in range(region.start, region.end + 1)
             if lines[i].lstrip().startswith(DD3_MARKER)),
            None,
        )
        if existing_dd3 is None:
            append.append(dd3_line)
        elif existing_dd3 != dd3_line:
            warn = (
                "本文に既存の DD-3 行があるため上書きしません（PR8）。辺由来と食い違うため"
                "人手で照合してください。\n"
                f"    既存 : {existing_dd3}\n"
                f"    辺由来: {dd3_line}"
            )

        if notarget_line and "付与先なし" not in body:
            append.append(notarget_line)

        if append:
            last = region.end
            while last >= region.start and lines[last].strip() == "":
                last -= 1
            insert_at = last + 1
            new = (["", *append]) if last >= region.start else list(append)
            self._add_edit(rel, Edit(insert_at, insert_at - 1, new, "body records insert"))
        return warn

    def _rel_of(self, lines: list[str]) -> str:
        for rel, cached in self._cache.items():
            if cached is lines:
                return rel
        raise BackrefError("内部エラー: 行配列の相対パスを解決できない")

    def _materialize(self, plan: FndPlan) -> None:
        for rel, edits in self._edits.items():
            old = "\n".join(self._cache[rel])
            # 末尾改行を元ファイルに合わせる
            orig = (self.root / rel).read_text(encoding="utf-8")
            trailing = "\n" if orig.endswith("\n") else ""
            new_lines = edit.apply_edits(self._cache[rel], edits)
            plan.old_text[rel] = orig
            plan.new_text[rel] = "\n".join(new_lines) + trailing


def build_index(root: Path | None, config: Path | None) -> tuple[NodeIndex, Path]:
    r = root or scan.find_repo_root()
    index = scan.build_index(repo_root=r, config_path=config)
    return index, r


def plan_reverse(index: NodeIndex, root: Path, fnd_id: str) -> FndPlan:
    return _Planner(index, root).plan(fnd_id)


def write_plan(plan: FndPlan, root: Path) -> None:
    """計画済みの新テキストを各ファイルへ書き込む。"""
    for rel, text in plan.new_text.items():
        (root / rel).write_text(text, encoding="utf-8")
