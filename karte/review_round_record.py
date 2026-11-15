"""受理済み review round のレシート。finding 0 件の round も表現する。

これは保存形式の準備のみ。review 出力の受理規約と AC 判定の形式は
Issue #801 のオーナー判断が確定するまで変更しない。
"""

from dataclasses import dataclass
import re

from .format_error import KarteFormatError
from .int_args import matched_int

TITLE_RE = re.compile(r"^Review Round ([1-9][0-9]*)\Z")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class ReviewRound:
    number: int
    digest: str
    source: str = ""  # 旧レシート互換。新しいレビューは原本の相対パスを必須保存する。


def from_block(block, issue: int) -> ReviewRound:
    """未知キーや不正 digest は fail-close にする。"""
    matched = TITLE_RE.fullmatch(block.title)
    if matched is None:
        raise KarteFormatError(f"{block.lineno} 行目: Review Round 見出しが不正: {block.title!r}")
    if set(block.fields) not in ({"digest"}, {"digest", "source"}):
        raise KarteFormatError(f"{block.lineno} 行目: Review Round のキーは digest と任意の source のみ")
    digest = block.fields["digest"]
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        raise KarteFormatError(f"{block.lineno} 行目: Review Round の digest は sha256 の 64 桁小文字 hex")
    number = matched_int(matched.group(1), KarteFormatError, "Review Round 番号")
    source = block.fields.get("source", "")
    if source and source != f"tmp/_karte/issue-{issue}-review-round-{number}.md":
        raise KarteFormatError(f"{block.lineno} 行目: Review Round の原本参照が不正")
    return ReviewRound(number, digest, source)


def render_round(record: ReviewRound) -> str:
    """round の安全な書き出し。"""
    if record.number < 1 or not DIGEST_RE.fullmatch(record.digest):
        raise KarteFormatError("Review Round の番号または digest が不正")
    if record.source and not record.source.endswith(f"-review-round-{record.number}.md"):
        raise KarteFormatError("Review Round の source が不正")
    extra = f"source: {record.source}\n" if record.source else ""
    return f"### Review Round {record.number}\ndigest: {record.digest}\n{extra}"
