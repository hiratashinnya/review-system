"""Codex wrapper の ``pr-reviewer`` 起動をコマンド行から検出する。"""

from __future__ import annotations

import re
import shlex

from .shell_tokens import is_executable_prefix, tokenize_shell

CODEX_MODULES = {"codex_worktree_exec", "issue_start.readonly_workspace"}
HEREDOC_PATTERN = re.compile(
    r'''<<(-?)[ \t]*((?:[^\s;|&<>'"\\]|\\[^\n]|'[^'\n]*'|"(?:\\.|[^"\\\n])*")+)'''
)
VALUE_OPTIONS = {
    "-C", "--prompt-file", "--output-file", "--binding-file", "--model",
    "--reasoning-effort", "--timeout-seconds", "--approval-file", "--source",
}


def is_codex_reviewer(command: str) -> bool:
    """シェルのコメントを除き、role が pr-reviewer の起動を探す。"""
    try:
        return any(_tokens_are_codex_reviewer(tokens) for tokens in tokenize_shell(_without_shell_comments(command)))
    except ValueError:
        for line in command.splitlines():
            try:
                groups = tokenize_shell(_without_shell_comments(line))
            except ValueError:
                continue
            if any(_tokens_are_codex_reviewer(tokens) for tokens in groups):
                return True
        return False


def _without_shell_comments(command: str) -> str:
    """未引用で単語先頭の ``#`` から行末を落とす。"""
    result = []
    quote = None
    escaped = False
    in_comment = False
    heredocs = []
    for line in command.splitlines(keepends=True):
        if heredocs:
            delimiter, strip_tabs = heredocs[0]
            terminator = line.rstrip("\n")
            if strip_tabs:
                terminator = terminator.lstrip("\t")
            if terminator == delimiter:
                heredocs.pop(0)
            continue
        clean_line = []
        for index, char in enumerate(line):
            if char == "\n":
                in_comment = False
                escaped = False
                clean_line.append(char)
                continue
            if in_comment:
                continue
            if escaped:
                escaped = False
            elif char == "\\" and quote != "'":
                escaped = True
            elif quote:
                if char == quote:
                    quote = None
            elif char in {"'", '"'}:
                quote = char
            elif char == "<" and (index == 0 or line[index - 1] != "<") and not line.startswith("<<<", index):
                match = HEREDOC_PATTERN.match(line, index)
                if match:
                    delimiters = shlex.split(match.group(2))
                    if len(delimiters) == 1:
                        heredocs.append((delimiters[0], bool(match.group(1))))
            elif char == "#" and (not clean_line or clean_line[-1].isspace()
                                   or clean_line[-1] in ";&|()"):
                in_comment = True
                continue
            clean_line.append(char)
        result.extend(clean_line)
    return "".join(result)


def _tokens_are_codex_reviewer(tokens: list[str]) -> bool:
    for index, token in enumerate(tokens[:-1]):
        if (token != "-m" or index == 0 or tokens[index - 1] not in {"python", "python3"}
                or not is_executable_prefix(tokens[:index - 1])
                or tokens[index + 1] not in CODEX_MODULES):
            continue
        arguments = iter(tokens[index + 2:])
        for argument in arguments:
            if argument in VALUE_OPTIONS:
                next(arguments, None)
            elif argument.startswith("--role=") and argument.partition("=")[2] == "pr-reviewer":
                return True
            elif argument == "--role" and next(arguments, None) == "pr-reviewer":
                return True
    return False
