"""Issue本文全体のMarkdown fenced-code状態（AC見出し・項目の誤認を防止）。"""

import re

OPEN = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
CLOSE = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*$")


def advance(fence: str | None, line: str) -> str | None:
    """開始行ではinfo stringを許すが、終了行は同文字・同数以上・後続空白のみ。"""
    if fence is not None:
        matched = CLOSE.fullmatch(line)
        if (matched is not None and matched.group(1)[0] == fence[0]
                and len(matched.group(1)) >= len(fence)):
            return None
        return fence

    matched = OPEN.fullmatch(line)
    if matched is not None:
        delimiter, info = matched.groups()
        if delimiter[0] == "`" and "`" in info:
            return None
        return delimiter
    return None
