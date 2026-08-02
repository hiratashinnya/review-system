"""カルテ書式のデータモデル・パーサ・シリアライザ・バリデータ。

書式（``tmp/_karte/issue-<N>.md``）:

    # Karte: issue-307

    ## Findings

    ### F-307-01
    status: open
    harm: real
    harm_detail: required 属性が消え必須入力が素通りする
    locus: review_system/forms.py::build_attrs
    summary: build_attrs が既存 attrs を破棄している
    rounds: [1, 2]
    resolved_round:

    ## Attempts

    ### Attempt 1
    round: 1
    finding_ids: [F-307-01]
    root_cause: boundfield-attrs-overwrite
    change_kind: logic
    targets: [review_system/forms.py::build_attrs]
    diagnosis: 既存 attrs を dict リテラルで作り直している

    ### Result 1
    attempt: 1
    finding_ids: [F-307-01]
    touched: [review_system/forms.py, review_system/forms.py::build_attrs]
    outcome: partial
    note: required は残ったが aria-* が欠ける

追記規律:
  * ``## Findings`` は **ID 付き指摘台帳**。``ingest-review`` だけがこのセクションを更新する
    （status/rounds の遷移を持つ台帳なので、セクション単位で書き直す）。
  * ``### Attempt k`` / ``### Result k`` は **追記のみ**。いったん書かれたブロックは
    どの verb も書き換えない。``close-attempt`` は Attempt を書き換えるのではなく
    対応する ``### Result k`` を追記する（実測 touched-set の記録先）。

値の書式は「1行 1 ``key: value``」のみ（複数行の自由記述は持たない＝決定論パースのため）。
``[a, b]`` はリスト、それ以外はスカラ文字列として解釈する。

依存仕様: :mod:`karte` の docstring（Issue #307「カルテの実体」「finding ID による結合」
「Attempt の機械比較可能ヘッダ」）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

FORMAT_VERSION = 1

CHANGE_KINDS = ("logic", "data-structure", "interface", "config", "test", "revert")
HARM_LEVELS = ("real", "none")
FINDING_STATUSES = ("open", "resolved")
OUTCOMES = ("fixed", "partial", "no-change", "regressed")

SECTION_FINDINGS = "Findings"
SECTION_ATTEMPTS = "Attempts"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
FINDING_ID_RE = re.compile(r"^F-([1-9][0-9]*)-([0-9]{2,})$")
DOC_HEADER_RE = re.compile(r"^#\s+Karte:\s+issue-([1-9][0-9]*)\s*$")
ATTEMPT_TITLE_RE = re.compile(r"^Attempt\s+([1-9][0-9]*)$")
RESULT_TITLE_RE = re.compile(r"^Result\s+([1-9][0-9]*)$")
KEY_RE = re.compile(r"^([a-z][a-z0-9_]*):(.*)$")

# 台帳の値に持ち込めない文字（1行 key: value ＋ `[a, b]` 記法を壊すため）。
FORBIDDEN_VALUE_CHARS = ("\n", "\r", "\0")
FORBIDDEN_LIST_ITEM_CHARS = (",", "[", "]")

_STOPWORDS = frozenset(
    ["the", "a", "an", "is", "are", "を", "が", "に", "は", "の", "で", "と", "し", "て"]
)


class KarteFormatError(Exception):
    """カルテ／レビューレポートの書式違反・スキーマ違反（fail-close）。"""


# --- 値 ---------------------------------------------------------------------


def parse_value(raw: str):
    """``[a, b]`` はリスト、それ以外はスカラ文字列として解釈する。"""
    text = raw.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [part.strip() for part in inner.split(",") if part.strip()]
    return text


def format_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(str(item) for item in value) + "]"
    return str(value)


def check_scalar(value, what: str) -> str:
    text = "" if value is None else str(value)
    for bad in FORBIDDEN_VALUE_CHARS:
        if bad in text:
            raise KarteFormatError(f"{what} に改行/NUL は書けない: {text!r}")
    return text.strip()


def check_list(values, what: str) -> list:
    if isinstance(values, str):
        raise KarteFormatError(f"{what} はリスト（`[a, b]`）で書く: {values!r}")
    checked = []
    for item in values:
        text = check_scalar(item, what)
        if not text:
            continue
        for bad in FORBIDDEN_LIST_ITEM_CHARS:
            if bad in text:
                raise KarteFormatError(f"{what} の要素に {bad!r} は使えない: {text!r}")
        if text not in checked:
            checked.append(text)
    return checked


def format_finding_id(issue: int, seq: int) -> str:
    """``F-{issue}-{seq}``（seq は 2 桁ゼロ詰め・例 ``F-312-03``）。"""
    return f"F-{int(issue)}-{int(seq):02d}"


def parse_finding_id(value: str):
    """``F-<issue>-<seq>`` を ``(issue, seq)`` に分解する。形式違反は例外。"""
    text = str(value).strip()
    matched = FINDING_ID_RE.match(text)
    if not matched:
        raise KarteFormatError(
            f"finding ID の形式違反（期待 `F-<issue>-<seq>`・例 F-312-03）: {value!r}"
        )
    return int(matched.group(1)), int(matched.group(2))


# --- ブロックパーサ ----------------------------------------------------------


@dataclass
class Block:
    section: str | None
    title: str
    fields: dict
    lineno: int


def parse_blocks(text: str) -> list:
    """``## Section`` / ``### Title`` ＋ ``key: value`` 行の決定論パーサ。

    解釈できない行が 1 行でもあれば :class:`KarteFormatError`（fail-close）。
    """
    blocks: list = []
    section = None
    current = None
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("<!--"):
            continue
        if line.startswith("### "):
            current = Block(section, line[4:].strip(), {}, lineno)
            blocks.append(current)
            continue
        if line.startswith("## "):
            section = line[3:].strip()
            current = None
            continue
        if line.startswith("# "):
            current = None
            continue
        matched = KEY_RE.match(line)
        if matched and current is not None:
            key = matched.group(1)
            if key in current.fields:
                raise KarteFormatError(f"{lineno} 行目: キー '{key}' が重複している")
            current.fields[key] = parse_value(matched.group(2))
            continue
        raise KarteFormatError(f"{lineno} 行目: 解釈できない行: {line!r}")
    return blocks


def _require(block: Block, key: str):
    if key not in block.fields:
        raise KarteFormatError(
            f"{block.lineno} 行目 '{block.title}': 必須キー '{key}' が無い"
        )
    return block.fields[key]


def _require_nonempty(block: Block, key: str) -> str:
    value = _require(block, key)
    if isinstance(value, list) or not str(value).strip():
        raise KarteFormatError(
            f"{block.lineno} 行目 '{block.title}': '{key}' が空（必須項目）"
        )
    return str(value).strip()


def _require_enum(block: Block, key: str, allowed) -> str:
    value = _require_nonempty(block, key)
    if value not in allowed:
        raise KarteFormatError(
            f"{block.lineno} 行目 '{block.title}': '{key}' は {list(allowed)} のいずれか: {value!r}"
        )
    return value


def _require_int_list(block: Block, key: str) -> list:
    value = block.fields.get(key, [])
    if isinstance(value, str):
        value = [value] if value.strip() else []
    numbers = []
    for item in value:
        text = str(item).strip()
        if not text.isdigit():
            raise KarteFormatError(
                f"{block.lineno} 行目 '{block.title}': '{key}' は整数のリスト: {item!r}"
            )
        numbers.append(int(text))
    return numbers


# --- モデル ------------------------------------------------------------------


@dataclass
class Finding:
    """ID 付き指摘（台帳の 1 行）。"""

    id: str
    status: str = "open"
    harm: str = "real"
    harm_detail: str = ""
    locus: str = ""
    summary: str = ""
    rounds: list = field(default_factory=list)
    resolved_round: int | None = None

    @property
    def seq(self) -> int:
        return parse_finding_id(self.id)[1]

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    def max_consecutive_rounds(self) -> int:
        """未解消のまま連続して挙げられたラウンド数の最大値（無進捗判定に使う）。"""
        best = 0
        run = 0
        previous = None
        for value in sorted(set(self.rounds)):
            run = run + 1 if previous is not None and value == previous + 1 else 1
            previous = value
            best = max(best, run)
        return best


@dataclass
class Attempt:
    """1 回の是正試行の宣言（機械比較可能ヘッダ）。"""

    number: int
    round: int
    finding_ids: list
    root_cause: str
    change_kind: str
    targets: list
    diagnosis: str = ""


@dataclass
class Result:
    """Attempt の処置結果（実測 touched-set の記録先・追記のみ）。"""

    attempt: int
    finding_ids: list
    touched: list
    outcome: str
    note: str = ""


@dataclass
class Karte:
    issue: int
    findings: list = field(default_factory=list)
    attempts: list = field(default_factory=list)
    results: list = field(default_factory=list)

    # --- 参照 ---
    def finding(self, finding_id: str):
        for item in self.findings:
            if item.id == finding_id:
                return item
        return None

    def open_findings(self) -> list:
        return [item for item in self.findings if item.is_open]

    def next_seq(self) -> int:
        return max((item.seq for item in self.findings), default=0) + 1

    def next_attempt_number(self) -> int:
        return max((item.number for item in self.attempts), default=0) + 1

    def attempt(self, number: int):
        for item in self.attempts:
            if item.number == number:
                return item
        return None

    def results_for(self, number: int) -> list:
        return [item for item in self.results if item.attempt == number]

    def touched_of(self, number: int) -> list:
        touched: list = []
        for item in self.results_for(number):
            for entry in item.touched:
                if entry not in touched:
                    touched.append(entry)
        return touched

    def attempts_for_finding(self, finding_id: str) -> list:
        return [item for item in self.attempts if finding_id in item.finding_ids]


# --- パース ------------------------------------------------------------------


def parse(text: str) -> Karte:
    """カルテ文書全体をパースする。書式違反は :class:`KarteFormatError`。"""
    issue = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        matched = DOC_HEADER_RE.match(line)
        if matched:
            issue = int(matched.group(1))
        break
    if issue is None:
        raise KarteFormatError("先頭行が '# Karte: issue-<N>' でない（カルテ書式ではない）")

    karte = Karte(issue=issue)
    for block in parse_blocks(text):
        if block.section == SECTION_FINDINGS:
            karte.findings.append(_finding_from_block(block, issue))
        elif block.section == SECTION_ATTEMPTS:
            if ATTEMPT_TITLE_RE.match(block.title):
                karte.attempts.append(_attempt_from_block(block))
            elif RESULT_TITLE_RE.match(block.title):
                karte.results.append(_result_from_block(block))
            else:
                raise KarteFormatError(
                    f"{block.lineno} 行目: '## {SECTION_ATTEMPTS}' 配下の見出しは "
                    f"'Attempt <k>' か 'Result <k>' のみ: {block.title!r}"
                )
        else:
            raise KarteFormatError(
                f"{block.lineno} 行目: 未知のセクション {block.section!r} 配下のブロック "
                f"{block.title!r}（許可されるのは '{SECTION_FINDINGS}' と '{SECTION_ATTEMPTS}'）"
            )

    seen = set()
    for item in karte.findings:
        if item.id in seen:
            raise KarteFormatError(f"finding ID が台帳内で重複している: {item.id}")
        seen.add(item.id)
    numbers = set()
    for item in karte.attempts:
        if item.number in numbers:
            raise KarteFormatError(f"Attempt 番号が重複している: {item.number}")
        numbers.add(item.number)
    for item in karte.results:
        if item.attempt not in numbers:
            raise KarteFormatError(f"Result が指す Attempt が存在しない: {item.attempt}")
    karte.findings.sort(key=lambda item: item.seq)
    karte.attempts.sort(key=lambda item: item.number)
    return karte


def _finding_from_block(block: Block, issue: int) -> Finding:
    issue_of_id, _seq = parse_finding_id(block.title)
    if issue_of_id != issue:
        raise KarteFormatError(
            f"{block.lineno} 行目: finding ID の issue 番号が文書と食い違う: "
            f"{block.title}（文書は issue-{issue}）"
        )
    resolved_round = block.fields.get("resolved_round", "")
    resolved = None
    if isinstance(resolved_round, str) and resolved_round.strip():
        if not resolved_round.strip().isdigit():
            raise KarteFormatError(
                f"{block.lineno} 行目: resolved_round は整数: {resolved_round!r}"
            )
        resolved = int(resolved_round.strip())
    return Finding(
        id=block.title,
        status=_require_enum(block, "status", FINDING_STATUSES),
        harm=_require_enum(block, "harm", HARM_LEVELS),
        harm_detail=_require_nonempty(block, "harm_detail"),
        locus=str(block.fields.get("locus", "")).strip(),
        summary=_require_nonempty(block, "summary"),
        rounds=_require_int_list(block, "rounds"),
        resolved_round=resolved,
    )


def _attempt_from_block(block: Block) -> Attempt:
    number = int(ATTEMPT_TITLE_RE.match(block.title).group(1))
    rounds = _require_int_list(block, "round")
    if len(rounds) != 1:
        raise KarteFormatError(f"{block.lineno} 行目: 'round' は単一の整数: {block.title}")
    return Attempt(
        number=number,
        round=rounds[0],
        finding_ids=validate_finding_ids(block.fields.get("finding_ids", [])),
        root_cause=validate_slug(_require_nonempty(block, "root_cause"), "root_cause"),
        change_kind=_require_enum(block, "change_kind", CHANGE_KINDS),
        targets=validate_targets(block.fields.get("targets", [])),
        diagnosis=str(block.fields.get("diagnosis", "")).strip(),
    )


def _result_from_block(block: Block) -> Result:
    attempt_numbers = _require_int_list(block, "attempt")
    if len(attempt_numbers) != 1:
        raise KarteFormatError(f"{block.lineno} 行目: 'attempt' は単一の整数: {block.title}")
    declared = int(RESULT_TITLE_RE.match(block.title).group(1))
    if attempt_numbers[0] != declared:
        raise KarteFormatError(
            f"{block.lineno} 行目: 見出し 'Result {declared}' と 'attempt: "
            f"{attempt_numbers[0]}' が食い違う"
        )
    return Result(
        attempt=declared,
        finding_ids=validate_finding_ids(block.fields.get("finding_ids", [])),
        touched=check_list(block.fields.get("touched", []), "touched"),
        outcome=_require_enum(block, "outcome", OUTCOMES),
        note=str(block.fields.get("note", "")).strip(),
    )


# --- レビューレポート（ingest-review の入力） ---------------------------------


NEW_FINDING_TITLES = ("new", "NEW", "new-finding")


@dataclass
class ReviewFinding:
    """レビューレポート 1 件分（台帳へ取り込む前の素）。"""

    title: str
    finding_id: str | None  # None＝``### new``＝採番を CLI に委ねる
    harm: str
    harm_detail: str
    locus: str
    summary: str
    lineno: int


def parse_review(text: str, issue: int) -> list:
    """レビューレポートをパースする（``### F-<issue>-<seq>`` か ``### new`` のブロック列）。

    ``harm`` 欄の欠落・不正な ID 形式・要約欠落はすべて集めて 1 度に報告する
    （1 件ずつ往復させない）。1 件でもあれば :class:`KarteFormatError`（fail-close）。
    """
    blocks = parse_blocks(text)
    if not blocks:
        raise KarteFormatError(
            "レビューレポートに finding ブロック（`### F-<issue>-<seq>` か `### new`）が無い"
        )
    findings: list = []
    errors: list = []
    for block in blocks:
        if block.section not in (None, SECTION_FINDINGS):
            errors.append(
                f"{block.lineno} 行目: レビューレポートのセクションは "
                f"'{SECTION_FINDINGS}' のみ（'{block.section}' は不可）"
            )
            continue
        finding_id = None
        if block.title not in NEW_FINDING_TITLES:
            try:
                issue_of_id, _seq = parse_finding_id(block.title)
            except KarteFormatError as exc:
                errors.append(f"{block.lineno} 行目: {exc}")
                continue
            if issue_of_id != issue:
                errors.append(
                    f"{block.lineno} 行目: finding ID の issue 番号が対象と違う: "
                    f"{block.title}（対象は issue-{issue}）"
                )
                continue
            finding_id = block.title
        try:
            findings.append(
                ReviewFinding(
                    title=block.title,
                    finding_id=finding_id,
                    harm=_require_enum(block, "harm", HARM_LEVELS),
                    harm_detail=_require_nonempty(block, "harm_detail"),
                    locus=check_scalar(block.fields.get("locus", ""), "locus"),
                    summary=_require_nonempty(block, "summary"),
                    lineno=block.lineno,
                )
            )
        except KarteFormatError as exc:
            errors.append(str(exc))
    if errors:
        raise KarteFormatError("レビューレポートの検証に失敗:\n  - " + "\n  - ".join(errors))
    return findings


# --- バリデータ（CLI 入力にも使う） -------------------------------------------


def validate_slug(value: str, what: str) -> str:
    text = check_scalar(value, what)
    if not SLUG_RE.match(text):
        raise KarteFormatError(
            f"{what} は slug（英小文字・数字で始まり、以降 a-z 0-9 . _ - のみ）: {value!r}"
        )
    return text


def validate_targets(values) -> list:
    targets = check_list(values, "targets")
    if not targets:
        raise KarteFormatError(
            "targets は 1 つ以上必要（触った関数/クラス単位・例 review_system/forms.py::build_attrs）"
        )
    return targets


def validate_finding_ids(values) -> list:
    ids = check_list(values, "finding_ids")
    if not ids:
        raise KarteFormatError("finding_ids は 1 つ以上必要（指摘↔診断↔処置結果を ID で結合する）")
    for item in ids:
        parse_finding_id(item)
    return ids


def validate_change_kind(value: str) -> str:
    text = check_scalar(value, "change_kind")
    if text not in CHANGE_KINDS:
        raise KarteFormatError(f"change_kind は {list(CHANGE_KINDS)} のいずれか: {value!r}")
    return text


# --- 同一指摘の再発番検出 -----------------------------------------------------


def normalize_text(value: str) -> str:
    """比較用の正規化（小文字化・英数字以外を空白に畳む・空白圧縮）。"""
    lowered = str(value).lower()
    collapsed = re.sub(r"[^0-9a-z぀-ヿ一-鿿]+", " ", lowered)
    return " ".join(collapsed.split())


def _tokens(value: str) -> frozenset:
    return frozenset(t for t in normalize_text(value).split() if t not in _STOPWORDS)


def _jaccard(left: frozenset, right: frozenset) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


DUPLICATE_JACCARD_THRESHOLD = 0.6


def is_same_finding(summary_a: str, locus_a: str, summary_b: str, locus_b: str) -> bool:
    """「同一指摘に新しい ID を振り直した」かどうかの決定論判定。

    2 つの独立した信号の OR:
      * 要約の正規化文字列が完全一致（locus は問わない）。
      * locus が一致し、かつ要約トークンの Jaccard 係数が閾値以上。
    """
    if normalize_text(summary_a) and normalize_text(summary_a) == normalize_text(summary_b):
        return True
    if normalize_text(locus_a) and normalize_text(locus_a) == normalize_text(locus_b):
        return _jaccard(_tokens(summary_a), _tokens(summary_b)) >= DUPLICATE_JACCARD_THRESHOLD
    return False


# --- シリアライズ -------------------------------------------------------------


def _emit(lines: list, key: str, value) -> None:
    lines.append(f"{key}: {format_value(value)}")


def render_finding(finding: Finding) -> str:
    lines = [f"### {finding.id}"]
    _emit(lines, "status", finding.status)
    _emit(lines, "harm", finding.harm)
    _emit(lines, "harm_detail", finding.harm_detail)
    _emit(lines, "locus", finding.locus)
    _emit(lines, "summary", finding.summary)
    _emit(lines, "rounds", finding.rounds)
    _emit(lines, "resolved_round", "" if finding.resolved_round is None else finding.resolved_round)
    return "\n".join(lines) + "\n"


def render_attempt(attempt: Attempt) -> str:
    lines = [f"### Attempt {attempt.number}"]
    _emit(lines, "round", attempt.round)
    _emit(lines, "finding_ids", attempt.finding_ids)
    _emit(lines, "root_cause", attempt.root_cause)
    _emit(lines, "change_kind", attempt.change_kind)
    _emit(lines, "targets", attempt.targets)
    _emit(lines, "diagnosis", attempt.diagnosis)
    return "\n".join(lines) + "\n"


def render_result(result: Result) -> str:
    lines = [f"### Result {result.attempt}"]
    _emit(lines, "attempt", result.attempt)
    _emit(lines, "finding_ids", result.finding_ids)
    _emit(lines, "touched", result.touched)
    _emit(lines, "outcome", result.outcome)
    _emit(lines, "note", result.note)
    return "\n".join(lines) + "\n"


def dumps(karte: Karte) -> str:
    """カルテ全体を文字列化する（``## Attempts`` を最後に置き、追記が必ずそこに入る）。"""
    parts = [
        f"# Karte: issue-{karte.issue}\n",
        f"<!-- karte-format: {FORMAT_VERSION} -->\n",
        f"\n## {SECTION_FINDINGS}\n",
    ]
    for finding in sorted(karte.findings, key=lambda item: item.seq):
        parts.append("\n" + render_finding(finding))
    parts.append(f"\n## {SECTION_ATTEMPTS}\n")
    blocks = [(item.number, 0, render_attempt(item)) for item in karte.attempts]
    blocks += [(item.attempt, 1, render_result(item)) for item in karte.results]
    for _number, _kind, body in sorted(blocks, key=lambda item: (item[0], item[1])):
        parts.append("\n" + body)
    return "".join(parts)


def new_karte(issue: int) -> Karte:
    return Karte(issue=int(issue))
