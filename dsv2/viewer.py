"""静的 HTML ビューア生成: meta.json ＋ 各ノードの ``.md`` 本文から単一 ``doc_view.html`` を出力する。

手書き HTML を持たず、``meta.json``（``dsv2 index`` の生成物）と本文 Markdown から**データ駆動で再生成**する
（Sub-F #75）。生成物は完全にオフライン自己完結＝外部 CDN/ネットワーク参照を持たない（データは
``<script type="application/json">`` にインラインし、フィルタ/ナビゲーションは同梱 JS で行う）。

グラフ照会（deps/dependents/ドリフト）は ``dsv2.query`` を再利用し CLI と完全一致させる。RULE-004 ドリフト
（辺 ``ref_version`` x.y ≠ 参照先バッジ x.y・``suppress: [RULE-004]`` は免除）も query 経由で算出する。
Markdown→HTML は**標準ライブラリのみの最小レンダラ**（見出し/リスト/コードフェンス/インラインコード/
強調/リンク/引用/段落・HTML エスケープ）で、外部ライブラリを持ち込まない。

依存仕様: doc-system-v2/FORMAT.md（1ノード=2ファイル・edges・版）・doc-system-v2/config.yml（layout /
  status_dirs・stage/type/status の並び順）。ドリフト規則は dsv2.query（RULE-004・DD-2・#81）を単一ソースに再利用。
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from . import query
from .meta import STAGES, index_by_id

DEFAULT_OUT = "doc_view.html"

# stage / type の表示順（config.yml layout の並びに一致・meta.py LAYOUT は集合なので順序をここで固定）。
_STAGE_ORDER = ["01-why", "02-what", "03-analysis", "05-design", "04-verification"]
_TYPE_ORDER = [
    "val", "sr", "fr", "nfr", "spec",
    "actor", "i", "o", "d", "p", "e", "term",
    "orc", "ds", "mod", "dm", "port", "prs", "scm", "cfg", "prompt",
    "td", "tc", "tr", "verify", "fnd", "dd", "q", "pend",
]


# --------------------------------------------------------------------------- #
# Markdown → HTML（標準ライブラリのみの最小レンダラ）
# --------------------------------------------------------------------------- #

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
# 強調は開始/終了の内側が非空白のときだけ対にする。本 repo の本文は glob（`*.md` `*.py`
# `docs/**`）を多用するため、空白隣接の単独 `*` を強調へ誤爆させない（Sub-F レビュー指摘）。
_BOLD = re.compile(r"\*\*(?!\s)(.+?)(?<!\s)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(?!\s)(.+?)(?<!\s)(?<!\*)\*(?!\*)")
_INLINE_CODE = re.compile(r"`([^`]+)`")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_ULI = re.compile(r"^\s*[-*]\s+(.*)$")
_OLI = re.compile(r"^\s*\d+\.\s+(.*)$")
_QUOTE = re.compile(r"^>\s?(.*)$")

# 先頭がスキーム（`名前:`）かどうか。無ければ相対パス/アンカーで安全。
_SCHEME = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")
# href に許可するスキーム（外部ロード/スクリプト実行に使えないもの）。
_SAFE_SCHEMES = frozenset({"http", "https", "mailto"})


def _safe_href(url: str) -> str | None:
    """外部ロード/スクリプト実行に使えない安全な href だけ通す。
    http/https/mailto・アンカー(#…)・相対パス（スキーム無し）は許可し、``javascript:`` 等
    未知スキームは None（リンク化しない＝素のテキストへ降格）。他がエスケープ徹底なので href も同水準に揃える。"""
    m = _SCHEME.match(url.strip())
    if m is None:
        return url  # スキーム無し＝相対パス/アンカー/空 → 安全
    return url if m.group(1).lower() in _SAFE_SCHEMES else None


def _link_sub(m: "re.Match[str]") -> str:
    href = _safe_href(m.group(2))
    if href is None:
        return m.group(1)  # 危険スキームはリンク化せず、既にエスケープ済みのテキストを残す
    return f'<a href="{href}" rel="noopener">{m.group(1)}</a>'


def _inline(text: str) -> str:
    """行内 Markdown を HTML へ。エスケープ後にインラインコード/リンク/強調を適用する。"""
    parts = _INLINE_CODE.split(text)  # 奇数 index がコード内容（バッククォート内は装飾しない）
    out: list[str] = []
    for i, seg in enumerate(parts):
        if i % 2 == 1:
            out.append(f"<code>{html.escape(seg)}</code>")
            continue
        seg = html.escape(seg)
        seg = _LINK.sub(_link_sub, seg)
        seg = _BOLD.sub(r"<strong>\1</strong>", seg)
        seg = _ITALIC.sub(r"<em>\1</em>", seg)
        out.append(seg)
    return "".join(out)


def render_markdown(text: str) -> str:
    """最小 Markdown → HTML。見出し/リスト/コードフェンス/引用/段落＋行内装飾。外部依存なし。"""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # コードフェンス（```lang ... ```）
        if line.lstrip().startswith("```"):
            i += 1
            code: list[str] = []
            while i < n and not lines[i].lstrip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # 終端フェンスを飛ばす
            out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            continue

        # 空行
        if not line.strip():
            i += 1
            continue

        # 見出し
        m = _HEADING.match(line)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # 引用ブロック（連続する > 行をまとめる）
        if _QUOTE.match(line):
            buf: list[str] = []
            while i < n and _QUOTE.match(lines[i]):
                buf.append(_QUOTE.match(lines[i]).group(1))
                i += 1
            out.append("<blockquote>" + _inline(" ".join(buf)) + "</blockquote>")
            continue

        # 順序なしリスト
        if _ULI.match(line):
            items: list[str] = []
            while i < n and _ULI.match(lines[i]):
                items.append(_ULI.match(lines[i]).group(1))
                i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + "</ul>")
            continue

        # 順序付きリスト
        if _OLI.match(line):
            items = []
            while i < n and _OLI.match(lines[i]):
                items.append(_OLI.match(lines[i]).group(1))
                i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + "</ol>")
            continue

        # 段落（次の空行 or ブロック開始まで）
        buf = []
        while i < n and lines[i].strip() and not (
            lines[i].lstrip().startswith("```")
            or _HEADING.match(lines[i])
            or _QUOTE.match(lines[i])
            or _ULI.match(lines[i])
            or _OLI.match(lines[i])
        ):
            buf.append(lines[i])
            i += 1
        out.append("<p>" + _inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# ビューモデル構築
# --------------------------------------------------------------------------- #

def _read_body(root: Path, node: dict) -> str:
    """ノードの本文 ``.md`` を読む（無ければ空文字）。"""
    path = root / node["body_path"]
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def build_view_model(root: Path, meta: dict) -> dict:
    """viewer が消費する自己完結データを組み立てる（deps/dependents/drift は dsv2.query に一致）。"""
    by_id = index_by_id(meta)
    view_nodes: list[dict] = []
    for node in meta["nodes"]:
        nid = node["id"]
        # deps は query.deps（存在/ドリフト情報つき）を再利用＝CLI と完全一致。
        dep_rows = query.deps(meta, nid) or []
        deps_out = [
            {
                "to": r["to"],
                "ref_version": r["ref_version"],
                "exists": r["exists"],
                "drift": r["drift"] is True,
                "target_type": by_id[r["to"]]["type"] if r["exists"] else None,
                "note": r["note"],
            }
            for r in dep_rows
        ]
        dependents_in = [
            {
                "from": r["from"],
                "type": r["type"],
                "ref_version": r["ref_version"],
                "drift": r["drift"] is True,
            }
            for r in query.dependents(meta, nid)
        ]
        view_nodes.append({
            "id": nid,
            "stage": node["stage"],
            "type": node["type"],
            "status": node["status"],
            "title": node["title"],
            "version": node["version"],
            "labels": node["labels"],
            "scheduled": node["scheduled"],
            "suppress": node.get("suppress", []),
            "condition": node.get("condition"),
            "body_html": render_markdown(_read_body(root, node)),
            "deps": deps_out,
            "dependents": dependents_in,
        })
    return {
        "root": meta.get("root", root.name),
        "stage_order": [s for s in _STAGE_ORDER if s in STAGES],
        "type_order": _TYPE_ORDER,
        "nodes": view_nodes,
    }


# --------------------------------------------------------------------------- #
# HTML 生成
# --------------------------------------------------------------------------- #

def render_html(model: dict) -> str:
    """ビューモデルを単一の自己完結 HTML 文字列へ。データは JSON としてインラインする。"""
    # </script> によるスクリプト脱出を防ぐ（インライン JSON の定石）。
    data_json = json.dumps(model, ensure_ascii=False).replace("</", "<\\/")
    total = len(model["nodes"])
    drift_total = sum(
        1 for n in model["nodes"] for d in n["deps"] if d["drift"]
    )
    return _HTML_TEMPLATE.replace("__DATA__", data_json) \
        .replace("__TOTAL__", str(total)) \
        .replace("__DRIFT__", str(drift_total))


def build_view(root: Path, meta: dict, out: Path) -> dict:
    """ビューモデルを構築し ``out`` へ HTML を書き込む。生成したモデルを返す。"""
    model = build_view_model(root, meta)
    out.write_text(render_html(model), encoding="utf-8")
    return model


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>doc-system v2 — doc_view</title>
<style>
:root { --bg:#fff; --fg:#1a1a1a; --muted:#666; --line:#ddd; --accent:#0b5; --drift:#c00;
        --panel:#f7f7f8; --code:#f0f0f2; }
* { box-sizing: border-box; }
body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
       color:var(--fg); background:var(--bg); font-size:14px; }
header { padding:8px 14px; border-bottom:1px solid var(--line); display:flex;
         gap:14px; align-items:center; flex-wrap:wrap; position:sticky; top:0; background:var(--bg); z-index:5; }
header h1 { font-size:15px; margin:0; }
header .stat { color:var(--muted); font-size:12px; }
header .drift { color:var(--drift); }
.layout { display:flex; height:calc(100vh - 46px); }
#sidebar { width:340px; min-width:260px; border-right:1px solid var(--line); overflow:auto; padding:8px; }
#main { flex:1; overflow:auto; padding:14px 20px; }
.filters { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px; }
.filters select, .filters input { font-size:12px; padding:3px 4px; border:1px solid var(--line); border-radius:4px; }
.filters input { flex:1; min-width:80px; }
details.tree > summary { cursor:pointer; font-weight:600; padding:2px 0; }
details.tree { margin-left:8px; }
.node-link { display:block; padding:2px 6px; margin-left:14px; cursor:pointer; border-radius:4px;
             white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.node-link:hover { background:var(--panel); }
.node-link.active { background:#e6f5ee; }
.badge { display:inline-block; font-size:10px; padding:0 5px; border-radius:8px; border:1px solid var(--line);
         color:var(--muted); margin-left:4px; }
.badge.status { background:#eef; }
.badge.drift { color:#fff; background:var(--drift); border-color:var(--drift); }
.count { color:var(--muted); font-weight:400; font-size:11px; }
#detail h2 { font-size:18px; margin:0 0 4px; }
#detail .meta-row { color:var(--muted); font-size:12px; margin-bottom:10px; }
#detail .idline { font-family: ui-monospace, monospace; font-size:12px; color:#333; word-break:break-all; }
.section { margin:16px 0; }
.section > h3 { font-size:13px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted);
                border-bottom:1px solid var(--line); padding-bottom:3px; }
.edge { padding:2px 0; }
.edge a { cursor:pointer; color:#06c; text-decoration:none; }
.edge a:hover { text-decoration:underline; }
.edge .rv { color:var(--muted); font-size:12px; }
.edge .missing { color:var(--drift); font-weight:600; }
.body { border:1px solid var(--line); background:var(--panel); border-radius:6px; padding:10px 14px; }
.body pre { background:var(--code); padding:8px; overflow:auto; border-radius:4px; }
.body code { background:var(--code); padding:0 3px; border-radius:3px; font-size:12.5px; }
.body pre code { background:none; padding:0; }
.body blockquote { border-left:3px solid var(--line); margin:6px 0; padding:2px 10px; color:#444; }
.body h1,.body h2,.body h3 { font-size:15px; }
.empty { color:var(--muted); font-style:italic; }
kbd { background:var(--code); border:1px solid var(--line); border-radius:3px; padding:0 4px; font-size:11px; }
</style>
</head>
<body>
<header>
  <h1>doc-system v2 <span class="count">doc_view</span></h1>
  <span class="stat">全 <b>__TOTAL__</b> ノード</span>
  <span class="stat drift">ドリフト辺 <b>__DRIFT__</b></span>
  <span class="stat">クリックで移動 / フィルタは左パネル</span>
</header>
<div class="layout">
  <aside id="sidebar">
    <div class="filters">
      <select id="f-stage"><option value="">stage: すべて</option></select>
      <select id="f-type"><option value="">type: すべて</option></select>
      <select id="f-status"><option value="">status: すべて</option></select>
      <label style="font-size:11px;"><input type="checkbox" id="f-drift"> ドリフトのみ</label>
      <input id="f-text" placeholder="id/タイトル 検索">
    </div>
    <div id="tree"></div>
  </aside>
  <main id="main"><div id="detail"><p class="empty">左のノードを選択してください。</p></div></main>
</div>
<script type="application/json" id="data">__DATA__</script>
<script>
"use strict";
const MODEL = JSON.parse(document.getElementById("data").textContent);
const NODES = MODEL.nodes;
const BY_ID = {};
NODES.forEach(n => { BY_ID[n.id] = n; });

const STAGE_ORDER = MODEL.stage_order;
const TYPE_ORDER = MODEL.type_order;
const el = (id) => document.getElementById(id);

function driftCount(n){ return n.deps.filter(d => d.drift).length; }

// ---- フィルタ用の値集合を投入 ----
function fillSelect(sel, values){
  values.forEach(v => {
    const o = document.createElement("option"); o.value = v; o.textContent = v; sel.appendChild(o);
  });
}
fillSelect(el("f-stage"), STAGE_ORDER.filter(s => NODES.some(n => n.stage===s)));
fillSelect(el("f-type"), TYPE_ORDER.filter(t => NODES.some(n => n.type===t)));
fillSelect(el("f-status"), [...new Set(NODES.map(n=>n.status).filter(Boolean))].sort());

function filtered(){
  const st = el("f-stage").value, ty = el("f-type").value, stt = el("f-status").value;
  const dr = el("f-drift").checked;
  const q = el("f-text").value.trim().toLowerCase();
  return NODES.filter(n =>
    (!st || n.stage===st) && (!ty || n.type===ty) && (!stt || n.status===stt) &&
    (!dr || driftCount(n) > 0) &&
    (!q || n.id.toLowerCase().includes(q) || (n.title||"").toLowerCase().includes(q))
  );
}

// ---- 階層ブラウズ（stage → type → status → node）----
function buildTree(){
  const rows = filtered();
  const tree = el("tree");
  tree.textContent = "";
  const stages = STAGE_ORDER.filter(s => rows.some(n => n.stage===s));
  if (!rows.length){ tree.innerHTML = '<p class="empty">該当ノードなし</p>'; return; }
  stages.forEach(stage => {
    const sNodes = rows.filter(n => n.stage===stage);
    const sDet = mkDetails(`${stage} <span class="count">(${sNodes.length})</span>`, true);
    const types = TYPE_ORDER.filter(t => sNodes.some(n => n.type===t));
    types.forEach(type => {
      const tNodes = sNodes.filter(n => n.type===type);
      const tDet = mkDetails(`${type} <span class="count">(${tNodes.length})</span>`, false);
      const statuses = [...new Set(tNodes.map(n => n.status))];
      const hasStatus = statuses.some(Boolean);
      if (hasStatus){
        statuses.filter(Boolean).sort().forEach(status => {
          const stNodes = tNodes.filter(n => n.status===status);
          const stDet = mkDetails(`${status} <span class="count">(${stNodes.length})</span>`, false);
          stNodes.forEach(n => stDet.appendChild(nodeLink(n)));
          tDet.appendChild(stDet);
        });
      } else {
        tNodes.forEach(n => tDet.appendChild(nodeLink(n)));
      }
      sDet.appendChild(tDet);
    });
    tree.appendChild(sDet);
  });
}
function mkDetails(labelHtml, open){
  const d = document.createElement("details"); d.className = "tree"; d.open = open;
  const s = document.createElement("summary"); s.innerHTML = labelHtml; d.appendChild(s);
  return d;
}
function nodeLink(n){
  const a = document.createElement("div");
  a.className = "node-link"; a.dataset.id = n.id;
  const dc = driftCount(n);
  a.innerHTML = escapeHtml(n.title || n.id) +
    (dc ? ` <span class="badge drift">drift ${dc}</span>` : "");
  a.title = n.id;
  a.onclick = () => selectNode(n.id);
  return a;
}

function escapeHtml(s){
  return String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
}

// ---- 詳細ペイン ----
function edgeLink(id, exists){
  if (exists === false) return `<span class="missing">${escapeHtml(id)} (MISSING)</span>`;
  return `<a onclick="selectNode('${cssq(id)}')">${escapeHtml(id)}</a>`;
}
function cssq(id){ return id.replace(/\\/g,"\\\\").replace(/'/g,"\\'"); }

function selectNode(id){
  const n = BY_ID[id];
  if (!n) return;
  document.querySelectorAll(".node-link.active").forEach(e => e.classList.remove("active"));
  const link = document.querySelector('.node-link[data-id="'+cssAttr(id)+'"]');
  if (link){ link.classList.add("active"); link.scrollIntoView({block:"nearest"}); }
  renderDetail(n);
  if (history.replaceState) history.replaceState(null,"", "#"+encodeURIComponent(id));
}
function cssAttr(id){ return id.replace(/"/g,'\\"'); }

// parent/child を型一致から導出（FORMAT.md: 同型間の依存辺＝親子）。
function parents(n){ return n.deps.filter(d => d.exists && d.target_type === n.type); }
function children(n){ return n.dependents.filter(d => d.type === n.type); }

function renderDetail(n){
  const badges = [];
  badges.push(`<span class="badge">${n.stage}</span>`);
  badges.push(`<span class="badge">${n.type}</span>`);
  if (n.status) badges.push(`<span class="badge status">${n.status}</span>`);
  if (n.condition) badges.push(`<span class="badge">${n.condition}</span>`);
  (n.labels||[]).forEach(l => badges.push(`<span class="badge">${escapeHtml(l)}</span>`));
  if ((n.suppress||[]).length) badges.push(`<span class="badge">suppress:${n.suppress.join(",")}</span>`);

  const par = parents(n), ch = children(n);
  const depOut = n.deps, depIn = n.dependents;

  const h = [];
  h.push(`<h2>${escapeHtml(n.title || n.id)}</h2>`);
  h.push(`<div class="idline">${escapeHtml(n.id)}</div>`);
  h.push(`<div class="meta-row">v${escapeHtml(n.version)} ${badges.join(" ")}</div>`);

  h.push(edgeSection("親（同型 refines 先）", par.map(d =>
    `<div class="edge">${edgeLink(d.to, d.exists)} ${rv(d)}</div>`)));
  h.push(edgeSection("子（同型 被参照）", ch.map(d =>
    `<div class="edge">${edgeLink(d.from, true)} <span class="rv">${d.type}${d.drift?' <span class="badge drift">DRIFT</span>':''}</span></div>`)));

  h.push(edgeSection(`依存先（out-edges・${depOut.length}）`, depOut.map(d =>
    `<div class="edge">${edgeLink(d.to, d.exists)} `+
    `<span class="rv">ref=${d.ref_version||'-'}${d.target_type?' ['+d.target_type+']':''}</span>`+
    `${d.drift?' <span class="badge drift">DRIFT</span>':''}</div>`)));
  h.push(edgeSection(`依存元（in-edges・${depIn.length}）`, depIn.map(d =>
    `<div class="edge">${edgeLink(d.from, true)} `+
    `<span class="rv">${d.type} ref=${d.ref_version||'-'}</span>`+
    `${d.drift?' <span class="badge drift">DRIFT</span>':''}</div>`)));

  h.push(`<div class="section"><h3>本文</h3><div class="body">${n.body_html || '<p class="empty">（本文なし）</p>'}</div></div>`);
  el("detail").innerHTML = h.join("\n");
  el("main").scrollTop = 0;
}
function rv(d){ return `<span class="rv">ref=${d.ref_version||'-'}${d.drift?' ':''}</span>${d.drift?'<span class="badge drift">DRIFT</span>':''}`; }
function edgeSection(title, rows){
  const body = rows.length ? rows.join("") : '<div class="empty">なし</div>';
  return `<div class="section"><h3>${title}</h3>${body}</div>`;
}

// ---- 配線 ----
["f-stage","f-type","f-status","f-drift","f-text"].forEach(id =>
  el(id).addEventListener("input", buildTree));
buildTree();
// ディープリンク（#id）で初期選択
const initial = decodeURIComponent((location.hash||"").replace(/^#/,""));
if (initial && BY_ID[initial]) selectNode(initial);
</script>
</body>
</html>
"""
