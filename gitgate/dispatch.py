"""Public CLI dispatch, including the large PR diff wrapper."""

import sys

from .cli import main as git_main
from .pr_diff import PrDiffError, run_pr_diff
from .base_cli import refuse_pending_publish, run_cli
from .base_error import BaseIntegrationError
from .base_request import VERBS
from pathlib import Path
from issue_start.worktree_ledger import LedgerError


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in VERBS:
        return run_cli(args)
    if args and args[0] in {"commit", "push"}:
        try:
            refuse_pending_publish(Path.cwd())
        except (BaseIntegrationError, LedgerError) as exc:
            sys.stderr.write(f"gitgate: {exc}\n")
            return 2
    if not args or args[0] != "show-pr-diff":
        return git_main(args)
    try:
        return run_pr_diff(args[1:])
    except PrDiffError as exc:
        sys.stderr.write(f"gitgate: {exc}\n")
        return 2
