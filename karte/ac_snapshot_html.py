"""Raw HTML block boundaries for AC snapshots (CommonMark types 1, 4–7).

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
# Type 7 cannot interrupt a paragraph; only accept it after a blank line.
ATTR = r"""(?:[ \t]+[a-zA-Z_:][a-zA-Z0-9_.:-]*(?:[ \t]*=[ \t]*(?:[^ \t"'=<>\x60]+|'[^']*'|"[^"]*"))?)"""
TAG = re.compile(r"^ {0,3}(?:<[a-zA-Z][a-zA-Z0-9-]*" + ATTR + r"*[ \t]*/?>|</[a-zA-Z][a-zA-Z0-9-]*[ \t]*>)[ \t]*$")
BLANK = re.compile(r"^[ \t]*$")


def advance(block, line, active, *, after_blank=False):
    """Return (end condition, whether this line is raw HTML)."""
    if block is None:
        if not active:
            return None, False
        match = RAW.match(line)
        if match:
            block = re.compile(r"</" + match.group(1) + r">", re.I)
        elif re.match(r"^ {0,3}<\?", line):
            block = re.compile(r"\?>")
        elif re.match(r"^ {0,3}<!\[CDATA\[", line):
            block = re.compile(r"\]\]>")
        elif re.match(r"^ {0,3}<![A-Z]", line):
            block = re.compile(">")
        elif BLOCK.match(line) or (after_blank and TAG.fullmatch(line)):
            block = BLANK
        else:
            return None, False
    if block.search(line):
        return None, block is not BLANK
    return block, True
