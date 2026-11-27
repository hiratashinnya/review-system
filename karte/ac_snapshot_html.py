"""Raw HTML block boundaries for AC snapshots (CommonMark types 1–7)."""
import re
from typing import NamedTuple

from .ac_snapshot_boundary import leaves_container
from .ac_snapshot_comment import visible_line

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
COMMENT = re.compile("-->")
COMMENT_START = re.compile(r"^ {0,3}<!--")


class HtmlTransition(NamedTuple):
    block: tuple[re.Pattern, int] | None
    raw: bool
    container: int | None
    comment: bool


def advance(block, line, active, *, boundary=False, list_indent=None) -> HtmlTransition:
    """Return the remaining block, raw flag, container indent and type-2 flag."""
    if block is not None:
        end, container = block
        if leaves_container(line, container):
            block, boundary, list_indent = None, True, None
    if block is None:
        if not active:
            return HtmlTransition(None, False, None, False)
        container = list_indent if list_indent and line.startswith(" " * list_indent) else 0
        candidate = line[container:]
        match = RAW.match(candidate)
        if match:
            block = re.compile(r"</" + match.group(1) + r">", re.I)
        elif COMMENT_START.match(candidate):
            block = COMMENT
        elif re.match(r"^ {0,3}<\?", candidate):
            block = re.compile(r"\?>")
        elif re.match(r"^ {0,3}<!\[CDATA\[", candidate):
            block = re.compile(r"\]\]>")
        elif re.match(r"^ {0,3}<![A-Z]", candidate):
            block = re.compile(">")
        elif BLOCK.match(candidate) or (boundary and TAG.fullmatch(candidate)):
            block = BLANK
        else:
            return HtmlTransition(None, False, None, False)
        block = (block, container)
    end, container = block
    if end.search(line):
        return HtmlTransition(None, end is not BLANK, container, end is COMMENT)
    return HtmlTransition(block, True, container, end is COMMENT)


def comment_suffix(block, line, container):
    """Retain a second comment opened after the first comment's closing marker."""
    suffix, opened, _, _ = visible_line(line.partition("-->")[2], False, 0, (), allow_open=True)
    return ((COMMENT, container) if opened else block), suffix
