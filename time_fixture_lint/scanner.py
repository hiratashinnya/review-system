"""wall clock と比較されうる時刻依存 test data を検査する（Issue #344 手当てB・#349 是正）。

背景・スコープの絞り込み方針
----------------------------
単純な絶対日付 grep は inert な `created_at`/`fetched_at`/`completed_at` 等を大量に
誤検出する。実測（Issue #344 起票時点）で `tests/` 配下の17 fixture・9 テストが絶対日付を
含むが、大半は無害 —— 例えば `blocker_gate/contract.py` の
``_date(result["fetched_at"]) > _date(result["completed_at"])`` は、fetched_at・completed_at
双方が同一スナップショット内の固定値同士の内部整合性チェックであり、どちらも wall clock
（``datetime.now()``/``time.time()``）と比較されない（安全 by construction）。

そこで本ツールは対象を「wall clock と直接比較されうる**境界値**の意味を持つフィールド名」
に絞る（:data:`SUSPICIOUS_FIELD_RE`：``expires_at``/``approved_at``/``resets_at`` (camelCase
``resetsAt`` も含む)/``expiry``/``deadline``/``valid_until``/``not_after``/``not_before``）。
``created_at``/``fetched_at``/``completed_at``/``id`` 等はこの語彙に含めない。

**上限（期限）側だけでなく下限（開始）側も対象**（PR #349 是正・F-344-02）：
``expires_at``/``valid_until``/``deadline``/``not_after``/``resets_at`` のような期限側だけでなく、
``approved_at``/``not_before`` のような窓の開始側も対象に含める。理由は向きではなく
「authoring 時点で値を『まだ現在時刻の反対側』に置いた場合、時間経過で比較結果が反転しうるか」
——``approved <= now`` 型の比較で ``approved_at`` を意図的に未来日にして「未承認」を表す
fixture を書けば、``expires_at`` が過去に転じて壊れるのと対称に、時間経過で ``False`` から
``True`` へ反転しうる。安全なのは、比較相手が wall clock ではなく同一スナップショット内の
他の固定値（fetched_at/completed_at 型）か、``time.time()`` 相対式（#302 パターン）の場合に限る。

2つの検出器:

* **fixture 検出器**（:func:`scan_fixtures`）―
  ``tests/fixtures/**/*.{yml,yaml,json}`` の1行1フィールド形（strict YAML / JSON 共通、
  シングル/ダブルクォート・裸値のいずれも可）を対象フィールド名でスキャンし、ヒットした
  フィクスチャを参照する ``tests/unit/*.py`` の**その参照箇所自身**が clock を制御している
  （``unittest.mock.patch``/``freeze_time``/``now=`` 注入等、:data:`PROTECTION_MARKER_RE`）ことを
  要求する。参照テストが1つも見つからない場合は「保護の有無を確認できない」として
  ``no_consumer`` を報告する（無視せず可視化する）。

* **python literal 検出器**（:func:`scan_python_literals`）―
  ``tests/unit/*.py`` 内の dict リテラル・定数代入から同じ語彙でヒットした行が、
  **その参照箇所自身のスコープ内**で clock 保護マーカーを持つか、``time.time()`` との
  相対式内にある（#302 で採用された安全パターン）ことを要求する。

保護判定のスコープ（PR #349 是正・F-344-01）
--------------------------------------------
旧実装は「参照テストファイル全文」を対象に :data:`PROTECTION_MARKER_RE` を検索しており、
clock と無関係な ``patch(...)`` が同じファイルのどこか別の場所にあるだけで「保護済み」と
誤判定していた（#339 と同クラスの再武装を検知できない false negative）。

本実装は :class:`_FileGraph` で各 python テストファイルを ``ast`` 解析し、フィクスチャ／
疑わしいリテラルの**参照行を直接囲む関数（メソッド）**を起点に、
(a) その関数自身のソース、
(b) 関数がクラスメソッドなら、そのクラスの ``setUp``/``setUpClass``（unittest が暗黙に
    呼ぶため、明示的な呼び出しが無くても保護スコープに含める）、
(c) 同一ファイル内のローカル関数呼び出し（``foo()``/``self.foo()`` を単純名で解決）で
    無向に連結する関数群（例：フィクスチャを読むヘルパー関数 A と、clock を patch する
    別のヘルパー関数 B を同じ test メソッドが両方呼ぶ構成で、A と B は「同じ test に
    呼ばれる」という一点で連結する）
の和集合をスコープとして :data:`PROTECTION_MARKER_RE` を検索する。
また ``patch(...)`` は**引数の対象文字列が clock 関連語（datetime/time/clock/freeze）を
含む場合のみ**保護マーカーとして数える——clock と無関係な対象への patch（例：
``patch("blocker_gate.cli.resolve_github_token")``）は、たとえ参照箇所と同じ関数内に
あっても保護とみなさない。

既知の残存限界（意図的に許容・Issue #129 と同水準の明記）：
モジュールレベル（関数の外）で参照される場合はスコープを狭められずファイル全文に
フォールバックする。また、同じヘルパー関数が「clock を保護する呼び出し元」と「保護
しない新しい呼び出し元」の両方から呼ばれる場合、無向連結成分は呼び出し元を区別しない
ため、新しい呼び出し元が誤って「保護済み」と判定されうる（fixture 共有ヘルパーの
呼び出し元ごとの区別は、静的解析の範囲を超えるデータフロー解析が必要なため未対応）。

誤検出（inert と判断した absolute date/epoch）は
:mod:`time_fixture_lint.allowlist` に (path, name) と理由を明記して登録する
（``asset_parity/exceptions.py` と同じ「消さず理由を残す」運用）。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
import re

from .allowlist import is_allowlisted

FIXTURE_EXTS = (".yml", ".yaml", ".json")
FIXTURE_ROOT = "tests/fixtures"
PY_TEST_ROOT = "tests/unit"

# wall clock と直接比較されうる境界値語彙（上限・下限どちらも含む。inert な
# created_at/fetched_at/completed_at は含めない。理由は本モジュール docstring 参照）。
SUSPICIOUS_FIELD_RE = re.compile(
    r"(?i)\b(expires?_?at|approved_at|resets?_?at|expiry|deadline|valid_until|not_after|not_before)\b"
)

# `key: value` トークン（YAML の1行1フィールド・JSON の1行複数フィールドの両方に対応）。
# key はシングル/ダブルクォート/裸のいずれも許容し、value もシングル/ダブルクォート/裸の
# いずれかにマッチする（F-344-03：旧実装はダブルクォートと裸値しか想定していなかった）。
FIELD_TOKEN_RE = re.compile(
    r"['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?\s*:\s*"
    r"(?:\"([^\"]*)\"|'([^']*)'|([^,}\s]+))"
)

# 値が ISO8601 絶対日付、または epoch 疑いの10桁整数か。
ABS_DATE_VALUE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
EPOCH_VALUE_RE = re.compile(r"^\d{10}$")

# python test 内の裸の epoch 定数代入（例: `NOW = 1783760000`）。
BARE_EPOCH_ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d{10})\b")

# patch(...) の対象文字列が clock 関連語を含む場合のみ保護マーカーとして数える
# （F-344-01：clock と無関係な patch() で保護済みと誤判定させない）。
_CLOCK_PATCH_TARGET = r"[\"'][^\"']*(?:datetime|\btime\b|clock|freeze)[^\"']*[\"']"

# clock を制御している証拠。参照箇所の保護スコープ内にいずれかがあれば「保護済み」とみなす。
PROTECTION_MARKER_RE = re.compile(
    r"unittest\.mock\.patch\(\s*" + _CLOCK_PATCH_TARGET + r"|"
    r"(?<![\w.])patch\(\s*" + _CLOCK_PATCH_TARGET + r"|"
    r"freeze_time\(|freezegun|now\s*=\s*datetime\(|wraps=datetime"
)

# 同一行で time.time() の相対式に包まれていれば安全（#302 で採用された修正パターン）。
RELATIVE_TIME_RE = re.compile(r"time\.time\(\)")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    name: str
    value: str
    status: str  # "protected" | "violation" | "allowlisted" | "no_consumer"
    detail: str


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    @property
    def violations(self) -> list[Finding]:
        return [f for f in self.findings if f.status in ("violation", "no_consumer")]


def _iter_fixture_files(root: Path) -> list[Path]:
    fixtures_dir = root / FIXTURE_ROOT
    if not fixtures_dir.is_dir():
        return []
    return sorted(p for p in fixtures_dir.rglob("*") if p.is_file() and p.suffix in FIXTURE_EXTS)


def _iter_python_test_files(root: Path) -> list[Path]:
    test_dir = root / PY_TEST_ROOT
    if not test_dir.is_dir():
        return []
    return sorted(test_dir.glob("test_*.py"))


def _field_hits_in_line(line: str) -> list[tuple[str, str]]:
    """1行から `key: value` トークンを全て抽出する（1行に複数フィールドがあっても良い）。"""
    hits: list[tuple[str, str]] = []
    for m in FIELD_TOKEN_RE.finditer(line):
        value = m.group(2)
        if value is None:
            value = m.group(3)
        if value is None:
            value = m.group(4) or ""
        hits.append((m.group(1), value.strip()))
    return hits


def _suspicious_fields_in_text(text: str) -> list[tuple[int, str, str]]:
    """(line_no, field_name, value) を疑わしいフィールドの行から抽出する。"""
    hits: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for name, value in _field_hits_in_line(line):
            if not SUSPICIOUS_FIELD_RE.search(name):
                continue
            if not (ABS_DATE_VALUE_RE.match(value) or EPOCH_VALUE_RE.match(value)):
                continue
            hits.append((line_no, name, value))
    return hits


def _occurrence_lines(text: str, basenames: set[str]) -> list[int]:
    """fixture basename（フルネーム/stem）が現れる行番号を全て返す。"""
    return [
        line_no
        for line_no, line in enumerate(text.splitlines(), 1)
        if any(b in line for b in basenames)
    ]


class _FileGraph:
    """1 python テストファイル分の局所呼び出しグラフ（無向・簡易名解決）。

    参照箇所を直接囲む関数を起点に、「同じファイル内でローカル関数呼び出しにより
    連結する関数群」＋「クラスの setUp/setUpClass」を保護マーカー探索スコープとして
    返す（モジュール docstring の「保護判定のスコープ」参照）。
    """

    def __init__(self, tree: ast.Module, text: str) -> None:
        self.tree = tree
        self.text = text
        self._by_name: dict[str, list[ast.AST]] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._by_name.setdefault(node.name, []).append(node)
        self._node_by_id: dict[int, ast.AST] = {
            id(n): n for nodes in self._by_name.values() for n in nodes
        }
        self._adjacency: dict[int, set[int]] = {}
        for func in self._node_by_id.values():
            for call_name in self._called_local_names(func):
                for callee in self._by_name.get(call_name, ()):
                    if callee is func:
                        continue
                    self._adjacency.setdefault(id(func), set()).add(id(callee))
                    self._adjacency.setdefault(id(callee), set()).add(id(func))

    @staticmethod
    def _called_local_names(func_node: ast.AST) -> set[str]:
        names: set[str] = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                target = node.func
                if isinstance(target, ast.Name):
                    names.add(target.id)
                elif isinstance(target, ast.Attribute):
                    names.add(target.attr)
        return names

    def _enclosing(self, lineno: int) -> tuple[ast.AST | None, ast.ClassDef | None]:
        best_func: ast.AST | None = None
        best_class: ast.ClassDef | None = None

        def visit(node: ast.AST, classes: list[ast.ClassDef]) -> None:
            nonlocal best_func, best_class
            if isinstance(node, ast.ClassDef):
                classes = classes + [node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", None) or node.lineno
                if node.lineno <= lineno <= end:
                    best_func = node
                    best_class = classes[-1] if classes else None
            for child in ast.iter_child_nodes(node):
                visit(child, classes)

        visit(self.tree, [])
        return best_func, best_class

    def protection_scope_text(self, lineno: int) -> str | None:
        """``lineno`` を含む参照箇所の保護判定スコープ本文。
        囲み関数が見つからない（モジュールレベル参照）場合は None
        （呼び出し側でファイル全文へフォールバックさせる）。"""
        func, cls = self._enclosing(lineno)
        if func is None:
            return None

        parts: list[str] = []
        seen: set[int] = set()

        def add(node: ast.AST) -> None:
            if id(node) in seen:
                return
            seen.add(id(node))
            segment = ast.get_source_segment(self.text, node)
            if segment:
                parts.append(segment)

        add(func)
        frontier = [id(func)]
        if cls is not None:
            for item in cls.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in (
                    "setUp",
                    "setUpClass",
                ):
                    add(item)
                    frontier.append(id(item))

        while frontier:
            current_id = frontier.pop()
            for neighbor_id in self._adjacency.get(current_id, ()):
                if neighbor_id in seen:
                    continue
                add(self._node_by_id[neighbor_id])
                frontier.append(neighbor_id)

        return "\n".join(parts)


def _build_graph(text: str) -> _FileGraph | None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    return _FileGraph(tree, text)


def _is_protected(graph: _FileGraph | None, text: str, lineno: int) -> bool:
    if graph is not None:
        scope = graph.protection_scope_text(lineno)
        if scope is not None:
            return bool(PROTECTION_MARKER_RE.search(scope))
    # ast 解析に失敗した、またはモジュールレベル参照でスコープを絞れない場合は
    # ファイル全文へフォールバックする（既知の限界。モジュール docstring 参照）。
    return bool(PROTECTION_MARKER_RE.search(text))


def scan_fixtures(root: Path) -> list[Finding]:
    """tests/fixtures/**/*.{yml,yaml,json} の疑わしいフィールドを検査する。"""
    findings: list[Finding] = []
    py_files = _iter_python_test_files(root)
    py_texts = {p: p.read_text(encoding="utf-8") for p in py_files}
    py_graphs = {p: _build_graph(t) for p, t in py_texts.items()}

    for fixture_path in _iter_fixture_files(root):
        rel = fixture_path.relative_to(root).as_posix()
        text = fixture_path.read_text(encoding="utf-8")
        hits = _suspicious_fields_in_text(text)
        if not hits:
            continue

        basenames = {fixture_path.name, fixture_path.stem}
        referencing = [p for p, t in py_texts.items() if any(b in t for b in basenames)]
        ref_rels = [p.relative_to(root).as_posix() for p in referencing]

        for line_no, name, value in hits:
            allow = is_allowlisted(rel, name)
            if allow is not None:
                findings.append(Finding(rel, line_no, name, value, "allowlisted", allow.reason))
                continue
            if not referencing:
                findings.append(Finding(
                    rel, line_no, name, value, "no_consumer",
                    "この fixture を参照する tests/unit/*.py が見つからない"
                    "（wall clock 保護の有無を確認できない）。allowlist に登録するか、"
                    "参照テストを追加/名称を合わせること。",
                ))
                continue

            unprotected: list[str] = []
            for p, r in zip(referencing, ref_rels):
                occ_lines = _occurrence_lines(py_texts[p], basenames)
                if not occ_lines or not all(
                    _is_protected(py_graphs[p], py_texts[p], ln) for ln in occ_lines
                ):
                    unprotected.append(r)

            if not unprotected:
                findings.append(Finding(
                    rel, line_no, name, value, "protected",
                    f"参照テスト全て({', '.join(ref_rels)})の参照箇所が clock 保護スコープ内。",
                ))
            else:
                findings.append(Finding(
                    rel, line_no, name, value, "violation",
                    f"参照テスト {', '.join(sorted(set(unprotected)))} の参照箇所（関数スコープで確認）に"
                    "clock 保護マーカー（unittest.mock.patch/freeze_time/now= 注入等、"
                    "clock 関連対象への patch に限る）が見つからない。",
                ))
    return findings


def scan_python_literals(root: Path) -> list[Finding]:
    """tests/unit/*.py 内の裸の疑わしいフィールド/epoch 定数を検査する。"""
    findings: list[Finding] = []
    for py_path in _iter_python_test_files(root):
        rel = py_path.relative_to(root).as_posix()
        text = py_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        graph = _build_graph(text)

        candidates: dict[str, list[int]] = {}
        for line_no, line in enumerate(lines, 1):
            if RELATIVE_TIME_RE.search(line):
                continue  # time.time() ± offset の相対式は安全（#302 のパターン）
            for name, value in _field_hits_in_line(line):
                if SUSPICIOUS_FIELD_RE.search(name) and (
                    ABS_DATE_VALUE_RE.match(value) or EPOCH_VALUE_RE.match(value)
                ):
                    candidates.setdefault(name, []).append(line_no)
            m2 = BARE_EPOCH_ASSIGN_RE.match(line)
            if m2:
                candidates.setdefault(m2.group(1), []).append(line_no)

        for name, line_nos in sorted(candidates.items()):
            allow = is_allowlisted(rel, name)
            first_line = line_nos[0]
            sample_value = lines[first_line - 1].strip()
            if allow is not None:
                findings.append(Finding(rel, first_line, name, sample_value, "allowlisted", allow.reason))
                continue
            protected = all(_is_protected(graph, text, ln) for ln in line_nos)
            if protected:
                findings.append(Finding(
                    rel, first_line, name, sample_value, "protected",
                    f"参照箇所（関数スコープで確認、{len(line_nos)}箇所で同名ヒット）に clock 保護マーカーあり。",
                ))
            else:
                findings.append(Finding(
                    rel, first_line, name, sample_value, "violation",
                    "clock 保護マーカー（同一スコープ内、clock 関連対象への patch に限る）も"
                    f"time.time() 相対化も無いまま固定値を使用（{len(line_nos)}箇所で同名ヒット）。"
                    "allowlist で inert と示すか、clock を制御すること。",
                ))
    return findings


def scan(root: Path) -> Report:
    return Report(findings=scan_fixtures(root) + scan_python_literals(root))
