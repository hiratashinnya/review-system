"""Codex/Claude 共通 PreToolUse hook entry。"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, TextIO

from blocker_gate.auth import resolve_github_token

from .gate import (
    IssueStartError,
    evaluate_issue_start,
    fail_closed,
    parse_dispatch_payload,
    record_open_entry,
)


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _deny_reason(evidence: Mapping[str, Any]) -> str:
    reason = (
        f"issue-start-gate: {evidence['result']} {evidence['reason']} "
        f"policy={evidence['policy_version']}"
    )
    # detail は fail-close の「何を直せばよいか」を持つ唯一の項目（例: isolation の期待値と実測値、
    # tool_input の missing/mixed field 名）。落とすと deny が不透明な reason code だけになり、
    # dispatch 側が修正できない。ALLOW 以外でしか表示されないので情報量の増加は deny 経路に閉じる。
    detail = evidence.get("detail")
    if isinstance(detail, str) and detail:
        reason += f" detail={detail}"
    blockers = evidence.get("blockers")
    if isinstance(blockers, list) and blockers:
        reason += " blockers=" + json.dumps(
            blockers, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    return reason


def run(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    cwd: Path | None = None,
    now: datetime | None = None,
    ledger_root: Path | None = None,
) -> int:
    """PreToolUse hook 本体。

    ``now`` / ``ledger_root`` は Issue #309 の worktree 所有台帳への起票のための注入点。
    ``ledger_root`` を省略すると ``cwd``（さらに省略時はプロセスの cwd）から
    ``main_worktree_root()`` で main worktree へ収束させる。**時刻を読むのはここ
    （composition root）だけ**で、``worktree_ledger`` は ``datetime.now()`` を呼ばない。
    """
    request = None
    payload: Mapping[str, Any] | None = None
    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            raise IssueStartError("ISSUE_START_PAYLOAD_INVALID")
        request = parse_dispatch_payload(payload, cwd=cwd)
        if request is None:
            return 0
        # cwd は snapshot fallback（Issue #345）の git fetch 起点。
        evidence = evaluate_issue_start(
            request, token=resolve_github_token(), cwd=cwd
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        evidence = fail_closed(request, IssueStartError("ISSUE_START_PAYLOAD_INVALID"))
    except IssueStartError as exc:
        evidence = fail_closed(request, exc)
    if evidence["result"] != "ALLOW":
        json.dump(
            _deny(_deny_reason(evidence)),
            stdout,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        stdout.write("\n")
        return 0
    # Issue #309: ALLOW した dispatch だけを worktree 所有台帳へ `open` 起票する。
    # **書込に失敗しても ALLOW のまま**（本 PR は fail-open。deny への昇格は PR-3）。
    evidence = dict(evidence)
    evidence["ledger"] = record_open_entry(
        payload if isinstance(payload, Mapping) else {},
        request,
        now=datetime.now(timezone.utc) if now is None else now,
        repo_root=ledger_root if ledger_root is not None else cwd,
    )
    # allow は stdout を空に保ち、hook protocol を汚さず evidence を harness log に残す。
    stderr.write(json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


def main() -> int:
    return run(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
