"""doc-system の Markdown を走査して NodeIndex を組み立てる。

パース規約は ``docs/doc-system/04-notation.md §8``:
  ``<details><summary>⬡ <ID> · v<x.y></summary>`` 行の次の ```yaml``` ブロックを読む。
  見出し = 直前の ``## `` 行、本文 = ``</details>`` 以降〜次の境界（``## ``/``---``/EOF）。
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from . import nodeyaml
from .model import Edge, Node, NodeIndex

# summary バッジ: ⬡ <id> · v<x.y>
_SUMMARY = "⬡"
_MIDDOT = "·"
_VERSION_RE = re.compile(r"v(\d+\.\d+)")

_DEFAULT_INCLUDE = ["doc-system/**/*.md"]
_DEFAULT_EXCLUDE = ["docs/**", "**/README.md", "**/00-dashboard.md", "**/00-dfd.md"]


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
    """
    return "<summary" in line and _SUMMARY in line and _MIDDOT in line


def _parse_summary(line: str) -> tuple[str, str] | None:
    """summary 行から (id, version) を取り出す。バッジが無ければ None。"""
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
    """1 ファイル分のテキストからノード群を抽出する。"""
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
    """config.yaml の ``trace_scope`` の include/exclude を読む（無ければ既定）。"""
    if not config_path.is_file():
        return list(_DEFAULT_INCLUDE), list(_DEFAULT_EXCLUDE)
    include: list[str] | None = None
    exclude: list[str] | None = None
    in_scope = False
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        if raw.strip() == "" or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if raw.strip() == "trace_scope:":
            in_scope = True
            continue
        if in_scope and indent == 0:
            break
        if in_scope:
            key, sep, rest = raw.strip().partition(":")
            if sep and rest.strip().startswith("["):
                vals = [str(v) for v in nodeyaml._inline_list(rest.strip())]
                if key.strip() == "include":
                    include = vals
                elif key.strip() == "exclude":
                    exclude = vals
    return (include or list(_DEFAULT_INCLUDE), exclude or list(_DEFAULT_EXCLUDE))


def discover_files(repo_root: Path, include: list[str], exclude: list[str]) -> list[Path]:
    """include グロブで集め、exclude グロブを除いた in-graph ファイル一覧。"""
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
    """リポジトリ root を走査して NodeIndex を構築する。"""
    root = repo_root or find_repo_root()
    cfg = config_path or (root / "docs" / "doc-system" / "config.yaml")
    include, exclude = load_trace_scope(cfg)
    nodes: list[Node] = []
    for path in discover_files(root, include, exclude):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        nodes.extend(parse_markdown(text, rel))
    return NodeIndex.build(nodes)
