"""Recognize Markdown punctuation escapes before HTML and code-span delimiters."""


def find_unescaped(line: str, token: str, start: int) -> int:
    """Only an even number of consecutive backslashes permits a delimiter."""
    position = line.find(token, start)
    while position >= 0:
        backslashes = 0
        cursor = position - 1
        while cursor >= 0 and line[cursor] == "\\":
            backslashes += 1
            cursor -= 1
        if backslashes % 2 == 0:
            return position
        position = line.find(token, position + len(token))
    return -1
