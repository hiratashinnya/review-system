"""Hide HTML comments without hiding fenced, indented, or multiline inline code."""
import re
from .ac_snapshot_fence import advance as advance_fence
from .ac_snapshot_escape import find_unescaped
from .ac_snapshot_boundary import leaves_container
_NEW_BLOCK = re.compile(r"^ {0,3}(?:#{1,6}(?:[ \t]|$)|(?:[-*+]|\d{1,9}[.)])[ \t]+|>|\x60{3,}|~{3,})")
_LIST = re.compile(r"^ {0,3}(?:[-*+]|\d{1,9}[.)])[ \t]+")
def _same_block(line, following, indent):
    marker = _LIST.match(line)
    minimum = len(marker.group()) if marker else indent
    for candidate in following:
        if not candidate.strip() or _NEW_BLOCK.match(candidate):
            break
        leading = candidate[:len(candidate) - len(candidate.lstrip(" \t"))]
        if minimum is not None and ("\t" in leading or leaves_container(candidate, minimum)):
            break
        yield candidate

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

class CommentFilter:
    def __init__(self):
        self.in_comment = False
        self.code_ticks = 0

    def filter(self, raw_line, fence, in_ac, list_context, content_indent, future_lines):
        leading = raw_line[:len(raw_line) - len(raw_line.lstrip(" \t"))]
        indent = len(leading)
        content_code = (indent >= 4 or "\t" in leading) and not (
            in_ac and list_context and content_indent is not None
            and content_indent <= indent <= content_indent + 3)
        opening_fence = (fence is None and not self.in_comment and not self.code_ticks
                         and advance_fence(
                             None, raw_line,
                             list_indent=(content_indent if in_ac and list_context else None),
                         ) is not None)
        if not self.code_ticks and (
            fence is not None or opening_fence or (content_code and not self.in_comment)
        ):
            return raw_line, False
        following = tuple(_same_block(
            raw_line, future_lines, content_indent if in_ac and list_context else None,
        ))
        line, self.in_comment, self.code_ticks, hidden = visible_line(
            raw_line, self.in_comment, self.code_ticks, following,
        )
        return line, hidden
