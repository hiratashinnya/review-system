"""Remove environment and command wrappers before executable inspection."""

import os

from .command_segments import assignment_token


def _environment_end(tokens, index):
    index += 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return index + 1
        if token in {"-i", "--ignore-environment"} or assignment_token(token):
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
        if assignment_token(tokens[index]):
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
            index += 2 if name == "command" and index + 1 < len(tokens) and tokens[index + 1] == "-p" else 1
        else:
            break
    return tokens[index:], None
