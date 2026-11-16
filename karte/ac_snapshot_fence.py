"""Issue本文全体のMarkdown fenced-code状態（AC見出し・項目の誤認を防止）。"""

import re

OPEN = re.compile(r"^([ \t]*)(`{3,}|~{3,})(.*)$")
CLOSE = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*$")


def advance(fence: str | None, line: str, *, allow_indented=False) -> str | None:
    """開始は3列以内（リスト内では相対字下げ許可）、終了は同文字・同数以上。"""
    if fence is not None:
        matched = CLOSE.fullmatch(line)
        if (matched is not None and matched.group(1)[0] == fence[0]
                and len(matched.group(1)) >= len(fence)):
            return None
        return fence

    matched = OPEN.fullmatch(line)
    if matched is not None:
        leading, delimiter, info = matched.groups()
        if not allow_indented and (len(leading) > 3 or "\t" in leading):
            return None  # 4列以上はMarkdownの字下げコードであり、fenced codeではない
        if delimiter[0] == "`" and "`" in info:
            return None
        return delimiter
    return None
