"""Issue #801: GitHub Issue 本文からレビュアー用 AC snapshot を正規化する。

snapshot はレビュー開始時の主文脈が作成し、Codex へも同一内容を渡す。
チェックと本文は明示的に凍結し、レビューアの自己申告で置換しない。
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from .format_error import KarteFormatError
from .ac_snapshot_fence import advance as advance_fence

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
    """AC項目の継続行・子リスト・コードを含めて正規化し、全文をdigestへ束縛する。"""
    if not isinstance(body, str):
        raise KarteFormatError("Issue本文は文字列であること")
    in_ac, level, found = False, 0, False
    items: list[tuple[list[str], bool | None, int]] = []
    base_indent: int | None = None
    fence: str | None = None
    for number, line in enumerate(body.splitlines(), start=1):
        stripped = line.strip()
        was_fenced = fence is not None
        heading = HEADING.fullmatch(stripped) if not was_fenced else None
        if heading:
            if found:
                raise KarteFormatError("Issue本文のAcceptance criteriaセクションが重複")
            in_ac, level, found = True, len(heading.group(1)), True
        h = NEXT_HEADING.match(line) if not was_fenced else None
        if in_ac and not heading and h and len(h.group(1)) <= level:
            in_ac = False
        # セクション外のコード例に含まれる偽AC見出しも無視する。
        fence = advance_fence(fence, line)
        if heading or not in_ac:
            continue
        checkbox = CHECKBOX.fullmatch(line) if not was_fenced and fence is None else None
        plain = ITEM.match(line) if not was_fenced and fence is None else None
        indent = len(line) - len(line.lstrip(" \t"))
        is_top_item = (checkbox is not None or plain is not None) and (
            base_indent is None or indent <= base_indent
        )
        if is_top_item:
            if base_indent is None:
                base_indent = indent
            if checkbox is not None:
                items.append(([checkbox.group(3).strip()], checkbox.group(2).lower() == "x", number))
            else:
                items.append(([plain.group(1).strip()], None, number))
        elif items:
            # 空行で区切られたトップレベルの段落は非checkbox ACとして保存する。
            if (stripped and fence is None and base_indent is not None
                    and indent <= base_indent and items[-1][0]
                    and not items[-1][0][-1].strip()):
                items.append(([line], None, number))
            else:
                items[-1][0].append(line)
        elif stripped:
            # 非リストの通常段落もAC。0件として黙って破棄しない。
            items.append(([line], None, number))
            base_indent = indent
    result = tuple(AC("\n".join(parts).rstrip("\n"), checked, first)
                   for parts, checked, first in items)
    if len({(item.text, item.checked is not None) for item in result}) != len(result):
        raise KarteFormatError("同一文言のACが重複しており照合できない")
    return result


def digest(items: tuple[AC, ...]) -> str:
    """AC本文・順序・checkbox状態に束縛した決定論的digest。"""
    data = [{"text": item.text, "checked": item.checked} for item in items]
    return sha256(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
