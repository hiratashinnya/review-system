"""Split shell input into quote-aware command segments and token lists."""

import shlex


def assignment_token(token):
    name, separator, _ = token.partition("=")
    return bool(separator) and name.isascii() and name.isidentifier()


def command_segments(command):
    raw_segments, current = [], []
    quote = None
    escaped = False
    comment = False
    for char in command:
        if comment:
            if char == "\n":
                comment = False
                if current:
                    raw_segments.append("".join(current))
                    current = []
            continue
        if quote == "'":
            current.append(char)
            if char == "'":
                quote = None
            continue
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            continue
        if quote:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
        elif char == "#" and (not current or current[-1].isspace() or current[-1] in ";|&(){}"):
            comment = True
        elif char in ";&|(){}\n":
            if current:
                raw_segments.append("".join(current))
                current = []
        else:
            current.append(char)
    if quote:
        return None
    if current:
        raw_segments.append("".join(current))
    segments = []
    for raw_segment in raw_segments:
        try:
            tokens = shlex.split(raw_segment, posix=True)
        except ValueError:
            return None
        if tokens:
            segments.append((tokens, raw_segment))
    return segments
