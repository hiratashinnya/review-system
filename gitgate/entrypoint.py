"""Dispatch the public gitgate command line to each verb family."""

import sys

from .cli import main as git_main
from .show_pr_diff import main as show_pr_diff_main


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "show-pr-diff":
        return show_pr_diff_main(argv[1:])
    return git_main(argv)
