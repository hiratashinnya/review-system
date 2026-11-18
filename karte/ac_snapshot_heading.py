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
LIST_LINE = re.compile(r"^ {0,3}(?:[-*+]|[0-9]+[.)])[ \t]+")


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
            or LIST_LINE.match(previous)):
        return None
    return 1 if line.strip().startswith("=") else 2
