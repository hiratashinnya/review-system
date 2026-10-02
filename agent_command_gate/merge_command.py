"""Inspect shell tokens for Git and GitHub CLI merge commands."""

import os

from .command_tokens import command_segments, unwrap_command
from .github_api import merge_api_reason
from .global_options import skip_global_options


def _inspect_segment(tokens):
    for token in tokens:
        if "$(" in token or "`" in token:
            nested = token.replace("$(", " ").replace("`", " ").replace(")", " ")
            if nested.strip() and nested != token:
                reason = _inspect(nested, 1)
                if reason:
                    return reason
    tokens, error = unwrap_command(tokens)
    if error:
        return error
    if not tokens:
        return None
    executable = os.path.basename(tokens[0])
    if executable not in {"git", "gh"} and any(mark in tokens[0] for mark in ("$", "`")):
        return "the executable name is dynamically expanded and cannot be inspected"
    if executable not in {"git", "gh"}:
        return None
    index, error = skip_global_options(tokens, executable)
    if error:
        return error
    if index is None or index >= len(tokens):
        return None
    subcommand = tokens[index]
    if any(mark in subcommand for mark in ("$", "`")):
        return "the Git or GitHub subcommand is dynamically expanded and cannot be inspected"
    if executable == "git" and subcommand == "merge":
        return "the git merge subcommand is denied"
    if executable == "gh" and subcommand == "pr":
        action = index + 1
        while action < len(tokens):
            option = tokens[action].partition("=")[0]
            if option not in {"-R", "--repo", "--hostname"}:
                break
            if "=" in tokens[action]:
                action += 1
                continue
            if action + 1 >= len(tokens):
                return "a GitHub repository option is missing its value"
            action += 2
        if action < len(tokens) and tokens[action] == "merge":
            return "the gh pr merge command is denied"
    if executable == "gh" and subcommand == "api":
        return merge_api_reason(tokens[index + 1 :])
    return None


def _inspect(command, depth=0):
    if depth > 3:
        return "nested command substitution is too complex to inspect"
    segments = command_segments(command)
    if segments is None:
        return "shell tokenization failed; refusing because the command cannot be inspected"
    for segment in segments:
        reason = _inspect_segment(segment)
        if reason:
            return reason
    return None


def merge_command_reason(command):
    """Return a denial reason for merge forms, or None for inspected non-merge commands."""
    return _inspect(command)
