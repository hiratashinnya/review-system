"""Issue #801: GitHub Issue 本文からレビュアー用 AC snapshot を正規化する。
"""

import re

from .format_error import KarteFormatError
from .ac_snapshot_fence import advance as advance_fence
from .ac_snapshot_html import advance as advance_html
from .ac_snapshot_comment import CommentFilter, comment_suffix
from .ac_snapshot_boundary import enclosing_indent, leaves_container
from .ac_snapshot_model import AC, digest
from .ac_snapshot_heading import heading_level, remove_setext_title, section_level, block_transition

CHECKBOX = re.compile(r"^(\s*(?:[-*+]|[0-9]{1,9}[.)])\s+)\[([ xX])\](\s+\S.*)$")
ITEM = re.compile(r"^\s*(?:[-*+]|[0-9]{1,9}[.)])\s+(\S.*)$")


def from_issue_body(body: str) -> tuple[AC, ...]:
    """AC項目の継続行・子リスト・コードを含めて正規化し、全文をdigestへ束縛する。"""
    if not isinstance(body, str):
        raise KarteFormatError("Issue本文は文字列であること")
    in_ac, level, found = False, 0, False
    items: list[tuple[list[str], bool | None, int]] = []
    base_indent, content_indent, list_context = None, None, False
    fence, html_block = None, None  # AC節の外でも状態を追跡
    comments = CommentFilter()
    boundary, lines = True, body.splitlines()
    visible_lines = [""] * len(lines)
    for number, raw_line in enumerate(lines, start=1):
        if fence is not None and leaves_container(raw_line, fence.container):
            fence, boundary, list_context = None, True, False
        was_inline_code = comments.code_ticks != 0
        active_indent = content_indent if list_context else None
        html_block, in_html, html_container, html_comment = advance_html(html_block, raw_line, fence is None and not was_inline_code and not comments.in_comment, boundary=boundary, list_indent=active_indent)
        html_block, suffix = comment_suffix(html_block, raw_line, html_container) if html_comment else (html_block, "")
        line, hidden = (suffix, True) if html_comment else (raw_line, False) if in_html else comments.filter(raw_line, fence, active_indent, lines[number:])
        visible_lines[number - 1] = "" if html_comment else line
        if hidden and not line.strip():
            if html_comment:
                boundary, list_context = block_transition(line, None, False, fence, in_html, was_inline_code, False, list_context, html_block, html_container)
            continue  # A comment-only line must not create an AC or heading.
        stripped = line.strip()
        leading = line[:len(line) - len(line.lstrip(" \t"))]
        indent = len(leading)
        was_fenced = fence is not None
        child = bool(enclosing_indent(line, active_indent))
        is_heading = not was_fenced and not was_inline_code and not in_html and not child and indent <= 3 and "\t" not in leading
        heading = section_level(visible_lines, number, is_heading)
        if heading:
            if found:
                raise KarteFormatError("Issue本文のAcceptance criteriaセクションが重複")
            in_ac, level, found = True, heading, True
        next_level = heading_level(visible_lines, number, is_heading)
        if in_ac and not heading and next_level is not None and next_level <= level:
            remove_setext_title(visible_lines, number, items)
            in_ac, list_context = False, False
        if not was_inline_code and not in_html:
            fence = advance_fence(
                fence, line,
                list_indent=(content_indent if list_context else None),
            )
        boundary, list_context = block_transition(line, next_level, was_fenced, fence, in_html, was_inline_code, child, list_context, html_block, html_container)
        plain_ok = not was_fenced and not was_inline_code and fence is None and not in_html
        checkbox = CHECKBOX.fullmatch(line) if plain_ok else None
        # A stripped prefix cannot create a new writable checkbox position.
        if checkbox is not None and CHECKBOX.fullmatch(raw_line) is None:
            checkbox = None
        plain = ITEM.match(line) if plain_ok else None
        # 4-space/tab-indented code is never an independent AC checkbox.
        top_item = plain if indent <= 3 and "\t" not in leading and not child else None
        if top_item is not None:
            list_context, content_indent = True, len(line) - len(top_item.group(1))
        if heading or not in_ac:
            continue
        if top_item is not None:
            if base_indent is None:
                base_indent = indent
            if checkbox is not None:
                items.append(([checkbox.group(3).strip()], checkbox.group(2).lower() == "x", number))
            else:
                items.append(([top_item.group(1).strip()], None, number))
        elif items:
            if (stripped and next_level is None and fence is None and not in_html and base_indent is not None
                    and indent <= base_indent and items[-1][0]
                    and not items[-1][0][-1].strip()):
                items.append(([line], None, number))
                list_context = False
            else:
                items[-1][0].append(line)
        elif stripped and indent <= 3 and "\t" not in leading:
            items.append(([line], None, number))
            base_indent = indent
            list_context = False
    result = tuple(AC("\n".join(parts).rstrip("\n"), checked, first)
                   for parts, checked, first in items)
    if len({(item.text, item.checked is not None) for item in result}) != len(result):
        raise KarteFormatError("同一文言のACが重複しており照合できない")
    return result
