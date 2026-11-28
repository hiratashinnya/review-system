"""Issue #801: GitHub Issue 本文からレビュアー用 AC snapshot を正規化する。
"""

import re

from .format_error import KarteFormatError
from .ac_snapshot_fence import advance as advance_fence
from .ac_snapshot_html import advance as advance_html
from .ac_snapshot_comment import CommentFilter, comment_suffix
from .ac_snapshot_boundary import containing_indent, finish_inner_lists, leaves_container, list_item_indent
from .ac_snapshot_model import AC, digest
from .ac_snapshot_heading import heading_level, remove_setext_title, section_level, block_transition

CHECKBOX = re.compile(r"^(\s*(?:[-*+]|[0-9]{1,9}[.)])\s+)\[([ xX])\](\s+\S.*)$")


def from_issue_body(body: str) -> tuple[AC, ...]:
    """AC項目の継続行・子リスト・コードを含めて正規化し、全文をdigestへ束縛する。"""
    if not isinstance(body, str):
        raise KarteFormatError("Issue本文は文字列であること")
    in_ac, level, found = False, 0, False
    items: list[tuple[list[str], bool | None, int]] = []
    base_indent, list_indents = None, []
    fence, html_block = None, None  # AC節の外でも状態を追跡
    comments = CommentFilter()
    boundary, lines = True, body.splitlines()
    visible_lines = [""] * len(lines)
    for number, raw_line in enumerate(lines, start=1):
        active_indent = containing_indent(raw_line, list_indents)
        if fence is not None and leaves_container(raw_line, fence.container):
            fence, boundary = None, True
        if html_block is not None and leaves_container(raw_line, html_block[1]):
            html_block, boundary = None, True
        if boundary and raw_line.strip():
            finish_inner_lists(list_indents, active_indent)
        was_inline_code = comments.code_ticks != 0
        block_active = fence is None and not was_inline_code and not comments.in_comment
        html_block, in_html, html_container, html_comment = advance_html(html_block, raw_line, block_active, boundary=boundary, list_indent=active_indent)
        if html_container is not None:
            finish_inner_lists(list_indents, html_container)
        item_indent = list_item_indent(raw_line, active_indent) if block_active and not in_html else None
        if item_indent is not None:
            finish_inner_lists(list_indents, active_indent)
            list_indents.append(item_indent)
        was_fenced = fence is not None
        if not was_inline_code and not in_html and not comments.in_comment:
            block_line = raw_line if item_indent is None else " " * item_indent + raw_line[item_indent:]
            fence = advance_fence(fence, block_line, list_indent=item_indent or active_indent)
        html_block, suffix = comment_suffix(html_block, raw_line, html_container) if html_comment else (html_block, "")
        fenced = was_fenced or fence is not None
        line, hidden = (suffix, True) if html_comment else (raw_line, False) if in_html else comments.filter(raw_line, fenced, active_indent, lines[number:], list_indents)
        visible_lines[number - 1] = "" if html_comment else line
        if hidden and not line.strip():
            if html_comment:
                boundary = html_block is None
            continue  # A comment-only line must not create an AC or heading.
        stripped = line.strip()
        leading = line[:len(line) - len(line.lstrip(" \t"))]
        indent = len(leading)
        is_heading = not fenced and not was_inline_code and not in_html and not active_indent and indent <= 3 and "\t" not in leading
        heading = section_level(visible_lines, number, is_heading)
        if heading:
            if found:
                raise KarteFormatError("Issue本文のAcceptance criteriaセクションが重複")
            in_ac, level, found = True, heading, True
        next_level = heading_level(visible_lines, number, is_heading)
        if in_ac and not heading and next_level is not None and next_level <= level:
            remove_setext_title(visible_lines, number, items)
            in_ac = False
        boundary = block_transition(line[active_indent:], next_level, was_fenced, fence, in_html, was_inline_code, html_block)
        if stripped and (boundary or fenced) and item_indent is None:
            finish_inner_lists(list_indents, active_indent)
        if heading or not in_ac:
            continue
        top_item = list_item_indent(line, 0) if not active_indent and not was_fenced and not was_inline_code and not in_html else None
        if top_item is not None:
            if base_indent is None:
                base_indent = indent
            checkbox = CHECKBOX.fullmatch(line)
            if checkbox is not None and CHECKBOX.fullmatch(raw_line) is not None:
                items.append(([checkbox.group(3).strip()], checkbox.group(2).lower() == "x", number))
            else:
                items.append(([line[top_item:].strip()], None, number))
        elif items:
            if (stripped and next_level is None and fence is None and not in_html and base_indent is not None
                    and indent <= base_indent and items[-1][0]
                    and not items[-1][0][-1].strip()):
                items.append(([line], None, number))
            else:
                items[-1][0].append(line)
        elif stripped and indent <= 3 and "\t" not in leading:
            items.append(([line], None, number))
            base_indent = indent
    result = tuple(AC("\n".join(parts).rstrip("\n"), checked, first)
                   for parts, checked, first in items)
    if len({(item.text, item.checked is not None) for item in result}) != len(result):
        raise KarteFormatError("同一文言のACが重複しており照合できない")
    return result
