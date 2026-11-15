"""Issue #801: finding 0 件と AC 全件判定の共通 Review Summary 契約。

既存の finding 9 項目は変更しない。Summary は原本中の補助ブロックとし、
未充足/未検証 AC は harm: real の finding 本文へ関連付ける。
"""

from dataclasses import dataclass
import re

from .block_parser import parse_blocks
from .format_error import KarteFormatError
from .int_args import ascii_int_or_none
from .vocabulary import NEW_FINDING_TITLES

SECTION = "Review Summary"
FINISH_MARKER = "<!-- review-complete -->"
DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
AC_TITLE_RE = re.compile(r"AC ([1-9][0-9]*)\Z")
RESULTS = frozenset(("satisfied", "not_met", "unverified"))


@dataclass(frozen=True)
class ACJudgment:
    number: int
    result: str
    evidence: str
    finding_refs: tuple[str, ...]


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


def _finding_refs(blocks):
    """### new の参照は原本内の出現順で new@1, new@2... とする。"""
    names, harm = [], {}
    new_number = 0
    for block in blocks:
        if block.section not in (None, "Findings"):
            continue
        if block.title in NEW_FINDING_TITLES:
            new_number += 1
            name = f"new@{new_number}"
        else:
            name = block.title
        names.append(name)
        harm[name] = block.fields.get("harm")
    return names, harm


def _judgment(block, issue, existing, harm):
    matched = AC_TITLE_RE.fullmatch(block.title)
    if not matched:
        raise KarteFormatError(f"{block.lineno} 行目: AC 見出しは 'AC <番号>' のみ")
    number = _integer(type("B", (), {"fields":{"number":matched.group(1)},"lineno":block.lineno})(), "number")
    if set(block.fields) != {"result", "evidence", "finding_refs"}:
        raise KarteFormatError(f"{block.lineno} 行目: AC のキーは result/evidence/finding_refs のみ")
    result = block.fields["result"]
    evidence = block.fields["evidence"]
    refs = block.fields["finding_refs"]
    if result not in RESULTS or not isinstance(evidence, str) or not evidence.strip():
        raise KarteFormatError(f"{block.lineno} 行目: AC 判定または根拠が不正")
    if not isinstance(refs, list) or len(refs) != len(set(refs)):
        raise KarteFormatError(f"{block.lineno} 行目: finding_refs は重複なしリスト")
    if (result == "satisfied" and refs) or (result != "satisfied" and not refs):
        raise KarteFormatError(f"{block.lineno} 行目: AC判定とfinding_refsが矛盾")
    for ref in refs:
        if ref not in existing:
            raise KarteFormatError(f"{block.lineno} 行目: 存在しないfinding参照: {ref}")
        if harm[ref] != "real":
            raise KarteFormatError(f"{block.lineno} 行目: 未充足/未検証ACのfindingは harm: real が必要: {ref}")
    return ACJudgment(number, result, evidence, tuple(refs))


def parse_summary(text: str, issue: int) -> ReviewSummary | None:
    """Summary 無しは旧フォーマットとして None。Summary があれば全項目 fail-close。"""
    blocks = parse_blocks(text, allow_preamble=True)
    items = [block for block in blocks if block.section == SECTION]
    if not items:
        if FINISH_MARKER in text:
            raise KarteFormatError("review-complete マーカーだけで Review Summary がない")
        return None
    if not text.rstrip().endswith(FINISH_MARKER):
        raise KarteFormatError("Review Summary の末尾に review-complete が必要")
    if blocks[-1].section != SECTION or items[0].title != "Summary":
        raise KarteFormatError("Review Summary は最後のセクション、最初のブロックは Summary")
    header = items[0]
    if set(header.fields) != {"finding_count", "ac_count", "ac_snapshot_digest"}:
        raise KarteFormatError("Summary のキーは finding_count/ac_count/ac_snapshot_digest のみ")
    digest = header.fields["ac_snapshot_digest"]
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        raise KarteFormatError("ac_snapshot_digest は SHA-256 小文字64桁が必要")
    count, ac_count = _integer(header, "finding_count"), _integer(header, "ac_count")
    names, harm = _finding_refs(blocks)
    if count != len(names):
        raise KarteFormatError(f"finding_count 不一致: 宣言={count} 実際={len(names)}")
    if len(items) != ac_count + 1:
        raise KarteFormatError(f"ac_count 不一致: 宣言={ac_count} 実際={len(items)-1}")
    judgments = tuple(_judgment(block, issue, set(names), harm) for block in items[1:])
    numbers = [item.number for item in judgments]
    if numbers != list(range(1, ac_count + 1)):
        raise KarteFormatError("AC の番号は1から連続し重複せず昇順であること")
    return ReviewSummary(count, ac_count, digest, judgments)
