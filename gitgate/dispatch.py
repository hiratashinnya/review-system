"""Public CLI dispatch, including the large PR diff wrapper."""

import sys

from .cli import main as git_main
from .pr_diff import PrDiffError, run_pr_diff


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] != "show-pr-diff":
        return git_main(args)
    try:
        return run_pr_diff(args[1:])
    except PrDiffError as exc:
        sys.stderr.write(f"gitgate: {exc}\n")
        return 2
