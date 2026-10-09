"""CLI commands for proposal lifecycle decisions."""

from __future__ import annotations

import datetime
import sys

from .cli_commit import _commit
from .cli_support import EXIT_ERROR, EXIT_NOT_FOUND, _require_proposal
from .schema import PROPOSAL_SPEC
from .store import load_store

def _decide(args, *, new_status, require_status="pending", updates=None) -> int:
    root = args.root
    store = load_store(root)
    document = _require_proposal(store, args.proposal)
    if document is None:
        return EXIT_NOT_FOUND
    if document.data["status"] != require_status:
        print(
            f"ERROR: [P1] {require_status} の改訂案にだけ実行できる"
            f"（現在: {document.data['status']}）",
            file=sys.stderr,
        )
        return EXIT_ERROR
    data = dict(document.data)
    data["status"] = new_status
    data.update(updates or {})
    return _commit(root, PROPOSAL_SPEC, data)


def cmd_approve(args) -> int:
    return _decide(args, new_status="approved", updates={
        "decided_in": args.triage,
        "decided_by": args.by,
        "decided_at": args.now or datetime.date.today(),
        "decision_reason": args.reason or "",
    })


def cmd_reject(args) -> int:
    return _decide(args, new_status="rejected", updates={
        "decided_in": args.triage or "",
        "decided_by": args.by,
        "decided_at": args.now or datetime.date.today(),
        "decision_reason": args.reason,
    })


def cmd_apply_done(args) -> int:
    return _decide(args, new_status="applied", require_status="approved", updates={
        "issue_ref": args.issue_ref,
        "applied_pr": args.applied_pr,
    })
