"""Inspect shell tokens for Git and GitHub CLI merge commands."""

import os

from .command_segments import command_segments
from .command_substitutions import shell_substitutions
from .command_wrappers import unwrap_command
from .github_api import merge_api_reason
from .global_options import skip_global_options

_DATA_COMMANDS = {"echo", "printf", "grep", "rg", "cat", "head", "tail", "cut", "sort", "uniq", "wc", "tr"}


def _inspect_segment(tokens, depth=0):
    tokens, error = unwrap_command(tokens)
    if error or not tokens: return error
    executable = os.path.basename(tokens[0])
    if executable not in {"git", "gh"}:
        if any(mark in tokens[0] for mark in ("$", "`")):
            return "the executable name is dynamically expanded and cannot be inspected"
        if executable in _DATA_COMMANDS: return None
        for offset, token in enumerate(tokens[1:], 1):
            name = os.path.basename(token)
            if name in {"git", "gh"}:
                reason = _inspect_segment(tokens[offset:], depth + 1)
            elif " " in token:
                reason = _inspect(token, depth + 1)
            elif any(marker in token.lower() for marker in ("auto-merge", "mergepullrequest", "enablepullrequestautomerge")):
                reason = "an indirect merge operation cannot be inspected safely"
            else:
                continue
            if reason:
                return f"an unclassified executable precedes a merge-capable command: {reason}"
        return None
    index, error = skip_global_options(tokens, executable)
    if error: return error
    if index is None or index >= len(tokens): return None
    subcommand = tokens[index]
    if any(mark in subcommand for mark in ("$", "`")):
        return "the Git or GitHub subcommand is dynamically expanded and cannot be inspected"
    if executable == "git" and subcommand == "merge": return "the git merge subcommand is denied"
    if executable == "gh" and subcommand == "api":
        return merge_api_reason(tokens[index + 1 :])
    if executable == "gh" and subcommand == "pr":
        action, error = skip_global_options(tokens, executable, index + 1)
        if error: return error
        if action < len(tokens) and (tokens[action] == "merge" or any(mark in tokens[action] for mark in ("$", "`"))): return "the gh pr merge command is denied or its action is dynamically expanded"
    return None


def _inspect(command, depth=0):
    if depth > 3: return "nested command text is too complex to inspect"
    segments = command_segments(command)
    if segments is None:
        return "shell tokenization failed; refusing because the command cannot be inspected"
    for segment, source in segments:
        nested = shell_substitutions(source)
        if nested is None: return "shell command substitution cannot be inspected safely"
        for command_text in nested:
            reason = _inspect(command_text, depth + 1)
            if reason: return reason
        reason = _inspect_segment(segment, depth)
        if reason: return reason
    return None


def merge_command_reason(command):
    """Return a denial reason for merge forms, or None for inspected non-merge commands."""
    return _inspect(command)
