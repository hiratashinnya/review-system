"""Raw HTML block boundaries for AC snapshots (CommonMark types 1, 3–7).

HTML comments (type 2) are handled by CommentFilter.
"""
import re

RAW = re.compile(r"^ {0,3}<(pre|script|style|textarea)(?:[\s>]|$)", re.I)
BLOCK_TAGS = (
    "address article aside base basefont blockquote body caption center col colgroup "
    "dd details dialog dir div dl dt fieldset figcaption figure footer form frame "
    "frameset h1 h2 h3 h4 h5 h6 head header hr html iframe legend li link main "
    "menu menuitem nav noframes ol optgroup option p param search section summary "
    "table tbody td tfoot th thead title tr track ul"
)
BLOCK = re.compile(r"^ {0,3}</?(?:" + "|".join(BLOCK_TAGS.split()) + r")(?:\s|/?>|$)", re.I)
# Type 7 cannot interrupt a paragraph.
ATTR = r"""(?:[ \t]+[a-zA-Z_:][a-zA-Z0-9_.:-]*(?:[ \t]*=[ \t]*(?:[^ \t"'=<>\x60]+|'[^']*'|"[^"]*"))?)"""
TAG = re.compile(r"^ {0,3}(?:<[a-zA-Z][a-zA-Z0-9-]*" + ATTR + r"*[ \t]*/?>|</[a-zA-Z][a-zA-Z0-9-]*[ \t]*>)[ \t]*$")
BLANK = re.compile(r"^[ \t]*$")


def advance(block, line, active, *, boundary=False, list_indent=None):
    """Return (end condition, whether this line is raw HTML)."""
    if block is not None:
        end, container = block
        if container and line.strip() and not line.startswith(" " * container):
            block = None
    if block is None:
        if not active:
            return None, False, None
        container = list_indent if list_indent and line.startswith(" " * list_indent) else 0
        candidate = line[container:]
        match = RAW.match(candidate)
        if match:
            block = re.compile(r"</" + match.group(1) + r">", re.I)
        elif re.match(r"^ {0,3}<\?", candidate):
            block = re.compile(r"\?>")
        elif re.match(r"^ {0,3}<!\[CDATA\[", candidate):
            block = re.compile(r"\]\]>")
        elif re.match(r"^ {0,3}<![A-Z]", candidate):
            block = re.compile(">")
        elif BLOCK.match(candidate) or (boundary and TAG.fullmatch(candidate)):
            block = BLANK
        else:
            return None, False
        block = (block, container)
    end, container = block
    if end.search(line):
        return None, end is not BLANK, container
    return block, True, container
