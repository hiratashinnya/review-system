"""Issue #801: AC判定とfinding参照の厳密な検査（Summaryから分離）。"""

from dataclasses import dataclass
import re

from .format_error import KarteFormatError
from .int_args import ascii_int_or_none
from .vocabulary import NEW_FINDING_TITLES

AC_TITLE_RE = re.compile(r"AC ([1-9][0-9]*)\Z")
RESULTS = frozenset(("satisfied", "not_met", "unverified"))


@dataclass(frozen=True)
class ACJudgment:
    number: int
    result: str
    evidence: str
    finding_refs: tuple[str, ...]


def finding_refs(blocks):
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


def judgment(block, issue, existing, harm):
    matched = AC_TITLE_RE.fullmatch(block.title)
    if not matched:
        raise KarteFormatError(f"{block.lineno} 行目: AC 見出しは 'AC <番号>' のみ")
    number = ascii_int_or_none(matched.group(1))
    if number is None:
        raise KarteFormatError(f"{block.lineno} 行目: AC番号が大きすぎる")
    if set(block.fields) != {"result", "evidence", "finding_refs"}:
        raise KarteFormatError(f"{block.lineno} 行目: AC のキーは result/evidence/finding_refs のみ")
    result = block.fields["result"]
    evidence = block.fields["evidence"]
    refs = block.fields["finding_refs"]
    if not isinstance(result, str) or result not in RESULTS or not isinstance(evidence, str) or not evidence.strip():
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


