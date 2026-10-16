"""PreToolUse hook の unmanaged / isolation-only 応答を処理する。"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, TextIO

from .hook_protocol import write_evidence


def handle_early_request(
    request: Any,
    *,
    isolation_ack_type: type,
    policy_version: str,
    residue: Mapping[str, Any],
    stamp: datetime,
    cwd: Path | None,
    ledger_root: Path | None,
    record_isolation_entry: Callable[..., Any],
    stderr: TextIO,
) -> int | None:
    """Unmanaged と isolation-only を処理し、managed request は呼び出し元へ戻す。"""
    if request is None:
        # unmanaged も residue 判定を通過した証跡を stderr に残し、stdout は空に保つ。
        write_evidence(
            stderr,
            {
                "schema_version": "issue-start-evidence/1",
                "policy_version": policy_version,
                "result": "UNMANAGED",
                "worktree_residue": residue,
            },
        )
        return 0
    if not isinstance(request, isolation_ack_type):
        return None

    # Issue #354 PR-4: blocker gate（GitHub API）を呼ばず、分離台帳だけに起票する。
    evidence = {
        "schema_version": "issue-start-evidence/1",
        "policy_version": policy_version,
        "result": "ISOLATION_ONLY",
        "exit_code": 0,
        "reason": "ISSUE_START_ISOLATION_ONLY_ALLOWED",
        "binding": asdict(request),
        "blocker_evidence": None,
        "blockers": [],
        "source": None,
        "snapshot_generated_at": None,
        "worktree_residue": residue,
        "ledger": record_isolation_entry(
            request,
            now=stamp,
            repo_root=ledger_root if ledger_root is not None else cwd,
        ),
    }
    write_evidence(stderr, evidence)
    return 0
