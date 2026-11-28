"""Recognize ATX and Setext acceptance-criteria headings without silent zero AC."""

import re

ATX = re.compile(r"^(#{1,6})[ \t]+(Acceptance criteria|受け入れ基準)(?:[ \t]+#+)?[ \t]*$", re.I)
SETEXT = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
LABELS = frozenset(("acceptance criteria", "受け入れ基準"))


def section_level(lines: list[str], number: int, allowed: bool) -> int | None:
    """The line must be outside fenced code and list-contained child headings."""
    if not allowed:
        return None
    line = lines[number - 1]
    match = ATX.fullmatch(line.strip())
    if match is not None:
        return len(match.group(1))
    if number < 2 or SETEXT.fullmatch(line) is None:
        return None
    previous = lines[number - 2]
    leading = previous[:len(previous) - len(previous.lstrip(" \t"))]
    if len(leading) > 3 or "\t" in leading or previous.strip().casefold() not in LABELS:
        return None
    return 1 if line.strip().startswith("=") else 2


ATX_GENERIC = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+|$)")
LIST_LINE = re.compile(r"^ {0,3}(?:[-*+]|[0-9]{1,9}[.)])[ \t]+")
FENCE_MARKER = re.compile(r"^ {0,3}(?:`{3,}|~{3,})[ \t]*$")
THEMATIC_BREAK = re.compile(r"^ {0,3}(?:(?:\*[ \t]*){3,}|(?:_[ \t]*){3,}|(?:-[ \t]*){3,})$")


def heading_level(lines: list[str], number: int, allowed: bool) -> int | None:
    """Recognize a heading (not only AC headings) that can end an AC section."""
    if not allowed:
        return None
    line = lines[number - 1]
    match = ATX_GENERIC.match(line)
    if match is not None:
        return len(match.group(1))
    if number < 2 or SETEXT.fullmatch(line) is None:
        return None
    previous = lines[number - 2]
    leading = previous[:len(previous) - len(previous.lstrip(" \t"))]
    if (not previous.strip() or len(leading) > 3 or "\t" in leading
            or LIST_LINE.match(previous) or ATX_GENERIC.match(previous)
            or FENCE_MARKER.fullmatch(previous)
            or THEMATIC_BREAK.fullmatch(previous)
            or previous.lstrip().startswith(">")):
        return None
    return 1 if line.strip().startswith("=") else 2


def remove_setext_title(lines: list[str], number: int, items: list) -> None:
    """Remove the Setext title line previously classified as AC prose."""
    if (not lines[number - 1].strip().startswith(("=", "-"))
            or number < 2 or not items or not items[-1][0]
            or items[-1][0][-1] != lines[number - 2]):
        return
    if len(items[-1][0]) == 1 and items[-1][2] == number - 1:
        items.pop()
    else:
        items[-1][0].pop()


def block_transition(line, next_level, was_fenced, fence, in_html, was_inline_code, child, list_context, html_block, html_container):
    """Track boundaries from recognized blocks, not raw previous-line guesses."""
    if next_level is not None:
        list_context = False
    if html_container == 0:
        list_context = False
    if in_html:
        return html_block is None, list_context
    if was_inline_code:
        return False, list_context
    thematic = bool(THEMATIC_BREAK.fullmatch(line))
    boundary = not line.strip() or next_level is not None or (was_fenced and fence is None) or thematic
    if (next_level is not None or (not was_fenced and fence is not None) or thematic) and not child:
        list_context = False
    return boundary, list_context
