"""カルテ書式のデータモデル・パーサ・シリアライザ・バリデータ。

書式（``tmp/_karte/issue-<N>.md``）:

    # Karte: issue-307

    ## Findings

    ### F-307-01
    status: open
    harm: real
    harm_detail: required 属性が消え必須入力が素通りする
    severity: blocker
    locus: [review_system/forms.py::build_attrs, .codex/forms.toml::build_attrs]
    summary: build_attrs が既存 attrs を破棄している
    evidence: forms.py:120 を Read。attrs = {...} で辞書を作り直している
    expected: 既存 attrs を保ったまま追加分だけマージする
    recheck: required 付きフィールドを描画し required 属性が残ることを確認する
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
import unicodedata
from dataclasses import dataclass, field

FORMAT_VERSION = 1

CHANGE_KINDS = ("logic", "data-structure", "interface", "config", "test", "revert")
HARM_LEVELS = ("real", "none")
# 指摘の優先度（``harm`` とは独立の軸。``harm: none`` でも ``severity: major`` はあり得る）。
SEVERITIES = ("blocker", "major", "minor")
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

# 同一指摘の再発番判定（`is_same_finding`）に使う文字 n-gram の粒度と閾値。
SHINGLE_SIZE = 2
DUPLICATE_SIMILARITY_THRESHOLD = 0.6


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


def normalize_locus(value) -> list:
    """``locus`` をリストへ正規化する（スカラ 1 件でもリストでも受ける）。

    レビューアが 1 箇所しか書かないときに ``[...]`` を強制すると書き味が悪いのでスカラを許し、
    台帳側は常にリストで持つ（表示・比較の分岐を 1 箇所に閉じる）。空は空リスト＝任意キー。

    **スカラ経路もリスト要素と同じ文字検査を通す**（:data:`FORBIDDEN_LIST_ITEM_CHARS`）。
    ここを緩めると、角括弧を省いて ``locus: a.md::x, b.toml::x`` と書いたときに 1 要素として
    受理され、:func:`format_value` が ``[a.md::x, b.toml::x]`` と書き出すので、**台帳を読み直した
    時点で 2 要素へ静かに割れる**。:func:`is_same_finding` は locus の交差で再発番を判定するため、
    レポート側（1 要素）と台帳側（2 要素）で照合面がズレ、**同一指摘の再発番を見逃す**方向に効く
    ——locus を複数化した目的そのものを裏切るので、fail-close で拒否する。
    """
    if isinstance(value, (list, tuple)):
        return check_list(value, "locus")
    text = check_scalar(value, "locus")
    return check_list([text], "locus") if text else []


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


def parse_blocks(text: str, *, allow_preamble: bool = False) -> list:
    """``## Section`` / ``### Title`` ＋ ``key: value`` 行の決定論パーサ。

    解釈できない行が 1 行でもあれば :class:`KarteFormatError`（fail-close）。

    ``allow_preamble``
        最初の ``### `` 見出しより**前**の自由記述行（レポート冒頭のタイトル・総括）を
        読み飛ばす。レビューレポート（レビューアが書く入力）専用の緩和で、カルテ本体
        （機械が書き機械が読む正本）は既定どおり 1 行でも解釈できなければ拒否する。
        1 件目のブロックに入った後は緩和しない——要約の折り返し行を黙って捨てると
        指摘の内容が欠落するため、そこは fail-close のままにする。
    """
    blocks: list = []
    section = None
    current = None
    seen_block = False
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("<!--"):
            continue
        if line.startswith("### "):
            current = Block(section, line[4:].strip(), {}, lineno)
            blocks.append(current)
            seen_block = True
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
        if allow_preamble and not seen_block and not matched:
            continue  # 1 件目の `### ` より前の自由文だけを無視する（レビューレポート限定）。
            # `key: value` 形の行は preamble でも黙って捨てず拒否する（K-10：無言の欠落防止）。
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
    severity: str = "major"
    # ``locus`` は**リスト**（Issue #341 レビュー feedback）。同じ欠陥が対称ミラー
    # （`.claude/` ↔ `.codex/` 等）の複数ファイルに出る本リポジトリでは、1 箇所しか持てないと
    # **同一欠陥が複数 finding に分裂**し、未解消件数が水増しされて `status` の
    # 「同一 finding が N ラウンド連続未解消」判定まで歪む。1 指摘＝1 欠陥のまま複数箇所を指せる。
    locus: list = field(default_factory=list)
    summary: str = ""
    # ``evidence``＝そう言える**根拠**（読んだファイル/行・実行したコマンドと結果）。
    # ``harm_detail``（実害の内容）と混ざると、再レビュー側が「本当に実体で確認したのか」を
    # 検証できない。`pr-reviewer` の「指摘の根拠は必ず実体で確認する」を書式側で要求する。
    evidence: str = ""
    # ``expected`` / ``recheck`` は**ラウンドをまたぐ**情報なので台帳に持つ（Issue #341 F-341-01）。
    # ``expected``＝どうなっていれば解消か（``issue-fixer`` の Step 1 診断の入力契約）。
    # ``recheck``＝次ラウンドで何を実行して解消を判定するか（再レビュー側の判定根拠）。
    # ここに持たないと 2 ラウンド目以降に台帳から復元できず、是正も再検証も
    # 「レビューアのチャット発言を覚えている」ことに依存してしまう。
    expected: str = ""
    recheck: str = ""
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
        severity=_require_enum(block, "severity", SEVERITIES),
        locus=normalize_locus(block.fields.get("locus", "")),
        summary=_require_nonempty(block, "summary"),
        evidence=_require_nonempty(block, "evidence"),
        expected=_require_nonempty(block, "expected"),
        recheck=_require_nonempty(block, "recheck"),
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

DISTINCT_FROM_KEY = "distinct_from"


def _optional_status(block: Block) -> str:
    """レビューレポートの任意キー ``status``（既定 ``open``）を読む（K-06）。

    ``resolved`` と**書いたときだけ**解消として扱う。値の綴り間違いは既定へ倒さず
    :class:`KarteFormatError`（fail-close）——「resolve」等の誤記を黙って ``open`` に
    落とすと、レビューアの解消宣言が無言で失われる。
    """
    if "status" not in block.fields:
        return "open"
    return _require_enum(block, "status", FINDING_STATUSES)


def _parse_distinct_from(block: Block, issue: int) -> tuple:
    """任意キー ``distinct_from``（再発番判定のペア限定エスケープハッチ・K-05）を読む。

    スカラ（``distinct_from: F-307-01``）とリスト（``distinct_from: [F-307-01, F-307-02]``）の
    両方を受ける。形式違反・対象 issue 違いはここで拒否し、**台帳に実在するか**は
    台帳を持つ CLI 側で検査する（ここは書式の責務だけを負う）。
    """
    raw = block.fields.get(DISTINCT_FROM_KEY, [])
    if isinstance(raw, str):
        raw = [raw] if raw.strip() else []
    ids = check_list(raw, DISTINCT_FROM_KEY)
    for item in ids:
        issue_of_id, _seq = parse_finding_id(item)
        if issue_of_id != issue:
            raise KarteFormatError(
                f"{block.lineno} 行目 '{block.title}': {DISTINCT_FROM_KEY} の finding ID の "
                f"issue 番号が対象と違う: {item}（対象は issue-{issue}）"
            )
    return tuple(ids)


@dataclass
class ReviewFinding:
    """レビューレポート 1 件分（台帳へ取り込む前の素）。"""

    title: str
    finding_id: str | None  # None＝``### new``＝採番を CLI に委ねる
    harm: str
    harm_detail: str
    severity: str
    locus: list
    summary: str
    evidence: str
    expected: str
    recheck: str
    lineno: int
    status: str = "open"          # ``resolved`` と**明示**したときだけ解消（K-06）
    distinct_from: tuple = ()     # 再発番判定を無効化する相手 ID（K-05・ペア限定）


def parse_review(text: str, issue: int) -> list:
    """レビューレポートをパースする（``### F-<issue>-<seq>`` か ``### new`` のブロック列）。

    ``harm`` 欄の欠落・不正な ID 形式・要約欠落はすべて集めて 1 度に報告する
    （1 件ずつ往復させない）。1 件でもあれば :class:`KarteFormatError`（fail-close）。

    レポート冒頭の前書き（``# レビュー結果`` とその下の総括文）は無視する。ブロックが
    1 件も無いときは「解釈できない行」ではなく **finding ブロックが無い** と報告する
    ——書式違反の指摘より「取り込むものが無い」ことの方が呼び出し側の処置に直結する。

    必須キー: ``harm`` / ``harm_detail`` / ``severity`` / ``summary`` / ``evidence`` /
    ``expected`` / ``recheck``（``locus`` は任意）。``severity`` / ``expected`` / ``recheck`` は
    Issue #341 F-341-01 で必須化した——``pr-reviewer`` の出力契約が必須と宣言している一方で
    台帳が持っておらず、2 ラウンド目以降に ``expected``（解消条件）と ``recheck``（再検証手順）を
    復元できなかった。``evidence`` は同レビューの書式 feedback で追加——「そう言える根拠」を
    ``harm_detail``（実害の内容）に混ぜると、再レビュー側が実体確認の有無を検証できない。

    ``locus`` は**スカラでもリストでも書ける**（:func:`normalize_locus` が正規化する）。
    同じ欠陥が対称ミラーの複数ファイルに出るときは ``locus: [a, b]`` と書いて **1 指摘のまま**
    複数箇所を指す——箇所ごとに finding を割ると未解消件数が水増しされ、``status`` の
    「同一 finding が N ラウンド連続未解消」判定まで歪む。

    任意キー:
      ``status``
          ``open``（既定）／``resolved``。**解消は明示宣言でのみ成立する**（K-06）。
          再掲されなかった finding を「不在＝解消」と見なす旧仕様は、部分的なレポートを
          1 回取り込むだけで ``harm: real`` の指摘が消える fail-open だったため廃止した。
      ``distinct_from``
          ``F-<issue>-<seq>``（``[a, b]`` で複数可）。再発番判定（:func:`is_same_finding`）の
          **偽陽性に対する明示的なエスケープハッチ**で、ここに名指しした相手との**ペアに限って**
          判定を無効化する（K-05）。判定そのもの・閾値は動かさない。ID の実在検査は台帳を持つ
          CLI 側（``cmd_ingest_review``）で行う。
    """
    blocks = parse_blocks(text, allow_preamble=True)
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
                    severity=_require_enum(block, "severity", SEVERITIES),
                    locus=normalize_locus(block.fields.get("locus", "")),
                    summary=_require_nonempty(block, "summary"),
                    evidence=_require_nonempty(block, "evidence"),
                    expected=_require_nonempty(block, "expected"),
                    recheck=_require_nonempty(block, "recheck"),
                    lineno=block.lineno,
                    status=_optional_status(block),
                    distinct_from=_parse_distinct_from(block, issue),
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
    """比較用の正規化（``casefold`` ＋ 「文字・数字」以外を区切りへ畳む・空白圧縮）。

    **保持する文字を列挙しない**（K-07）。以前は ``[^0-9a-z ぁ-ヿ 一-鿿]+`` という
    ホワイトリストで畳んでいたため、全角英数・ハングル・アクセント付きラテン・CJK 拡張漢字
    （Ext-A 以降）が丸ごと空白になり、要約がそれらだけで構成されると正規化結果が**空文字**に
    なった。空文字同士は :func:`is_same_finding` の完全一致判定でも n-gram 判定でも
    「同一ではない」と扱われる（:func:`_jaccard` は空集合を 0.0 で返す）ため、
    **再発番を見逃す fail-open** になっていた。

    そこで :mod:`unicodedata` の一般カテゴリで「文字（``L*``）・数字（``N*``）」だけを残し、
    それ以外（記号・句読点・空白・制御）を区切りに畳む。文字体系を列挙しないので、
    新しい文字種が出てきても取りこぼさない（fail-open が構造的に起きない）。

    NFKC 等の互換正規化は**行わない**——全角と半角、丸数字と数字を勝手に同一視すると、
    「別物として起票された指摘」を再発番と誤検出しうる（偽陽性は K-05 の逃げ道と違って
    レビューアが正当な新規指摘を挙げられなくなる方向の害）。畳むのは大小文字だけに留める。
    """
    kept = []
    for char in str(value).casefold():
        kept.append(char if unicodedata.category(char)[0] in ("L", "N") else " ")
    return " ".join("".join(kept).split())


def shingles(value: str, size: int = SHINGLE_SIZE) -> frozenset:
    """比較用の文字 n-gram 集合（既定は bigram）。

    語の区切りに**空白を使わない**（＝空白位置が言い換えで揺れる）ため、空白トークン化は
    使わない。``「既存 attrs を破棄」`` と ``「既存の attrs を破棄」`` は空白トークンでは
    ``が既存`` / ``が既存の`` という別トークンになり、同一指摘なのに一致率が閾値を割る。
    文字 n-gram は言語非依存・決定論的で、語形の揺れ（助詞の挿入・「（再掲）」等の付記）に
    強い。形態素解析器のような外部依存も要らない（標準ライブラリのみの制約）。
    """
    text = normalize_text(value).replace(" ", "")
    if not text:
        return frozenset()
    if len(text) <= size:
        return frozenset([text])
    return frozenset(text[index:index + size] for index in range(len(text) - size + 1))


def _jaccard(left: frozenset, right: frozenset) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def is_same_finding(summary_a: str, locus_a, summary_b: str, locus_b) -> bool:
    """「同一指摘に新しい ID を振り直した」かどうかの決定論判定。

    2 つの独立した信号の OR:
      * 要約の正規化文字列が完全一致（locus は問わない＝一字一句の再掲）。
      * locus が**交差**し、かつ要約の文字 n-gram Jaccard 係数が閾値以上
        （言い換え・付記つきの再掲）。

    locus の交差を必須にしているのは、同じ箇所への**別の**指摘（例「docstring が古い」）を
    誤って同一視しないため——文字 n-gram だけで判定を回すと、短い要約同士が偶然似ただけで
    再発番と誤検出し、レビューアが正当な新規指摘を挙げられなくなる。

    ``locus`` は複数箇所を持てる（Issue #341 レビュー feedback）ので、完全一致ではなく
    **1 箇所でも共通なら同じ箇所とみなす**（``targets`` の交差判定と同じ考え方）。
    完全一致にすると、前ラウンドで 1 箇所だけ直してミラー側が残った再掲を「別物」と誤判定し、
    再発番を見逃す。

    それでも残る偽陽性（同一 locus に出た短い別指摘同士が閾値を超える）には、レビュー
    レポート側の ``distinct_from``（K-05）で**名指ししたペアだけ**判定を外せる。閾値
    :data:`DUPLICATE_SIMILARITY_THRESHOLD` は逃がすために動かさない——「通すために閾値を
    下げる」と、本来検出したい再発番まで一律に見逃す。
    """
    if normalize_text(summary_a) and normalize_text(summary_a) == normalize_text(summary_b):
        return True
    set_a = {normalize_text(item) for item in normalize_locus(locus_a) if normalize_text(item)}
    set_b = {normalize_text(item) for item in normalize_locus(locus_b) if normalize_text(item)}
    if set_a & set_b:
        return (
            _jaccard(shingles(summary_a), shingles(summary_b))
            >= DUPLICATE_SIMILARITY_THRESHOLD
        )
    return False


# --- シリアライズ -------------------------------------------------------------


def _emit(lines: list, key: str, value) -> None:
    lines.append(f"{key}: {format_value(value)}")


def render_finding(finding: Finding) -> str:
    lines = [f"### {finding.id}"]
    _emit(lines, "status", finding.status)
    _emit(lines, "harm", finding.harm)
    _emit(lines, "harm_detail", finding.harm_detail)
    _emit(lines, "severity", finding.severity)
    _emit(lines, "locus", finding.locus)
    _emit(lines, "summary", finding.summary)
    _emit(lines, "evidence", finding.evidence)
    _emit(lines, "expected", finding.expected)
    _emit(lines, "recheck", finding.recheck)
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
