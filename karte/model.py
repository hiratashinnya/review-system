"""カルテ書式のデータモデル・パーサ・シリアライザ・バリデータ。

書式（``tmp/_karte/issue-<N>.md``）:

    # Karte: issue-307

    ## Findings

    ### F-307-01
    status: open
    harm: real
    harm_detail: required 属性が消え必須入力が素通りする
    severity: blocker
    scope: in
    disposition: fix-here
    deferred_to:
    waived_by:
    waived_reason:
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

改ざん防止の機械的裏付けと既知の限界（Issue #363 F-363-09）:
  * この追記規律は CLI（本モジュール・``karte/cli.py``）が既存 Attempt/Result への再実行を
    ``KarteUsageError`` で拒否することで守られる。それに加え ``.claude/settings.json`` の
    ``permissions.deny`` に ``Edit(/tmp/_karte/**)`` を登録し、
    Edit/Write 系ツールによる ``tmp/_karte/**`` への直接書込みを全ロール共通で拒否する
    （是正当事者自身を含む——権限規則はロールを区別しないので例外を作らない）。
    ``python3 -m karte`` 経由の追記はこの deny の対象外で従来どおり機能する。
    ``Edit`` 規則は ``Write`` も覆うため、``Write(/tmp/_karte/**)`` 専用のエントリは置かない
    （置くと Claude Code が "never matches" 警告を出す。経緯は
    ``.ai/rationale/karte-deny-write-entry.md``）。**台帳の保護は実際には二層で成立している**。
    非隔離で動く主文脈には ``permissions.deny`` が発火する（実測：``Edit`` エントリのみの状態で
    メインチェックアウトの ``tmp/_karte/probe-pattern-522.md`` への ``Write`` が
    "File is in a directory that is denied by your permission settings." で拒否された）。
    隔離ロール（是正・実装当事者）には worktree isolation が同じ書込みを構造的に拒否する
    （実測：隔離 worktree からメインチェックアウトの同パスへの ``Write`` が "This agent is
    isolated in the worktree ... Edit the worktree copy of this file instead of the
    shared-checkout path." で拒否された。自分の worktree 内への ``Write``/``Edit`` は成功するが、
    そこは CLI が参照しない場所であり本物の台帳ではない）。
  * **既知の限界**：この deny は Claude Code の Edit/Write ツール経由の書込みだけを塞ぐ。
    Bash 経由の ``sed -i``・``tee``・シェルリダイレクト等でのファイル改変には掛からない。
    多層防御の一枚であって sandbox ではない（``.claude/hooks/agent-command-gate.sh`` の
    静的検査と同じ制約＝Issue #129）。訂正が必要な Result の内容誤りは、当事者が
    この防御を回避して直接書き換えるのではなく、主文脈による確認つき訂正、または
    安全な訂正用 verb の新設（本 Issue の範囲外）等、当事者以外が介在する経路を通すこと。

スコープ外指摘の一本化（Issue #495）:
  ``## Findings`` は**スコープの内外を問わない単一の指摘台帳**である。スコープ外の指摘を
  別のセクション・別の経路（チャットでの列挙）へ逃がすと、実害判定（``harm``）・カルテ記録・
  ``status`` の verdict をまとめて迂回でき、実害ありの指摘が未処置のまま ``clean`` を
  通過する（PR #490 でこれが起き、Issue #493 が merge 後に流出した）。よって
  * ``scope``（``in``/``out``）は**申告**として残すが**免除力を持たない**、
  * ``harm: real`` にはオーナー判断（``disposition``）の記録を要求し、
  * 未決定のまま残る間は verdict を ``clean`` にしない、
  という3点で経路を1本に閉じる。``issue-implementer``/``issue-fixer`` のハンドオフ
  ``out_of_scope_findings`` も、同じ書式の finding ブロックへ写して ``ingest-review``
  （実行するのは主文脈）でこの列に取り込む。

``harm_detail`` の内容 lint（Issue #511）:
  ``harm_detail`` は**放置時の実害だけ**を書く欄で、処置方針（「対応不要」「別 Issue」）や
  判断経緯（「オーナー確認済み」「新規発生ではない」）を書く欄ではない。
  :func:`check_harm_detail` が :func:`parse_review`（＝``ingest-review`` の入力）に対して
  これを機械的に検査し、違反はレポート全体の取り込みごと拒否する（fail-close）。
  既知の誤検出は :mod:`karte.allowlist` へ**理由付きで**登録して抑制する。
  **既存カルテを読む :func:`parse` 側には掛けない**（``scope`` 必須化と同じ移行方針）。

値の書式は「1行 1 ``key: value``」のみ（複数行の自由記述は持たない＝決定論パースのため）。
``[a, b]`` はリスト、それ以外はスカラ文字列として解釈する。

解析・検証の部品（語彙・値/ブロックのパーサ・``disposition``・``harm_detail`` lint・レビュー
レポートのパーサ等）は責務別のモジュールへ分け、公開名は本モジュールから再エクスポートする
（Issue #746・移設した設計理由は ``.ai/rationale/karte-module-split.md``）。

依存仕様: :mod:`karte` の docstring（Issue #307「カルテの実体」「finding ID による結合」
「Attempt の機械比較可能ヘッダ」）／Issue #495「提案挙動」1〜6（finding の一本化・``scope``・
``disposition``・verdict ゲート・``deferred`` を ``resolved`` にしない・ハンドオフの取り込み）／
Issue #503「提案挙動」（``deferred``/``waived`` の除外を単一の述語
:attr:`Finding.needs_remediation` へ集約し、verdict・``check``・無進捗検知が共有する）・
「観測2」（``change_kind`` に文書のみの変更を表す ``doc`` を追加し、既存の ``config`` 記録は
遡って読み替えない）／Issue #511「提案挙動」（``harm_detail`` に処置方針・経緯の語彙を
検出したら取り込みごと拒否し、該当行と検出語を示す）。
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .block_fields import (
    optional_enum as _optional_enum,
    require_enum as _require_enum,
    require_int_list as _require_int_list,
    require_nonempty as _require_nonempty,
)
from .block_parser import Block, parse_blocks
from .disposition import (
    DISPOSITION_ALL_KEYS,
    DISPOSITION_REQUIRED_KEYS,
    Disposition,
    parse_disposition,
)
from .field_validators import (
    validate_change_kind,
    validate_finding_ids,
    validate_slug,
    validate_targets,
)
from .finding_id import format_finding_id, parse_finding_id
from .format_error import KarteFormatError
from .harm_detail_lint import (
    DISPOSITION_TERMS,
    HARM_DETAIL_FORBIDDEN_TERMS,
    PROCESS_TERMS,
    check_harm_detail,
    find_harm_detail_terms,
    normalize_for_term_match,
)
from .int_args import matched_int, require_ascii_int
from .review_block import DISTINCT_FROM_KEY
from .review_finding import ReviewFinding
from .review_report import parse_review
from .value_codec import check_list, check_scalar, format_value, normalize_locus, parse_value
from .vocabulary import (
    ATTEMPT_TITLE_RE,
    CHANGE_KINDS,
    CLEARING_DISPOSITIONS,
    CLEARING_HARM,
    DEFAULT_SCOPE,
    DEFERRED_TO_RE,
    DISPOSITIONS,
    DOC_HEADER_RE,
    FINDING_ID_RE,
    FINDING_STATUSES,
    FORBIDDEN_LIST_ITEM_CHARS,
    FORBIDDEN_VALUE_CHARS,
    HARM_LEVELS,
    KEY_RE,
    NEW_FINDING_TITLES,
    OUTCOMES,
    RESULT_TITLE_RE,
    SCOPES,
    SECTION_ATTEMPTS,
    SECTION_FINDINGS,
    SEVERITIES,
    SLUG_RE,
)

FORMAT_VERSION = 1

# 同一指摘の再発番判定（`is_same_finding`）に使う文字 n-gram の粒度と閾値。
SHINGLE_SIZE = 2
DUPLICATE_SIMILARITY_THRESHOLD = 0.6


@dataclass
class Finding:
    """ID 付き指摘（台帳の 1 行）。"""

    id: str
    status: str = "open"
    harm: str = "real"
    harm_detail: str = ""
    severity: str = "major"
    # ``locus`` はリスト（ミラー複数ファイルの同一欠陥を 1 指摘で指す・Issue #341）。
    locus: list = field(default_factory=list)
    summary: str = ""
    # ``evidence``＝そう言える根拠（読んだファイル/行・実行したコマンドと結果）。
    evidence: str = ""
    # ``expected``＝解消の条件、``recheck``＝次ラウンドの判定手順（ラウンドをまたぐため台帳に持つ）。
    expected: str = ""
    recheck: str = ""
    # ``scope``＝レビューアの申告（免除力なし）。既定は ``scope`` 無しの既存カルテの移行措置。
    scope: str = DEFAULT_SCOPE
    # ``disposition``＝オーナー判断の記録。空文字＝未決定。
    disposition: str = ""
    deferred_to: str = ""
    waived_by: str = ""
    waived_reason: str = ""
    rounds: list = field(default_factory=list)
    resolved_round: int | None = None

    @property
    def seq(self) -> int:
        return parse_finding_id(self.id)[1]

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    @property
    def cleared_by_disposition(self) -> bool:
        """「当該 PR では処置しない」とオーナー判断で決まったか（Issue #495／#503）。

        **``deferred``/``waived`` の除外規則はここ 1 箇所にだけ書く。** ``status`` の
        verdict・``check`` の診断網羅要求・無進捗検知は、いずれもこの述語を経由する
        :attr:`needs_remediation` を通して同じ規則を共有する（Issue #503）。

        **``harm: none`` には解除力を与えない**（:data:`CLEARING_HARM`・オーナー確定
        2026-09-07）。``harm: none`` の finding に ``disposition`` を書いても記録が残るだけで
        verdict は ``no-harm-only`` のまま——実害なしの指摘だけが残った状態はオーナーへ
        打ち上げる（AI が 2 行書いて STOP を消せる経路を作らない）。

        ``status`` を ``resolved`` に倒さないのは、「別 Issue へ移したと書くだけで指摘が
        台帳から消える」経路を作らないため（二層設計）。よってこの述語が ``True`` でも
        finding は ``status: open`` のまま台帳に残る。
        """
        return self.harm == CLEARING_HARM and self.disposition in CLEARING_DISPOSITIONS

    @property
    def needs_remediation(self) -> bool:
        """**この PR で是正が求められている未解消 finding か**（Issue #503・判定の単一点）。

        3 つの判定経路がこの述語だけを共有する:
          * ``status`` の verdict … ``clean`` を妨げる未解消 finding
            （:meth:`Karte.remediation_findings`）。
          * ``check`` の診断網羅要求 … 当該ラウンドで診断（Attempt）が要る finding。
          * 無進捗検知 … 「3 ラウンド連続で未解消」を数える対象。

        Issue #495 の実装は除外を verdict 算出にしか入れておらず、``check`` は
        ``deferred`` の finding にも診断を要求して**毎ラウンド必ず 1 回 block**し
        （Issue #503 観測1）、無進捗検知は誰も直さないと決めた finding を拾って
        ``escalate: yes`` を偽陽性で出していた（同 観測3）。どちらも「常に鳴るゲートは
        本物を検出できなくなる」形で安全機構を形骸化させるため、除外を 1 箇所へ寄せる。
        """
        return self.is_open and not self.cleared_by_disposition

    @property
    def needs_disposition(self) -> bool:
        """``harm: real`` なのにオーナー判断（disposition）が未決定のまま未解消か。

        ``scope`` の値によらない——``scope: out``（スコープ外の申告）は実害判定・記録・
        ゲートのいずれの免除にもならない、が Issue #495 の要点そのもの。
        """
        return self.is_open and self.harm == "real" and not self.disposition

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
        return next((item for item in self.findings if item.id == finding_id), None)

    def open_findings(self) -> list:
        return [item for item in self.findings if item.is_open]

    def open_ids(self) -> set:
        return {item.id for item in self.open_findings()}

    def remediation_findings(self) -> list:
        """**この PR で是正が求められている未解消 finding**（Issue #503・単一の集合）。

        verdict の「``clean`` を妨げる未解消」（``status --json`` の ``blocking_findings``）・
        ``check`` の診断網羅要求・無進捗検知は、いずれもこの 1 つの集合を使う。
        除かれるのは **``harm: real`` かつ** ``deferred``/``waived`` のものだけ
        （:data:`CLEARING_HARM`）。``harm: none`` は ``disposition`` を書いても残る。
        """
        return [item for item in self.findings if item.needs_remediation]

    def undecided_findings(self) -> list:
        """``harm: real`` かつ disposition 未決定のまま未解消の finding（Issue #495）。"""
        return [item for item in self.findings if item.needs_disposition]

    def next_seq(self) -> int:
        return max((item.seq for item in self.findings), default=0) + 1

    def next_attempt_number(self) -> int:
        return matched_int(str(max((a.number for a in self.attempts), default=0) + 1), KarteFormatError, "Attempt 番号")

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
            issue = matched_int(matched.group(1), KarteFormatError, "カルテ見出しの issue")
        break
    if issue is None:
        raise KarteFormatError("先頭行が '# Karte: issue-<N>' でない（カルテ書式ではない）")

    karte = Karte(issue=issue)
    for block in parse_blocks(text):
        if block.section == SECTION_FINDINGS:
            karte.findings.append(_finding_from_block(block, issue))
        elif block.section == SECTION_ATTEMPTS:
            if attempt_title := ATTEMPT_TITLE_RE.match(block.title):
                karte.attempts.append(_attempt_from_block(block, attempt_title))
            elif result_title := RESULT_TITLE_RE.match(block.title):
                karte.results.append(_result_from_block(block, result_title))
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
        message = f"{block.lineno} 行目: resolved_round は整数: {resolved_round!r}"
        resolved = require_ascii_int(resolved_round.strip(), KarteFormatError(message))
    # ``scope`` は台帳側では任意（欠落は DEFAULT_SCOPE）。新規取り込み側で必須にしてある。
    disposition = parse_disposition(block)
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
        scope=_optional_enum(block, "scope", SCOPES, DEFAULT_SCOPE),
        disposition=disposition.kind,
        deferred_to=disposition.deferred_to,
        waived_by=disposition.waived_by,
        waived_reason=disposition.waived_reason,
        rounds=_require_int_list(block, "rounds"),
        resolved_round=resolved,
    )


def _attempt_from_block(block: Block, title: re.Match[str]) -> Attempt:
    number = matched_int(title.group(1), KarteFormatError, "Attempt 見出しの番号")
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


def _result_from_block(block: Block, title: re.Match[str]) -> Result:
    attempt_numbers = _require_int_list(block, "attempt")
    if len(attempt_numbers) != 1:
        raise KarteFormatError(f"{block.lineno} 行目: 'attempt' は単一の整数: {block.title}")
    declared = matched_int(title.group(1), KarteFormatError, "Result 見出しの番号")
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

    類似度による判定で locus の交差を必須にしているのは、別の箇所への指摘（例「docstring が古い」）を
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
    _emit(lines, "scope", finding.scope)
    _emit(lines, "disposition", finding.disposition)
    _emit(lines, "deferred_to", finding.deferred_to)
    _emit(lines, "waived_by", finding.waived_by)
    _emit(lines, "waived_reason", finding.waived_reason)
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
