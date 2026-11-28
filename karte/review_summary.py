"""Issue #801: finding 0 件と AC 全件判定の共通 Review Summary 契約。

既存の finding 9 項目は変更しない。Summary は原本中の補助ブロックとし、
未充足/未検証 AC は harm: real の finding 本文へ関連付ける。
"""

from dataclasses import dataclass
import re

from .block_parser import parse_blocks
from .format_error import KarteFormatError
from .int_args import ascii_int_or_none
from .review_summary_ac import ACJudgment, finding_refs, judgment

SECTION = "Review Summary"
FINISH_MARKER = "<!-- review-complete -->"
DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class ReviewSummary:
    finding_count: int
    ac_count: int
    ac_snapshot_digest: str
    judgments: tuple[ACJudgment, ...]


def _integer(block, key):
    number = ascii_int_or_none(block.fields.get(key, ""))
    if number is None:
        raise KarteFormatError(f"{block.lineno} 行目: {key} は非負の ASCII 整数が必要")
    return number


def has_summary_controls(text: str) -> bool:
    """フィールド値に含まれる文字列を除き、独立したSummary見出し・完了行を探す。"""
    for raw in text.splitlines():
        line = raw.strip()
        if line == FINISH_MARKER or (line.startswith("## ") and line[3:].strip() == SECTION):
            return True
    return False


def parse_summary(text: str, issue: int) -> ReviewSummary | None:
    """Summary 無しは旧フォーマットとして None。Summary があれば全項目 fail-close。"""
    blocks = parse_blocks(text, allow_preamble=True)
    items = [block for block in blocks if block.section == SECTION]
    if not items:
        if has_summary_controls(text):
            raise KarteFormatError("review-complete マーカーだけで Review Summary がない")
        return None
    if text.rstrip().splitlines()[-1].strip() != FINISH_MARKER:
        raise KarteFormatError("Review Summary の最終非空行に独立した review-complete が必要")
    if blocks[-1].section != SECTION or items[0].title != "Summary":
        raise KarteFormatError("Review Summary は最後のセクション、最初のブロックは Summary")
    header = items[0]
    if set(header.fields) != {"finding_count", "ac_count", "ac_snapshot_digest"}:
        raise KarteFormatError("Summary のキーは finding_count/ac_count/ac_snapshot_digest のみ")
    digest = header.fields["ac_snapshot_digest"]
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        raise KarteFormatError("ac_snapshot_digest は SHA-256 小文字64桁が必要")
    count, ac_count = _integer(header, "finding_count"), _integer(header, "ac_count")
    names, finding_state = finding_refs(blocks)
    if count != len(names):
        raise KarteFormatError(f"finding_count 不一致: 宣言={count} 実際={len(names)}")
    if len(items) != ac_count + 1:
        raise KarteFormatError(f"ac_count 不一致: 宣言={ac_count} 実際={len(items)-1}")
    judgments = tuple(judgment(block, issue, set(names), finding_state) for block in items[1:])
    numbers = [item.number for item in judgments]
    if numbers != list(range(1, ac_count + 1)):
        raise KarteFormatError("AC の番号は1から連続し重複せず昇順であること")
    return ReviewSummary(count, ac_count, digest, judgments)
