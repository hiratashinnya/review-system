"""doc-system の Markdown を走査して NodeIndex を組み立てる。

パース規約は ``docs/doc-system/04-notation.md §8``:
  ``<details><summary>⬡ <ID> · v<x.y.z></summary>`` 行の次の ```yaml``` ブロックを読む。
  見出し = 直前の ``## `` 行、本文 = ``</details>`` 以降〜次の境界（``## ``/``---``/EOF）。
"""

from __future__ import annotations

import fnmatch
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # repo root（dsv2 用）
from dsv2 import nodeyaml  # noqa: E402  # issue #172: docidx/ から dsv2/ へ分離した共有モジュール
from .model import Edge, Node, NodeIndex

# summary バッジ: ⬡ <id> · v<x.y.z>
_SUMMARY = "⬡"
_MIDDOT = "·"
_VERSION_RE = re.compile(r"v(\d+\.\d+\.\d+)")

_TRACE_SCOPE_HINT = (
    'docidx は trace_scope をインラインリスト形式（例: include: ["doc-system/**/*.md"]）'
    "のみ対応します。ブロック形式（- item）・未設定・config 欠如には対応しません。"
    "config.yaml の trace_scope を該当形式に直してください。"
)


class TraceScopeError(Exception):
    """config.yaml の ``trace_scope`` を解釈できないとき送出する。

    既定値へ黙ってフォールバックすると config 変更（ブロック化・グロブ追加）が docidx に
    効かないドリフトを生むため、フォールバックせず停止して利用者に記法修正を促す。
    """


def find_repo_root(start: Path | None = None) -> Path:
    """``doc-system/`` を含むディレクトリを上方向に探してリポジトリ root とする。"""
    here = (start or Path.cwd()).resolve()
    candidates = [here, *here.parents, Path(__file__).resolve().parent.parent]
    for d in candidates:
        if (d / "doc-system").is_dir():
            return d
    return here


def _is_node_summary_line(line: str) -> bool:
    """本物のノード summary 行か（本文中の例・インラインコードを誤検出しない）。

    本文には ``⬡ SPEC-1 · v0.3`` のような例が現れるため、``<summary`` タグの存在を必須とする。

    依存仕様: SPEC-1-1 v0.1.0, SPEC-1 v0.3.0（04-notation.md §8・02-meta-schema.md §1 DD-8 v0.1.1）
    """
    return "<summary" in line and _SUMMARY in line and _MIDDOT in line


def _parse_summary(line: str) -> tuple[str, str] | None:
    """summary 行から (id, version) を取り出す。バッジが無ければ None。

    依存仕様: SPEC-1 v0.3.0, SPEC-1-1 v0.1.0（04-notation.md §8・02-meta-schema.md §1 DD-8 v0.1.1）
    """
    if not _is_node_summary_line(line):
        return None
    after = line.split(_SUMMARY, 1)[1]
    node_id, _, rest = after.partition(_MIDDOT)
    node_id = node_id.strip()
    match = _VERSION_RE.search(rest)
    if not node_id or not match:
        return None
    return node_id, match.group(1)


def _is_boundary(line: str) -> bool:
    s = line.strip()
    return s == "---" or s.startswith("## ") or _is_node_summary_line(line)


def parse_markdown(text: str, rel_path: str) -> list[Node]:
    """1 ファイル分のテキストからノード群を抽出する。

    依存仕様: SPEC-1 v0.3.0, SPEC-1-1 v0.1.0, SPEC-1-2 v0.1.0（ノード発見・構造化・マーカー=id）。
      見出し=直前 `## `／本文=`</details>` 後＝04-notation.md §4。マーカー直後 YAML 欠如＝§8。
    """
    lines = text.splitlines()
    nodes: list[Node] = []
    heading = ""
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            i += 1
            continue
        parsed = _parse_summary(line) if _SUMMARY in line else None
        if not parsed:
            i += 1
            continue
        node_id, version = parsed
        summary_line_no = i + 1

        # YAML フェンスを探す（summary の数行内）
        j = i + 1
        while j < n and not lines[j].strip().startswith("```"):
            j += 1
        yaml_text = ""
        parse_error: str | None = None
        data: dict = {}
        if j < n:  # 開始フェンス
            k = j + 1
            buf: list[str] = []
            while k < n and not lines[k].strip().startswith("```"):
                buf.append(lines[k])
                k += 1
            yaml_text = "\n".join(buf)
            try:
                data = nodeyaml.parse(yaml_text)
            except nodeyaml.NodeYamlError as exc:
                parse_error = str(exc)
            j = k  # 終了フェンス位置
        else:
            parse_error = "YAML ブロックが見つからない"

        # </details> を探し、本文を境界まで集める
        d = j
        while d < n and lines[d].strip() != "</details>":
            d += 1
        body_lines: list[str] = []
        b = d + 1
        while b < n and not _is_boundary(lines[b]):
            body_lines.append(lines[b])
            b += 1
        body = "\n".join(body_lines).strip()

        nodes.append(_make_node(node_id, version, heading, rel_path,
                                summary_line_no, data, body, parse_error))
        i = b  # 本文の後ろから継続
    return nodes


def _make_node(node_id, version, heading, rel_path, line_no, data, body, parse_error) -> Node:
    """YAML dict＋バッジ情報から Node を組み立てる。

    依存仕様: SPEC-1-1 v0.1.0（id/type/labels/scheduled/edges の抽出）。
    """
    edges = tuple(Edge.from_dict(e) for e in data.get("edges", []) if isinstance(e, dict))
    labels_raw = data.get("labels", [])
    labels = tuple(str(x) for x in labels_raw) if isinstance(labels_raw, list) else ()
    known = {"id", "type", "labels", "scheduled", "condition", "edges"}
    extra = {k: v for k, v in data.items() if k not in known}
    return Node(
        id=node_id,
        type=str(data.get("type", "")),
        version=version,
        heading=heading,
        file=rel_path,
        line=line_no,
        labels=labels,
        scheduled=str(data.get("scheduled", "") or ""),
        condition=str(data.get("condition", "") or ""),
        edges=edges,
        body=body,
        fields=extra,
        parse_error=parse_error,
    )


def load_trace_scope(config_path: Path) -> tuple[list[str], list[str]]:
    """config.yaml の ``trace_scope`` の include/exclude を読む。

    **インラインリスト形式（``include: ["…"]``）のみ対応**。読めない場合
    （config が無い／``trace_scope`` ブロックが無い／``include`` が無い／キーがブロック形式
    などインラインでない）は、既定値へフォールバックせず :class:`TraceScopeError` を送出して
    停止する（黙って古いハードコード既定値ですり替えるドリフトを断つため）。``exclude`` は
    省略可（無ければ空集合）。

    依存仕様: SPEC-24 v0.2.0（trace_scope による in-graph 判定）・config.yaml: trace_scope。
    """
    if not config_path.is_file():
        raise TraceScopeError(f"config.yaml が見つかりません: {config_path}。{_TRACE_SCOPE_HINT}")
    include: list[str] | None = None
    exclude: list[str] | None = None
    seen_scope = False
    in_scope = False
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        if raw.strip() == "" or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if raw.strip() == "trace_scope:":
            in_scope = True
            seen_scope = True
            continue
        if in_scope and indent == 0:
            break
        if in_scope:
            key, sep, rest = raw.strip().partition(":")
            key = key.strip()
            if key not in ("include", "exclude"):
                continue
            if not (sep and rest.strip().startswith("[")):
                # ブロック形式（- item）や空など、インラインでない記法は黙って既定に逃がさず停止
                raise TraceScopeError(
                    f"config.yaml の trace_scope.{key} がインラインリスト形式ではありません"
                    f"（該当行: {raw.strip()!r}）。{_TRACE_SCOPE_HINT}"
                )
            vals = [str(v) for v in nodeyaml._inline_list(rest.strip())]
            if key == "include":
                include = vals
            else:
                exclude = vals
    if not seen_scope:
        raise TraceScopeError(
            f"config.yaml に trace_scope ブロックがありません: {config_path}。{_TRACE_SCOPE_HINT}"
        )
    if include is None:
        raise TraceScopeError(
            f"config.yaml の trace_scope に include がありません: {config_path}。{_TRACE_SCOPE_HINT}"
        )
    return include, exclude or []


def discover_files(repo_root: Path, include: list[str], exclude: list[str]) -> list[Path]:
    """include グロブで集め、exclude グロブを除いた in-graph ファイル一覧。

    依存仕様: SPEC-24 v0.2.0, SPEC-31 v0.1.0（in-graph 判定・空集合）・config.yaml: trace_scope。
    """
    found: set[Path] = set()
    for pattern in include:
        for p in repo_root.glob(pattern):
            if p.is_file():
                found.add(p)
    result: list[Path] = []
    for p in sorted(found):
        rel = p.relative_to(repo_root).as_posix()
        if any(fnmatch.fnmatch(rel, ex) for ex in exclude):
            continue
        result.append(p)
    return result


def build_index(repo_root: Path | None = None, config_path: Path | None = None) -> NodeIndex:
    """リポジトリ root を走査して NodeIndex を構築する。

    依存仕様: SPEC-1 v0.3.0（ノード発見）・SPEC-24 v0.2.0, SPEC-31 v0.1.0（trace_scope 解決）。
    """
    root = repo_root or find_repo_root()
    cfg = config_path or (root / "docs" / "doc-system" / "config.yaml")
    include, exclude = load_trace_scope(cfg)
    nodes: list[Node] = []
    for path in discover_files(root, include, exclude):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        nodes.extend(parse_markdown(text, rel))
    return NodeIndex.build(nodes)
