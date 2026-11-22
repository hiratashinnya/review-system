"""Ignore HTML comments, preserving visible Markdown and physical line numbers."""


def visible_line(line: str, in_comment: bool) -> tuple[str, bool, bool]:
    """Visible text, continued comment state, and whether content was hidden.

    Closed inline backtick code spans are literal, not HTML comments.
    Fenced/indented code is handled by the caller.
    """
    parts = []
    pos = 0
    hidden = in_comment
    while pos < len(line):
        if in_comment:
            close = line.find("-->", pos)
            if close < 0:
                return "".join(parts), True, True
            in_comment = False
            hidden = True
            pos = close + 3
            continue
        opening = line.find("<!--", pos)
        tick = line.find(chr(96), pos)
        if tick >= 0 and (opening < 0 or tick < opening):
            end = tick
            while end < len(line) and line[end] == chr(96):
                end += 1
            delimiter = line[tick:end]
            close = line.find(delimiter, end)
            if close >= 0:
                parts.append(line[pos:close + len(delimiter)])
                pos = close + len(delimiter)
                continue
            parts.append(line[pos:end])
            pos = end
            continue
        if opening < 0:
            parts.append(line[pos:])
            break
        parts.append(line[pos:opening])
        pos = opening + 4
        in_comment = True
        hidden = True
    return "".join(parts), in_comment, hidden
