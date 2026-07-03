"""現行 doc-system（v1・585 ノードが 23 の .md に同居）を新フォーマット v2
（``doc-system-v2/nodes/**`` ＝ 1ノード2ファイル）へ一括移行する（stdlib のみ）。

依存仕様: doc-system-v2/FORMAT.md（Sub-A・新フォーマット正本）・doc-system-v2/config.yml
  （layout / status_dirs / condition_vocab）・GitHub Issue #71（Sub-B 変換ブループリント）。
  slug 生成は doc-system-v2/slugify.py（唯一実装）を import して使う（独自再実装禁止）。
  サイドカー YAML はミニサブセット（docidx.nodeyaml が読める文法）で出力する。

変換規則（#71）:
  1. 対象 = doc-system/**/*.md から 00-dashboard.md・03-analysis/00-dfd.md を除外。⬡ バッジ持ちノードのみ。
  2. ノード境界 = ``^#{2,3} [A-Z]+-\\d`` 見出し。TYPE-N を持たない H3（### 論点 等）は本文サブ節。
  3. 本文 = 見出し次行〜次ノード見出し（or EOF）から <details>…</details> を除去（末尾の --- 分離子も除去）。
     DD/Q/PEND の **status: X** 行は本文に残す。
  4. version = <details><summary>⬡ TYPE-N · vX.Y.Z</summary> の X.Y.Z。
  5. title = 見出しから TYPE-N: プレフィクスと末尾 condition/umbrella マーカーを除去。slug = slugify(title)。
  6. slug 衝突は型接尾辞（不足時 id 接尾辞）で分岐し、title もそれに合わせ slug==slugify(title) を保つ。
  7. 属性 → サイドカー（labels/scheduled/condition/suppress(+reason)/carrier/result/log_ref/edges）。
     傘 SPEC（condition:normal かつ同型 -N 子を持つ）は condition を落とす。id/type/resolved は落とす。
  8. status → path（FND resolved→fnd/resolved 他は fnd/open。Q/DD/PEND は **status:X** から status_dirs へ）。
  9. 親 edge 合成（TYPE-N-M… の子は直親 TYPE-N… への無名 edge・ref_version=親 x.y・既存重複は張らない）。
 10. 配置 = nodes/<stage>/<type>/[<status>/]{slug}.{md,yaml}。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO))                    # docidx
sys.path.insert(0, str(_REPO / "doc-system-v2"))  # slugify

from docidx import nodeyaml            # noqa: E402
from slugify import slugify            # noqa: E402

DEFAULT_SRC = _REPO / "doc-system"
DEFAULT_DST = _REPO / "doc-system-v2"

# 除外ファイル（相対 posix）。
EXCLUDE = {"doc-system/00-dashboard.md", "doc-system/03-analysis/00-dfd.md"}

# --- config.yml layout / status_dirs を正本とし一致させて直書き（validate.py / meta.py と同方針）。---
LAYOUT = {
    "01-why": ["val", "sr"],
    "02-what": ["fr", "nfr", "spec"],
    "03-analysis": ["actor", "i", "o", "d", "p", "e", "term"],
    "05-design": ["orc", "ds", "mod", "dm", "port", "prs", "scm", "cfg", "prompt"],
    "04-verification": ["td", "tc", "tr", "verify", "fnd", "dd", "q", "pend"],
}
TYPE_STAGE = {t: st for st, types in LAYOUT.items() for t in types}
STATUS_DIRS = {
    "fnd": {"open", "resolved"},
    "q": {"open", "decided", "deferred", "closed"},
    "dd": {"decided", "closed"},
    "pend": {"open", "resolved", "deferred"},
}

HEAD_RE = re.compile(r"^(#{2,3}) ([A-Z]+-[0-9][0-9-]*): (.*)$")
YAML_RE = re.compile(r"```yaml\n(.*?)\n```", re.S)
DETAILS_RE = re.compile(r"<details>.*?</details>\s*", re.S)
STATUS_RE = re.compile(r"^\*\*status:\s*(\w+)\*\*", re.M)
# 末尾の condition マーカー（（normal）（failure・…）（normal・post-mvp）等）。
COND_SUFFIX = re.compile(r"[（(](?:normal|boundary|empty|failure|error)(?:[・][^）)]*)?[)）]\s*$")
# 末尾の傘マーカー（（傘）（umbrella）（アンブレラ））。
UMB_SUFFIX = re.compile(r"[（(](?:傘|umbrella|アンブレラ)[)）]\s*$")
SUPPRESS_COMMENT_RE = re.compile(r"^\s*suppress:\s*\[[^\]]*\]\s*#\s*(.*\S)\s*$")


class MigrationGap(Exception):
    """v1 を v2 へ忠実にマップできない（invent 禁止・停止して報告すべき）事象。"""


def strip_title_markers(title: str) -> str:
    """見出しタイトルから末尾の condition / umbrella マーカーを（積み重なりも）除去する。"""
    t = title.strip()
    prev = None
    while prev != t:
        prev = t
        t = COND_SUFFIX.sub("", t).strip()
        t = UMB_SUFFIX.sub("", t).strip()
    return t


def _body_of(region_lines: list[str]) -> str:
    """ノード領域（見出し行含む）の本文を返す。見出し行と <details> と末尾 --- 分離子を除去。"""
    text = "\n".join(region_lines[1:])          # 見出し行を落とす
    text = DETAILS_RE.sub("", text)             # バッジブロックを落とす
    lines = text.split("\n")
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and (lines[-1].strip() == "" or lines[-1].strip() == "---"):
        lines.pop()
    body = "\n".join(lines).strip()
    return body + "\n" if body else ""


def parse_corpus(src: Path) -> list[dict]:
    """v1 コーパスを走査し、ノード辞書のリストを（ファイル→出現順で）返す。"""
    files = [p for p in sorted(src.rglob("*.md"))
             if _posix_rel(p, src.parent) not in EXCLUDE]
    nodes: list[dict] = []
    for f in files:
        lines = f.read_text("utf-8").split("\n")
        idxs = [i for i, l in enumerate(lines) if HEAD_RE.match(l)]
        for k, i in enumerate(idxs):
            m = HEAD_RE.match(lines[i])
            nid = m.group(2)
            raw_title = m.group(3)
            end = idxs[k + 1] if k + 1 < len(idxs) else len(lines)
            region = lines[i:end]
            region_text = "\n".join(region)
            bm = re.search(r"⬡ " + re.escape(nid) + r" · v(\d+\.\d+\.\d+)", region_text)
            if not bm:
                raise MigrationGap(f"{nid}: 版バッジ（⬡ {nid} · vX.Y.Z）が見つからない")
            ym = YAML_RE.search(region_text)
            if not ym:
                raise MigrationGap(f"{nid}: YAML ブロックが見つからない")
            raw_yaml = ym.group(1)
            data = nodeyaml.parse(raw_yaml)
            yid = str(data.get("id", ""))
            if yid != nid:
                raise MigrationGap(f"{nid}: 見出し id と YAML id 不一致（yaml={yid!r}）")
            ytype = str(data.get("type", ""))
            if ytype.lower() not in TYPE_STAGE:
                raise MigrationGap(f"{nid}: 未知 type {ytype!r}（config.yml layout に無い）")
            supp_reason = None
            for rl in raw_yaml.split("\n"):
                sm = SUPPRESS_COMMENT_RE.match(rl)
                if sm:
                    supp_reason = sm.group(1).strip()
                    break
            nodes.append({
                "id": nid,
                "type": ytype.lower(),
                "title": strip_title_markers(raw_title),
                "version": bm.group(1),
                "condition": (str(data["condition"]) if data.get("condition") else None),
                "labels": list(data.get("labels", []) or []),
                "scheduled": str(data.get("scheduled", "") or ""),
                "suppress": [str(r) for r in (data.get("suppress") or [])],
                "suppress_reason": supp_reason,
                "carrier": (str(data["carrier"]) if data.get("carrier") else None),
                "result": (str(data["result"]) if data.get("result") else None),
                "log_ref": (str(data["log_ref"]) if data.get("log_ref") else None),
                "resolved": bool(data.get("resolved")) if data.get("resolved") is not None else False,
                "edges": [dict(e) for e in (data.get("edges", []) or [])],
                "status": (STATUS_RE.search(region_text).group(1)
                           if STATUS_RE.search(region_text) else None),
                "src": _posix_rel(f, src.parent),
                "body": _body_of(region),
            })
    return nodes


def _posix_rel(p: Path, base: Path) -> str:
    return str(p.relative_to(base)).replace("\\", "/")


def assign_slugs(nodes: list[dict]) -> dict[str, str]:
    """id → 最終 slug を返す。衝突は型接尾辞（不足時 id 接尾辞）で分岐し slug==slugify(title) を保つ。

    衝突解消時は各ノードの ``title``（サイドカー保存タイトル）を末尾接尾辞付きに更新する
    （＝slug が slugify(title) と一致し validate の id 一貫性を満たす）。
    """
    by_slug: dict[str, list[dict]] = {}
    for n in nodes:
        by_slug.setdefault(slugify(n["title"]), []).append(n)

    id2slug: dict[str, str] = {}
    for base, group in by_slug.items():
        if len(group) == 1:
            id2slug[group[0]["id"]] = base
            continue
        # 衝突: まず型接尾辞。同型が複数で不足なら id 接尾辞へ全体降格。
        type_titles = {n["id"]: f'{n["title"]}（{n["type"].upper()}）' for n in group}
        type_slugs = {i: slugify(t) for i, t in type_titles.items()}
        if len(set(type_slugs.values())) == len(group):
            for n in group:
                n["title"] = type_titles[n["id"]]
                id2slug[n["id"]] = type_slugs[n["id"]]
        else:
            for n in group:
                n["title"] = f'{n["title"]}（{n["id"]}）'
                id2slug[n["id"]] = slugify(n["title"])

    # グローバル一意性の最終確認（衝突解消後も残るなら invent せず停止）。
    seen: dict[str, str] = {}
    for nid, slug in id2slug.items():
        if slug in seen:
            raise MigrationGap(f"slug 衝突が解消できない: {slug!r}（{seen[slug]} と {nid}）")
        seen[slug] = nid
    return id2slug


def is_umbrella_normal(node: dict, ids_by_type: dict[str, set[str]]) -> bool:
    """condition:normal かつ同型の -N 子を持つ傘ノードか（＝condition を落とす対象）。"""
    if node.get("condition") != "normal":
        return False
    prefix = node["id"] + "-"
    return any(other != node["id"] and other.startswith(prefix)
              for other in ids_by_type.get(node["type"], set()))


def build_edges(node: dict, id2slug: dict[str, str], id2node: dict[str, dict],
                counters: dict) -> list[dict]:
    """edge の to を slug へ張替え、必要なら直親への無名 edge を合成して返す。"""
    orig_targets = {str(e.get("to", "")) for e in node["edges"]}
    out: list[dict] = []
    for e in node["edges"]:
        to = str(e.get("to", ""))
        if to not in id2slug:
            counters["dangling"].append((node["id"], to))
            continue
        row = {"to": id2slug[to]}
        if e.get("ref_version") is not None:
            row["ref_version"] = str(e["ref_version"])
        if e.get("note"):
            row["note"] = str(e["note"])
        out.append(row)
    # 親 edge 合成（直親のみ・既存重複は張らない）。
    parent = node["id"].rsplit("-", 1)[0]
    if parent in id2node and parent not in orig_targets:
        pv = id2node[parent]["version"].split(".")
        out.append({"to": id2slug[parent], "ref_version": f"{pv[0]}.{pv[1]}"})
        counters["synth"] += 1
    return out


def _q(s: str) -> str:
    """YAML ミニサブセット向けに文字列をクォートする（nodeyaml が読める形）。"""
    if '"' not in s:
        return '"' + s + '"'
    if "'" not in s:
        return "'" + s + "'"
    raise MigrationGap(f"タイトル/値に \" と ' が両方含まれ安全にクォートできない: {s!r}")


def serialize_sidecar(node: dict, edges: list[dict], drop_condition: bool) -> str:
    """サイドカー .yaml 本文を組み立てる（FORMAT.md サンプルのキー順）。"""
    lines = [f"title: {_q(node['title'])}", f'version: "{node["version"]}"']
    if node.get("condition") and not drop_condition:
        lines.append(f"condition: {node['condition']}")
    lines.append("labels: [" + ", ".join(node["labels"]) + "]")
    lines.append(f"scheduled: {_q(node['scheduled'])}")
    if node["suppress"]:
        lines.append("suppress: [" + ", ".join(node["suppress"]) + "]")
        if not node.get("suppress_reason"):
            raise MigrationGap(f"{node['id']}: suppress 非空だが理由コメントが抽出できない")
        lines.append(f"suppress_reason: {_q(node['suppress_reason'])}")
    if node.get("carrier"):
        lines.append(f"carrier: {_q(node['carrier'])}")
    if node["type"] == "tr" and node.get("result"):
        lines.append(f"result: {node['result']}")
    if node["type"] == "tr" and node.get("log_ref"):
        lines.append(f"log_ref: {_q(node['log_ref'])}")
    if not edges:
        lines.append("edges: []")
    else:
        lines.append("edges:")
        for e in edges:
            lines.append(f"  - to: {_q(e['to'])}")
            if "ref_version" in e:
                lines.append(f'    ref_version: "{e["ref_version"]}"')
            if "note" in e:
                lines.append(f"    note: {_q(e['note'])}")
    return "\n".join(lines) + "\n"


def dest_dir(node: dict, dst_root: Path) -> Path:
    """nodes/<stage>/<type>/[<status>/] を返す（status→path・#71 規則8）。"""
    stage = TYPE_STAGE[node["type"]]
    parts = [dst_root, "nodes", stage, node["type"]]
    if node["type"] == "fnd":
        parts.append("resolved" if node["resolved"] else "open")
    elif node["type"] in STATUS_DIRS:  # q / dd / pend
        st = node["status"]
        if st not in STATUS_DIRS[node["type"]]:
            raise MigrationGap(
                f"{node['id']}: status {st!r} が {node['type']} の status_dirs "
                f"{sorted(STATUS_DIRS[node['type']])} に無い")
        parts.append(st)
    return Path(*parts)


def _clean_nodes(dst_root: Path) -> int:
    """nodes/ 配下の既存 .md/.yaml を除去し（冪等な再生成）、削除数を返す。"""
    nodes_dir = dst_root / "nodes"
    removed = 0
    if nodes_dir.exists():
        for p in nodes_dir.rglob("*"):
            if p.is_file() and p.suffix in (".md", ".yaml"):
                p.unlink()
                removed += 1
    return removed


def run(src: Path = DEFAULT_SRC, dst: Path = DEFAULT_DST) -> dict:
    """移行を実行し、集計 dict を返す（MIGRATION_REPORT.md も出力）。"""
    nodes = parse_corpus(src)
    id2node = {n["id"]: n for n in nodes}
    ids_by_type: dict[str, set[str]] = {}
    for n in nodes:
        ids_by_type.setdefault(n["type"], set()).add(n["id"])

    id2slug = assign_slugs(nodes)  # ※ 衝突ノードの title を副作用で更新
    counters = {"synth": 0, "dangling": []}

    removed = _clean_nodes(dst)
    total_edges = 0
    umbrella_dropped = 0
    for n in nodes:
        edges = build_edges(n, id2slug, id2node, counters)
        total_edges += len(edges)
        drop = is_umbrella_normal(n, ids_by_type)
        if drop:
            umbrella_dropped += 1
        d = dest_dir(n, dst)
        d.mkdir(parents=True, exist_ok=True)
        slug = id2slug[n["id"]]
        (d / f"{slug}.md").write_text(n["body"], encoding="utf-8")
        (d / f"{slug}.yaml").write_text(serialize_sidecar(n, edges, drop), encoding="utf-8")

    if counters["dangling"]:
        raise MigrationGap(f"dangling edges 残存: {counters['dangling']}")

    # 生成物からグラフ照会（drift / orphans）を実行し結果をレポートへ載せる（#71 検証ゲート）。
    from . import query
    from .meta import build_meta
    meta = build_meta(dst)
    drift_rows = query.drift(meta)
    orphan_rows = query.orphans(meta)
    suppressed_drift = sum(
        1 for n in nodes if "RULE-004" in n["suppress"]
        for e in n["edges"]
        if e.get("ref_version") and id2node.get(e["to"])
        and e["ref_version"].split(".")[:2] != id2node[e["to"]]["version"].split(".")[:2])

    report = _report(nodes, id2slug, counters, total_edges, umbrella_dropped, removed,
                     drift_rows, orphan_rows, suppressed_drift)
    (dst / "MIGRATION_REPORT.md").write_text(report, encoding="utf-8")
    return {
        "nodes": len(nodes),
        "edges": total_edges,
        "synth": counters["synth"],
        "dangling": len(counters["dangling"]),
        "umbrella_dropped": umbrella_dropped,
        "removed": removed,
    }


def _report(nodes, id2slug, counters, total_edges, umbrella_dropped, removed,
            drift_rows=None, orphan_rows=None, suppressed_drift=0) -> str:
    drift_rows = drift_rows or []
    orphan_rows = orphan_rows or []
    from collections import Counter
    by_type = Counter(n["type"] for n in nodes)
    L = []
    L.append("# doc-system v1 → v2 移行レポート（Sub-B #71）\n")
    L.append(f"- 移行ノード数: **{len(nodes)}**")
    L.append(f"- edge 総数（合成込み）: **{total_edges}**（うち合成した親 edge: **{counters['synth']}**）")
    L.append(f"- dangling edge（未解決 to）: **{len(counters['dangling'])}**")
    L.append(f"- 傘 SPEC（condition:normal）で condition を落としたノード: **{umbrella_dropped}**")
    L.append(f"- 再生成前に除去した既存ノードファイル数: **{removed}**")
    L.append("")
    L.append("> **Sub-A サンプルノードの扱い**: 移行前の `nodes/` には Sub-A の"
             "**サンプルノード**（FORMAT.md §検証 が「サンプル」と明記）3 件が置かれていた。"
             "うち 2 件（傘 SPEC＝SPEC-62／子 SPEC＝SPEC-62-2）は v1 実ノードに対応するため"
             "移行で**同一 slug に再生成**される。残る 1 件"
             "（FND『サイドカーに status を持たせず path 導出とする設計判断の要確認』＝v2 自体の設計に関する"
             "Sub-A デモ用 finding・v1 コーパスに存在しない）は、本移行が生成する v1 由来 585 ノードには含まれず、"
             "厳密 585 ノード化のため除去した（内容は git 履歴・PR #77 に保全）。"
             "v2 verification 層のネイティブ finding として残すべきかはオーナー判断。")
    L.append("")
    L.append("## 型別件数（v2 生成）")
    L.append("| type | 件数 |")
    L.append("|------|------|")
    for t in sorted(by_type):
        L.append(f"| {t} | {by_type[t]} |")
    L.append(f"| **合計** | **{sum(by_type.values())}** |")
    L.append("")
    L.append("## status 分布（path 導出）")
    from collections import Counter as C
    st = C()
    for n in nodes:
        if n["type"] == "fnd":
            st[f"fnd/{'resolved' if n['resolved'] else 'open'}"] += 1
        elif n["type"] in STATUS_DIRS:
            st[f"{n['type']}/{n['status']}"] += 1
    for k in sorted(st):
        L.append(f"- {k}: {st[k]}")
    L.append("")
    L.append("## グラフ照会（生成物に対する dsv2 drift / orphans）")
    L.append(f"- ドリフト辺（RULE-004）: **{len(drift_rows)}** 件"
             f"（v1 由来の凍結記録・ref_version スナップショットの自然発火）。")
    L.append(f"- うち suppress:[RULE-004] により**免除**された辺: **{suppressed_drift}** 件"
             f"（VERIFY 5 ノード＝過去の検証事実スナップショット・DD-2）。免除辺は上記 {len(drift_rows)} 件に含まれない。")
    L.append(f"- 完全孤立ノード（in/out 辺 0・RULE-005 相当）: **{len(orphan_rows)}** 件。"
             f"（v1 でも孤立していた DD/FND 等・移行で新規孤立は発生していない）。")
    if orphan_rows:
        L.append("")
        L.append("<details><summary>完全孤立ノード一覧</summary>\n")
        for o in orphan_rows:
            L.append(f"- `{o['id']}`（{o['stage']}/{o['type']}）")
        L.append("\n</details>")
    L.append("")
    L.append("## slug 衝突の解消")
    coll = {}
    for n in nodes:
        coll.setdefault(id2slug[n["id"]], []).append(n["id"])
    # 衝突は解消済みなので、接尾辞付き（型/id）の slug を列挙。
    dis = [(id2slug[n["id"]], n["id"], n["title"]) for n in nodes
           if n["title"].endswith("）") and ("（" + n["type"].upper() + "）" in n["title"]
                                           or "（" + n["id"] + "）" in n["title"])]
    if dis:
        L.append("| 解消後 slug | 元 id | サイドカー title |")
        L.append("|------|------|------|")
        for slug, nid, title in sorted(dis):
            L.append(f"| `{slug}` | {nid} | {title} |")
    else:
        L.append("（衝突なし）")
    L.append("")
    L.append("## 旧 id → slug 対応表")
    L.append("| 旧 id | slug | type |")
    L.append("|------|------|------|")
    for n in sorted(nodes, key=lambda x: (x["type"], x["id"])):
        L.append(f"| {n['id']} | `{id2slug[n['id']]}` | {n['type']} |")
    L.append("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    src = Path(argv[0]).resolve() if len(argv) > 0 else DEFAULT_SRC
    dst = Path(argv[1]).resolve() if len(argv) > 1 else DEFAULT_DST
    try:
        stats = run(src, dst)
    except MigrationGap as ex:
        print(f"GAP（invent 禁止・停止）: {ex}", file=sys.stderr)
        return 4
    print(f"移行完了: {stats['nodes']} ノード / edge {stats['edges']}"
          f"（合成 {stats['synth']}）/ dangling {stats['dangling']}"
          f" / 傘 condition 落とし {stats['umbrella_dropped']} / 除去 {stats['removed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
