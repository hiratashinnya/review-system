"""Read-only `gh pr diff` command used by the PR reviewer."""

import subprocess
import sys

from .cli import GitgateError, validate_integer


def build_show_pr_diff_argv(args):
    """Build only the fixed, read-only GitHub CLI command for one PR diff."""
    if len(args) != 1:
        raise GitgateError("`show-pr-diff` requires exactly one positive PR number")
    pr_number = validate_integer(args[0])
    if not any(digit != "0" for digit in pr_number):
        raise GitgateError("`show-pr-diff` requires a positive PR number")
    return ["gh", "pr", "diff", pr_number]


def main(args):
    try:
        argv = build_show_pr_diff_argv(args)
    except GitgateError as exc:
        sys.stderr.write(f"gitgate: {exc}\n")
        return 2
    try:
        return subprocess.run(argv, shell=False).returncode
    except OSError as exc:
        sys.stderr.write(f"gitgate: command execution failed: {exc}\n")
        return 127
