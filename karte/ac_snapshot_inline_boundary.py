"""Find the source lines that can continue an open inline Markdown construct."""

from .ac_snapshot_boundary import enclosing_indent
from .ac_snapshot_fence import advance as advance_fence
from .ac_snapshot_heading import ATX_GENERIC, LIST_LINE, SETEXT, THEMATIC_BREAK
from .ac_snapshot_html import advance as advance_html


def inline_continuation(line, following, list_indent):
    offset = enclosing_indent(line, list_indent)
    marker = LIST_LINE.match(line[offset:])
    indent = offset + len(marker.group()) if marker else list_indent
    for candidate in following:
        if not candidate.strip():
            break
        relative = candidate[enclosing_indent(candidate, indent):]
        leading = relative[:len(relative) - len(relative.lstrip(" \t"))]
        if (indent is not None and "\t" in leading
                or ATX_GENERIC.match(relative) or LIST_LINE.match(relative)
                or SETEXT.fullmatch(relative) or THEMATIC_BREAK.fullmatch(relative)
                or (len(leading) <= 3 and relative.lstrip(" ").startswith(">"))
                or advance_fence(None, candidate, list_indent=indent) is not None
                or advance_html(None, candidate, True, list_indent=indent).raw):
            break
        yield candidate
