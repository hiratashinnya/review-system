"""Shared container boundary for raw blocks and inline lookahead."""

import re
from typing import NamedTuple

LIST_LINE = re.compile(r"^( {0,3}(?:[-*+]|[0-9]{1,9}[.)]))([ \t]+)")
THEMATIC_BREAK = re.compile(r"^ {0,3}(?:(?:\*[ \t]*){3,}|(?:_[ \t]*){3,}|(?:-[ \t]*){3,})$")
BLOCKQUOTE = re.compile(r"^ {0,3}>")


class ListItem(NamedTuple):
    content_index: int
    indent: int
    indented_code: bool


def list_items(line: str, parent: int):
    """Recognize successive list markers and determine their content columns."""
    index = column = parent
    while marker := LIST_LINE.match(line[index:]):
        if THEMATIC_BREAK.fullmatch(line[index:]) or not line[index + marker.end():].strip():
            break
        marker_end = column + marker.end(1)
        actual = len((" " * column + marker.group()).expandtabs(4))
        index += marker.end()
        indented_code = actual - marker_end > 4
        column = marker_end + 1 if indented_code else actual
        yield ListItem(index, column, indented_code)
        if indented_code:
            break


def start_list_items(line: str, parent: int, indents: list[int]) -> ListItem | None:
    """Remember the item containers that begin on this physical line."""
    items = tuple(list_items(line, parent))
    if not items:
        return None
    finish_inner_lists(indents, parent)
    indents.extend(item.indent for item in items)
    return items[-1]


def containing_indent(line: str, indents: list[int]) -> int:
    """Return the deepest current list container compatible with this line."""
    return next((indent for indent in reversed(indents) if enclosing_indent(line, indent)), 0)


def finish_inner_lists(indents: list[int], parent: int) -> None:
    """Remove deeper list items when a new sibling or enclosing block begins."""
    while indents and indents[-1] > parent:
        indents.pop()


def leaves_container(line: str, indent: int | None) -> bool:
    """A nonblank line outside the opening list indentation ends its block."""
    return bool(indent and line.strip() and not line.startswith(" " * indent))


def enclosing_indent(line: str, indent: int | None) -> int:
    """Find the active list indentation for a block starting on this line."""
    return indent if indent and line.startswith(" " * indent) else 0
