"""Claude Code の managed-dispatch 用 PreToolUse hook entry。"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from blocker_gate.auth import resolve_github_token

from .gate import (
    ISSUE_START_POLICY_VERSION,
    IsolationOnlyAck,
    IssueStartError,
    assert_no_worktree_residue,
    evaluate_issue_start,
    fail_closed,
    parse_dispatch_payload,
    record_isolation_only_entry,
    record_open_entry,
)
from .hook_execution import run_flow
from .hook_protocol import deny as _deny
from .hook_protocol import deny_reason as _deny_reason


def run(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    cwd: Path | None = None,
    now: datetime | None = None,
    ledger_root: Path | None = None,
) -> int:
    """Compose hook dependencies and execute the shared dispatch protocol.

    ``now`` and ``ledger_root`` remain injectable for deterministic ledger and residue checks.
    """
    stamp = datetime.now(timezone.utc) if now is None else now
    return run_flow(
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        cwd=cwd,
        stamp=stamp,
        ledger_root=ledger_root,
        policy_version=ISSUE_START_POLICY_VERSION,
        isolation_ack_type=IsolationOnlyAck,
        error_type=IssueStartError,
        parse_payload=parse_dispatch_payload,
        assert_no_residue=assert_no_worktree_residue,
        evaluate=evaluate_issue_start,
        fail_closed=fail_closed,
        resolve_token=resolve_github_token,
        record_isolation_entry=record_isolation_only_entry,
        record_open_entry=record_open_entry,
    )


def main() -> int:
    return run(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
