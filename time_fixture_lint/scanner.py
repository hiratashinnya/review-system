"""wall clock と比較されうる時刻依存 test data を検査する（Issue #344 手当てB）。

背景・スコープの絞り込み方針
----------------------------
単純な絶対日付 grep は inert な `created_at`/`fetched_at`/`completed_at` 等を大量に
誤検出する。実測（Issue #344 起票時点）で `tests/` 配下の17 fixture・9 テストが絶対日付を
含むが、大半は無害 —— 例えば `blocker_gate/contract.py` の
``_date(result["fetched_at"]) > _date(result["completed_at"])`` は**下限比較**で、
``completed_at`` は常に実行時点の実時刻から生成されるため、固定された過去の
``fetched_at`` が将来 ``>`` に転じることはない（安全 by construction）。

そこで本ツールは対象を「wall clock と比較されうる**上限/期限側**の意味を持つフィールド名」
に絞る（:data:`SUSPICIOUS_FIELD_RE`：``expires_at``/``approved_at``/``resets_at`` (camelCase
``resetsAt`` も含む)/``expiry``/``deadline``/``valid_until``/``not_after``/``not_before``）。
``created_at``/``fetched_at``/``completed_at``/``id`` 等はこの語彙に含めない。

2つの検出器:

* **fixture 検出器**（:func:`scan_fixtures`）―
  ``tests/fixtures/**/*.{yml,yaml,json}`` の1行1フィールド形（strict YAML / JSON 共通）を
  対象フィールド名でスキャンし、ヒットしたフィクスチャを参照する ``tests/unit/*.py`` が
  clock を制御している（``unittest.mock.patch``/``freeze_time``/``now=`` 注入等、
  :data:`PROTECTION_MARKER_RE`）ことを要求する。参照テストが1つも見つからない場合は
  「保護の有無を確認できない」として ``no_consumer`` を報告する（無視せず可視化する）。

* **python literal 検出器**（:func:`scan_python_literals`）―
  ``tests/unit/*.py`` 内の dict リテラル・定数代入から同じ語彙でヒットした行が、
  同一ファイル内で clock 保護マーカーを持つか、``time.time()`` との相対式内にある
  （#302 で採用された安全パターン）ことを要求する。

誤検出（inert と判断した absolute date/epoch）は
:mod:`time_fixture_lint.allowlist` に (path, name) と理由を明記して登録する
（``asset_parity/exceptions.py`` と同じ「消さず理由を残す」運用）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from .allowlist import is_allowlisted

FIXTURE_EXTS = (".yml", ".yaml", ".json")
FIXTURE_ROOT = "tests/fixtures"
PY_TEST_ROOT = "tests/unit"

# 期限/上限を示唆する語だけに絞った語彙（inert な created_at/fetched_at/completed_at は含めない）。
SUSPICIOUS_FIELD_RE = re.compile(
    r"(?i)\b(expires?_?at|approved_at|resets?_?at|expiry|deadline|valid_until|not_after|not_before)\b"
)

# `key: value` / `"key": value` の1行1フィールド形（strict YAML と JSON の双方に対応）。
FIELD_LINE_RE = re.compile(r'^\s*"?([A-Za-z_][A-Za-z0-9_]*)"?\s*:\s*"?([^",}]*)"?,?\s*$')

# 値が ISO8601 絶対日付、または epoch 疑いの10桁整数か。
ABS_DATE_VALUE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
EPOCH_VALUE_RE = re.compile(r"^\d{10}$")

# python test 内の裸の epoch 定数代入（例: `NOW = 1783760000`）。
BARE_EPOCH_ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d{10})\b")

# clock を制御している証拠。いずれかが同一ファイルにあれば「保護済み」とみなす。
PROTECTION_MARKER_RE = re.compile(
    r"unittest\.mock\.patch\(|(?<![\w.])patch\(|freeze_time\(|freezegun|now\s*=\s*datetime\(|wraps=datetime"
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


def _suspicious_fields_in_text(text: str) -> list[tuple[int, str, str]]:
    """(line_no, field_name, value) を1行1フィールド形の行から抽出する。"""
    hits: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        m = FIELD_LINE_RE.match(line)
        if not m:
            continue
        name, value = m.group(1), m.group(2)
        if not SUSPICIOUS_FIELD_RE.search(name):
            continue
        if not (ABS_DATE_VALUE_RE.match(value) or EPOCH_VALUE_RE.match(value)):
            continue
        hits.append((line_no, name, value))
    return hits


def scan_fixtures(root: Path) -> list[Finding]:
    """tests/fixtures/**/*.{yml,yaml,json} の疑わしいフィールドを検査する。"""
    findings: list[Finding] = []
    py_files = _iter_python_test_files(root)
    py_texts = {p: p.read_text(encoding="utf-8") for p in py_files}

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
            protected_files = [
                r for r, p in zip(ref_rels, referencing) if PROTECTION_MARKER_RE.search(py_texts[p])
            ]
            if len(protected_files) == len(referencing):
                findings.append(Finding(
                    rel, line_no, name, value, "protected",
                    f"参照テスト全て({', '.join(ref_rels)})に clock 保護マーカーあり。",
                ))
            else:
                unprotected = sorted(set(ref_rels) - set(protected_files))
                findings.append(Finding(
                    rel, line_no, name, value, "violation",
                    f"参照テスト {', '.join(unprotected)} に clock 保護マーカー"
                    "（unittest.mock.patch/freeze_time/now= 注入等）が見つからない。",
                ))
    return findings


def scan_python_literals(root: Path) -> list[Finding]:
    """tests/unit/*.py 内の裸の疑わしいフィールド/epoch 定数を検査する。"""
    findings: list[Finding] = []
    for py_path in _iter_python_test_files(root):
        rel = py_path.relative_to(root).as_posix()
        text = py_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        protected = bool(PROTECTION_MARKER_RE.search(text))

        candidates: dict[str, list[int]] = {}
        for line_no, line in enumerate(lines, 1):
            if RELATIVE_TIME_RE.search(line):
                continue  # time.time() ± offset の相対式は安全（#302 のパターン）
            m = FIELD_LINE_RE.match(line)
            if m:
                name, value = m.group(1), m.group(2)
                if SUSPICIOUS_FIELD_RE.search(name) and (
                    ABS_DATE_VALUE_RE.match(value) or EPOCH_VALUE_RE.match(value)
                ):
                    candidates.setdefault(name, []).append(line_no)
                    continue
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
            if protected:
                findings.append(Finding(
                    rel, first_line, name, sample_value, "protected",
                    f"ファイル内に clock 保護マーカーあり（{len(line_nos)}箇所で同名ヒット）。",
                ))
            else:
                findings.append(Finding(
                    rel, first_line, name, sample_value, "violation",
                    f"clock 保護マーカーも time.time() 相対化も無いまま固定値を使用"
                    f"（{len(line_nos)}箇所で同名ヒット）。allowlist で inert と示すか、"
                    "clock を制御すること。",
                ))
    return findings


def scan(root: Path) -> Report:
    return Report(findings=scan_fixtures(root) + scan_python_literals(root))
