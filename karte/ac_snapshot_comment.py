"""Hide HTML comments without hiding fenced, indented, or multiline inline code."""
import re
from .ac_snapshot_boundary import has_code_indent
from .ac_snapshot_escape import find_unescaped
from .ac_snapshot_html import COMMENT
from .ac_snapshot_inline_boundary import inline_continuation


def _close(line, position, width):
    """End of first closing backtick run with exactly this width."""
    for match in re.finditer(chr(96) + "+", line[position:]):
        if len(match.group()) == width:
            return position + match.end()
    return None


def visible_line(line, in_comment, code_ticks, future_lines, *, allow_open=False):
    """Filter HTML comments; preserve matched CommonMark code spans verbatim."""
    parts, pos, hidden = [], 0, in_comment
    while pos < len(line):
        if code_ticks:
            end = _close(line, pos, code_ticks)
            if end is None:
                parts.append(line[pos:])
                break
            parts.append(line[pos:end])
            pos, code_ticks = end, 0
            continue
        if in_comment:
            close = line.find("-->", pos)
            if close < 0:
                return "".join(parts), True, 0, True
            pos, in_comment, hidden = close + 3, False, True
            continue
        opening = find_unescaped(line, "<!--", pos)
        tick = find_unescaped(line, chr(96), pos)
        if tick >= 0 and (opening < 0 or tick < opening):
            end = tick
            while end < len(line) and line[end] == chr(96):
                end += 1
            width = end - tick
            close = _close(line, end, width)
            if close is not None:
                parts.append(line[pos:close])
                pos = close
            elif any(_close(rest, 0, width) is not None for rest in future_lines):
                parts.append(line[pos:])
                code_ticks = width
                break
            else:
                parts.append(line[pos:end])
                pos = end
            continue
        if opening < 0:
            parts.append(line[pos:])
            break
        if not allow_open and "-->" not in line[opening + 4:] and not any("-->" in rest for rest in future_lines):
            parts.append(line[pos:])
            break
        parts.append(line[pos:opening])
        pos, in_comment, hidden = opening + 4, True, True
    return "".join(parts), in_comment, code_ticks, hidden

def comment_suffix(block, line, container):
    """Retain a second comment opened after the first comment's closing marker."""
    suffix, opened, _, _ = visible_line(line.partition("-->")[2], False, 0, (), allow_open=True)
    return ((COMMENT, container) if opened else block), suffix


class CommentFilter:
    def __init__(self):
        self.in_comment = False
        self.code_ticks = 0

    def filter(self, raw_line, fenced, content_indent, future_lines, indents):
        if not (self.in_comment or self.code_ticks or "<!--" in raw_line or "`" in raw_line):
            return raw_line, False
        content_code = has_code_indent(raw_line, content_indent)
        if not self.code_ticks and (
            fenced or (content_code and not self.in_comment)
        ):
            return raw_line, False
        following = tuple(inline_continuation(future_lines, indents))
        line, self.in_comment, self.code_ticks, hidden = visible_line(
            raw_line, self.in_comment, self.code_ticks, following,
        )
        return line, hidden
