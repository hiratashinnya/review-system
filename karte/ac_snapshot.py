"""Issue #801: GitHub Issue 本文からレビュアー用 AC snapshot を正規化する。

snapshot はレビュー開始時の主文脈が作成し、Codex へも同一内容を渡す。
チェックと本文は明示的に凍結し、レビューアの自己申告で置換しない。
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from .format_error import KarteFormatError

HEADING = re.compile(r"^(#{1,6})\s+(Acceptance criteria|受け入れ基準)\s*$", re.I)
NEXT_HEADING = re.compile(r"^(#{1,6})\s+")
CHECKBOX = re.compile(r"^(\s*[-*]\s+)\[([ xX])\](\s+\S.*)$")
ITEM = re.compile(r"^\s*(?:[-*]|[1-9][0-9]*[.)])\s+(\S.*)$")


@dataclass(frozen=True)
class AC:
    text: str
    checked: bool | None
    line_number: int


def from_issue_body(body: str) -> tuple[AC, ...]:
    """Acceptance criteria の各itemを本文順で抽出。非checkboxは評価のみ、更新不可。"""
    if not isinstance(body, str):
        raise KarteFormatError("Issue本文は文字列であること")
    in_ac, level, found, items = False, 0, False, []
    for number, line in enumerate(body.splitlines(), start=1):
        heading = HEADING.fullmatch(line.strip())
        if heading:
            if found:
                raise KarteFormatError("Issue本文のAcceptance criteriaセクションが重複")
            in_ac, level, found = True, len(heading.group(1)), True
            continue
        h = NEXT_HEADING.match(line)
        if in_ac and h and len(h.group(1)) <= level:
            in_ac = False
        if not in_ac:
            continue
        checkbox = CHECKBOX.fullmatch(line)
        if checkbox:
            items.append(AC(checkbox.group(3).strip(), checkbox.group(2).lower() == "x", number))
        elif match := ITEM.match(line):
            items.append(AC(match.group(1).strip(), None, number))
    if len({(item.text, item.checked is not None) for item in items}) != len(items):
        raise KarteFormatError("同一文言のACが重複しており照合できない")
    return tuple(items)


def digest(items: tuple[AC, ...]) -> str:
    """AC本文・順序・checkbox状態に束縛した決定論的digest。"""
    data = [{"text": item.text, "checked": item.checked} for item in items]
    return sha256(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
