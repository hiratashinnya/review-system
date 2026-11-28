"""Shared container boundary for raw blocks and inline lookahead."""

import re

LIST_LINE = re.compile(r"^ {0,3}(?:[-*+]|[0-9]{1,9}[.)])[ \t]+")
THEMATIC_BREAK = re.compile(r"^ {0,3}(?:(?:\*[ \t]*){3,}|(?:_[ \t]*){3,}|(?:-[ \t]*){3,})$")
BLOCKQUOTE = re.compile(r"^ {0,3}>")


def list_item_indent(line: str, parent: int) -> int | None:
    """Return the list item's content column when a marker starts a block."""
    relative = line[parent:]
    marker = LIST_LINE.match(relative)
    if marker is None or not relative[marker.end():].strip() or THEMATIC_BREAK.fullmatch(relative):
        return None
    return parent + marker.end()


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
