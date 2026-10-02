"""Extract nested commands from shell command and backtick substitutions."""


def _substitution_end(source, start, opening, closing):
    depth = 1
    quote = None
    index = start + len(opening)
    while index < len(source):
        char = source[index]
        if char == "\\" and quote != "'":
            index += 2
            continue
        if quote == "'":
            if char == "'":
                quote = None
        elif quote:
            if char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif source.startswith(opening, index):
            depth += 1
            index += len(opening)
            continue
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _backtick_end(source, start):
    index = start + 1
    while index < len(source):
        if source[index] == "\\":
            index += 2
        elif source[index] == "`":
            return index
        else:
            index += 1
    return None


def shell_substitutions(source):
    found = []
    quote = None
    index = 0
    while index < len(source):
        char = source[index]
        if char == "\\" and quote != "'":
            index += 2
            continue
        if quote == "'":
            if char == "'":
                quote = None
        elif quote:
            if char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == "`":
            end = _backtick_end(source, index)
            if end is None:
                return None
            found.append(source[index + 1 : end])
            index = end
        elif source.startswith("$(", index):
            end = _substitution_end(source, index + 1, "(", ")")
            if end is None:
                return None
            found.append(source[index + 2 : end])
            index = end
        index += 1
    return found
