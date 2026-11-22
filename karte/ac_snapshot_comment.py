"""Hide HTML comments without hiding literal fenced or indented code."""
from .ac_snapshot_fence import advance as advance_fence


class CommentFilter:
    def __init__(self):
        self.in_comment = False

    def filter(self, raw_line, fence, in_ac, list_context, content_indent):
        leading = raw_line[:len(raw_line) - len(raw_line.lstrip(" \t"))]
        indent = len(leading)
        content_code = (indent >= 4 or "\t" in leading) and not (
            in_ac and list_context and content_indent is not None
            and content_indent <= indent <= content_indent + 3)
        opening_fence = (fence is None and not self.in_comment and advance_fence(
            None, raw_line, list_indent=(content_indent if in_ac and list_context else None),
        ) is not None)
        if fence is not None or opening_fence or (content_code and not self.in_comment):
            return raw_line, False
        line, self.in_comment, hidden = visible_line(raw_line, self.in_comment)
        return line, hidden



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
