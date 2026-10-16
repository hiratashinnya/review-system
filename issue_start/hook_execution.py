"""PreToolUse hook の payload、判定、台帳フローを実行する。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, TextIO

from .hook_early import handle_early_request
from .hook_protocol import write_deny, write_evidence


def run_flow(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    cwd: Path | None,
    stamp: datetime,
    ledger_root: Path | None,
    policy_version: str,
    isolation_ack_type: type,
    error_type: type[Exception],
    parse_payload: Callable[..., Any],
    assert_no_residue: Callable[..., Any],
    evaluate: Callable[..., Mapping[str, Any]],
    fail_closed: Callable[..., Mapping[str, Any]],
    resolve_token: Callable[[], str | None],
    record_isolation_entry: Callable[..., Any],
    record_open_entry: Callable[..., Any],
) -> int:
    request = None
    payload: Mapping[str, Any] | None = None
    residue: Mapping[str, Any] | None = None
    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            raise error_type("ISSUE_START_PAYLOAD_INVALID")
        request = parse_payload(payload, cwd=cwd, now=stamp)
        # 残留 worktree は managed / unmanaged を問わず全 dispatch を fail-close する。
        residue = assert_no_residue(
            repo_root=ledger_root if ledger_root is not None else cwd, now=stamp
        )
        early_exit = handle_early_request(
            request,
            isolation_ack_type=isolation_ack_type,
            policy_version=policy_version,
            residue=residue or {},
            stamp=stamp,
            cwd=cwd,
            ledger_root=ledger_root,
            record_isolation_entry=record_isolation_entry,
            stderr=stderr,
        )
        if early_exit is not None:
            return early_exit
        # cwd は snapshot fallback（Issue #345）の git fetch 起点。
        evidence = evaluate(request, token=resolve_token(), cwd=cwd)
    except (json.JSONDecodeError, UnicodeDecodeError):
        evidence = fail_closed(request, error_type("ISSUE_START_PAYLOAD_INVALID"))
    except error_type as exc:
        evidence = fail_closed(request, exc)

    if evidence["result"] != "ALLOW":
        return write_deny(stdout, evidence)
    # Issue #309: ALLOW の台帳起票は fail-open を維持する。
    evidence = dict(evidence)
    evidence["worktree_residue"] = residue
    evidence["ledger"] = record_open_entry(
        payload if isinstance(payload, Mapping) else {},
        request,
        now=stamp,
        repo_root=ledger_root if ledger_root is not None else cwd,
    )
    write_evidence(stderr, evidence)
    return 0
