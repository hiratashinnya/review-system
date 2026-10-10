"""Policy dispatcher and the ordinary commit/push fence for pending integration."""

import json
import sys
from pathlib import Path
from issue_start import worktree_ledger
from branch_source.policy import BranchSourceError
from .base_abort import abort
from .base_authority import identity
from .base_continue import continue_integration
from .base_error import BaseIntegrationError, require
from .base_journal import active_operation
from .base_live import default_api
from .base_request import VERBS, parse_request
from .base_start import start


def execute(verb, args, *, workspace=None, api=None):
    request = parse_request(verb, list(args))
    root, entry, binding = identity(workspace or Path.cwd())
    if verb == "integrate-base":
        return start(root, entry, binding, request, api or default_api())
    operation = active_operation(entry)
    if verb == "integrate-base-abort":
        return abort(root, entry, binding, operation)
    return continue_integration(root, entry, binding, operation, request["test_modules"],
                                api or default_api())


def refuse_pending_publish(workspace):
    root = worktree_ledger.main_worktree_root(workspace)
    relative = Path(workspace).resolve().relative_to(root.resolve()).as_posix()
    entries = worktree_ledger.read_ledger(root)["entries"]
    require(not any(entry.get("worktree_path") == relative and active_operation(entry)
                    for entry in entries), "BASE_PENDING_COMMIT_PUSH_DENIED")


def run_cli(args):
    try:
        result = execute(args[0], args[1:])
        print(json.dumps(result, ensure_ascii=False))
        return 3 if result["status"] == "conflicts" else 0
    except (BaseIntegrationError, worktree_ledger.LedgerError,
            BranchSourceError) as exc:
        sys.stderr.write(f"gitgate: {exc}\n")
        return 2
