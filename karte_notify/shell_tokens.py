"""引用を保ちながらシェルのコマンド境界と引数を分ける。"""

import re
import shlex

_ASSIGNMENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*=")
_PREFIXES = {"env", "command", "exec", "if", "then", "while", "until", "do", "!", "--"}


def tokenize_shell(command: str) -> list[list[str]]:
    """引用外の制御演算子・改行で分割し、各コマンドの引数を返す。"""
    parts: list[str] = []
    current: list[str] = []
    quote = None
    escaped = False
    for index, char in enumerate(command):
        if escaped:
            if char == "\n":
                current.pop()
            else:
                current.append(char)
            escaped = False
            continue
        if char == "\\" and quote != "'":
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
            continue
        previous = command[index - 1] if index else ""
        following = command[index + 1] if index + 1 < len(command) else ""
        redirection = char in "|&" and (previous in {"<", ">"} or (char == "&" and following == ">"))
        if char in ";|&()\n" and not redirection:
            if current:
                parts.append("".join(current))
                current = []
        else:
            current.append(char)
    if current:
        parts.append("".join(current))
    return [tokens for part in parts if (tokens := _shell_words(part))]


def _shell_words(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def is_executable_prefix(tokens: list[str]) -> bool:
    """Python より前が環境代入か、対応する shell 前置きだけか確認する。"""
    index = 0
    while index < len(tokens):
        if tokens[index:index + 2] == ["rtk", "proxy"]:
            index += 2
        elif tokens[index] in _PREFIXES or _ASSIGNMENT.match(tokens[index]):
            index += 1
        else:
            return False
    return True
