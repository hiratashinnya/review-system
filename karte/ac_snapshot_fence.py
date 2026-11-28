"""Track Markdown fenced code at the correct indentation within an AC snapshot."""

from dataclasses import dataclass
import re

from .ac_snapshot_boundary import enclosing_indent, leaves_container

OPEN = re.compile(r"^( *)(`{3,}|~{3,})(.*)$")
CLOSE = re.compile(r"^( *)(`{3,}|~{3,})[ \t]*$")


@dataclass(frozen=True)
class Fence:
    marker: str
    max_indent: int
    container: int = 0


def advance(fence: Fence | None, line: str, *, list_indent: int | None = None) -> Fence | None:
    """Closing fence uses the opening container's indent, never an arbitrary indent."""
    if fence is not None and leaves_container(line, fence.container):
        fence, list_indent = None, None
    if fence is not None:
        closing = CLOSE.fullmatch(line)
        if (closing is not None and len(closing.group(1)) <= fence.max_indent
                and closing.group(2)[0] == fence.marker[0]
                and len(closing.group(2)) >= len(fence.marker)):
            return None
        return fence

    opening = OPEN.fullmatch(line)
    if opening is None:
        return None
    leading, marker, info = opening.groups()
    indent = len(leading)
    container = enclosing_indent(line, list_indent)
    if container <= indent <= container + 3:
        max_indent = container + 3
    else:
        return None  # Four-space indented code is not a fenced code opener.
    if marker[0] == "`" and "`" in info:
        return None
    return Fence(marker, max_indent, container)
