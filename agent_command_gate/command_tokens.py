"""Tokenize shell commands and remove inspection-safe launch wrappers."""

import os
import shlex


CONTROL_TOKENS = {";", "&&", "||", "&", "|", "(", ")", "{", "}", "\n"}


def _assignment(token):
    name, separator, _ = token.partition("=")
    return bool(separator) and name.isascii() and name.isidentifier()


def command_segments(command):
    lexer = shlex.shlex(_separate_shell_lines(command), posix=True, punctuation_chars=";&|(){}")
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return None
    segments, current = [], []
    for token in tokens:
        if token in CONTROL_TOKENS:
            if current:
                segments.append(current)
                current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    return segments


def _separate_shell_lines(command):
    output = []
    quote = None
    escaped = False
    comment = False
    for char in command:
        if comment:
            if char == "\n":
                output.append(";")
                comment = False
            continue
        if quote == "'":
            output.append(char)
            if char == "'":
                quote = None
            continue
        if escaped:
            output.append(char)
            escaped = False
            continue
        if char == "\\":
            output.append(char)
            escaped = True
            continue
        if quote:
            output.append(char)
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            output.append(char)
        elif char == "#" and (not output or output[-1].isspace() or output[-1] in ";|&()"):
            comment = True
        elif char == "\n":
            output.append(";")
        else:
            output.append(char)
    return "".join(output)


def _environment_end(tokens, index):
    index += 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return index + 1
        if token in {"-i", "--ignore-environment"} or _assignment(token):
            index += 1
        elif token in {"-u", "--unset", "-C", "--chdir"}:
            index += 2
        elif token.startswith("--unset=") or token.startswith("--chdir="):
            index += 1
        elif token.startswith("-"):
            return None
        else:
            return index
    return index


def unwrap_command(tokens):
    index = 0
    while index < len(tokens):
        name = os.path.basename(tokens[index])
        if _assignment(tokens[index]):
            index += 1
        elif name == "env":
            index = _environment_end(tokens, index)
            if index is None:
                return None, "an env option is ambiguous and cannot be inspected"
        elif name == "rtk":
            index += 1
            if index < len(tokens) and tokens[index] == "proxy":
                index += 1
            elif index < len(tokens) and tokens[index].startswith("-") and tokens[index] not in {"--help", "--version"}:
                return None, "an rtk option is ambiguous and cannot be inspected"
        elif name in {"command", "builtin", "exec"}:
            index += 1
        else:
            break
    return tokens[index:], None
