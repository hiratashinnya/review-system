"""Raw HTML blocks (<pre>/<script>/<style>/<textarea>) inside an AC snapshot.

CommonMark keeps these lines verbatim until the matching end tag, so their
contents are never AC headings or checkboxes (Codex P1 r4681383555).
"""

import re

OPEN = re.compile(r"^ {0,3}<(pre|script|style|textarea)(?:[\s>]|$)", re.I)


def advance(block, line, active):
    """Return ``(block_after_line, in_html_block_for_line)``.

    ``block`` is the end-tag regex of the open raw block, or None. ``active`` says
    whether this line may open a block (not inside fenced or inline code).
    """
    if block is None:
        match = OPEN.match(line) if active else None
        if match is None:
            return None, False
        block = re.compile(r"</" + match.group(1) + r">", re.I)
    if block.search(line):
        return None, True
    return block, True
