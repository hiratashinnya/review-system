"""Find the source lines that can continue an open inline Markdown construct."""

from .ac_snapshot_boundary import BLOCKQUOTE, LIST_LINE, THEMATIC_BREAK, containing_indent, expand_indent
from .ac_snapshot_fence import advance as advance_fence
from .ac_snapshot_heading import ATX_GENERIC, SETEXT
from .ac_snapshot_html import advance as advance_html


def inline_continuation(following, indents):
    for candidate in following:
        if not candidate.strip():
            break
        indent = containing_indent(candidate, indents)
        relative = expand_indent(candidate)[indent:]
        if (ATX_GENERIC.match(relative) or LIST_LINE.match(relative)
                or SETEXT.fullmatch(relative) or THEMATIC_BREAK.fullmatch(relative)
                or BLOCKQUOTE.match(relative)
                or advance_fence(None, candidate, list_indent=indent) is not None
                or advance_html(None, candidate, True, list_indent=indent).raw):
            break
        yield candidate
