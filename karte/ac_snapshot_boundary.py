"""Shared container boundary for raw blocks and inline lookahead."""


def leaves_container(line: str, indent: int | None) -> bool:
    """A nonblank line outside the opening list indentation ends its block."""
    return bool(indent and line.strip() and not line.startswith(" " * indent))


def enclosing_indent(line: str, indent: int | None) -> int:
    """Find the active list indentation for a block starting on this line."""
    return indent if indent and line.startswith(" " * indent) else 0
