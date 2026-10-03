"""Extract nested commands from shell command and backtick substitutions."""


def _backtick_end(source, start):
    index = start + 1
    while index < len(source):
        if source[index] == "\\":
            index += 2
        elif source[index] == "`": return index
        else:
            index += 1
    return None


def _command_end(source, index, nesting):
    if source[index] == "`": return _backtick_end(source, index), index + 1
    return _substitution_end(source, index + 1, "(", ")", nesting + 1), index + 2


def _substitution_end(source, start, opening, closing, nesting=0):
    if nesting > 16: return None
    depth, quote, index = 1, None, start + len(opening)
    while index < len(source):
        char = source[index]
        if char == "\\" and quote != "'":
            index += 2
            continue
        if quote:
            if char == quote: quote = None
            elif quote == '"' and (char == "`" or source.startswith("$(", index)):
                end, _ = _command_end(source, index, nesting)
                if end is None: return None
                index = end
        elif char in {"'", '"'}:
            quote = char
        elif char == "`":
            end = _backtick_end(source, index)
            if end is None: return None
            index = end
        elif source.startswith(opening, index):
            depth += 1
            index += len(opening)
            continue
        elif char == closing:
            depth -= 1
            if depth == 0: return index
        index += 1
    return None


def shell_substitutions(source):
    found, quote, index = [], None, 0
    while index < len(source):
        char = source[index]
        if char == "\\" and quote != "'":
            index += 2
            continue
        if quote:
            if char == quote: quote = None
            elif quote == '"' and (char == "`" or source.startswith("$(", index)):
                end, body = _command_end(source, index, 0)
                if end is None: return None
                found.append(source[body:end])
                index = end
        elif char in {"'", '"'}:
            quote = char
        elif char == "`" or source.startswith("$(", index):
            end, body = _command_end(source, index, 0)
            if end is None: return None
            found.append(source[body:end])
            index = end
        index += 1
    return found
