"""``harm_detail`` の内容 lint（処置方針・判断経緯の語彙を取り込みごと拒否する・Issue #511）。

設計理由は ``.ai/rationale/karte-module-split.md``「karte/harm_detail_lint.py」を参照。
"""

from .allowlist import is_allowlisted
from .block_parser import Block
from .format_error import KarteFormatError

DISPOSITION_TERMS = (
    "対応不要",
    "処置不要",
    "修正不要",
    "対応は不要",
    "別 Issue",
    "別の Issue",
    "申し送り",
    "繰り越し",
    "据え置き",
    "次スプリント",
    "本 PR で直す",
    "fix-here",
    "deferred",
    "waived",
)
PROCESS_TERMS = (
    "オーナー確認済み",
    "新規発生ではない",
    "差分範囲外",
    "スコープ外",
)
HARM_DETAIL_FORBIDDEN_TERMS = DISPOSITION_TERMS + PROCESS_TERMS


def normalize_for_term_match(value: str) -> str:
    """語彙照合用の正規化（ASCII 大小文字を畳み、空白をすべて除去する・記号は落とさない）。"""
    return "".join(str(value).casefold().split())


def find_harm_detail_terms(harm_detail: str) -> list:
    """``harm_detail`` に含まれる禁止語彙を出現順ではなく定義順で返す（無ければ空）。"""
    text = normalize_for_term_match(harm_detail)
    return [
        term
        for term in HARM_DETAIL_FORBIDDEN_TERMS
        if normalize_for_term_match(term) in text
    ]


def check_harm_detail(harm_detail: str, *, issue: int, block: Block) -> str:
    """``harm_detail`` の内容 lint（fail-close・Issue #511）。

    禁止語彙を含み、かつ :mod:`karte.allowlist` に理由付きで登録されていなければ
    :class:`KarteFormatError` を送出する。呼び出し元が他の検証エラーと同じ列に集約する。
    """
    hits = [
        term
        for term in find_harm_detail_terms(harm_detail)
        if is_allowlisted(issue, term, harm_detail) is None
    ]
    if hits:
        raise KarteFormatError(
            f"{block.lineno} 行目 '{block.title}': harm_detail に処置方針・判断経緯の語彙が"
            f"含まれる: {hits}。harm_detail には**放置時の実害**だけを書く"
            "（どこで直すべきかという見立ては書かない。決まったオーナー判断だけが "
            "disposition/deferred_to/waived_reason に載る）。実害の記述としてその語が"
            "不可避なら、まず言い換えを試し、それでも残るなら karte/allowlist.py へ"
            "理由付きで登録する。"
        )
    return harm_detail
