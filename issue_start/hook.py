"""Codex/Claude 共通 PreToolUse hook entry。"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, TextIO

from blocker_gate.auth import resolve_github_token

from .gate import (
    ISSUE_START_POLICY_VERSION,
    IssueStartError,
    assert_no_worktree_residue,
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

    ``now`` / ``ledger_root`` は Issue #309 の worktree 所有台帳への起票と、Issue #354 の
    残留 worktree 判定のための注入点。``ledger_root`` を省略すると ``cwd``（さらに省略時は
    プロセスの cwd）から ``main_worktree_root()`` で main worktree へ収束させる。
    **時刻を読むのはここ（composition root）だけ**で、``worktree_ledger`` は
    ``datetime.now()`` を呼ばない。

    段（前段で deny したら後段へ進まない）:

    1. payload を読む（読めなければ ``ISSUE_START_PAYLOAD_INVALID`` で deny）
    2. managed binding を読む（unmanaged なら ``request is None``）
    3. **残留 worktree の deny**（Issue #354・:func:`assert_no_worktree_residue`）。
       **unmanaged も含む全 dispatch に掛かる**ので 2 の結果を待たずここで判定する
    4. unmanaged ならここで exit 0（blocker 判定は managed のみ）。**stdout は無出力のまま
       だが、stderr へ residue 判定（``swept``/``claimed``/``unclaimed`` を含む）を
       evidence として1行残す**（F-354-08）——#354 が実測した乗っ取りは unmanaged 側
       （``pr-reviewer``）で起きたので、まさにこの経路の観測性が欠けていた
    5. blocker 判定 → ALLOW なら台帳へ ``open`` 起票
    """
    request = None
    payload: Mapping[str, Any] | None = None
    stamp = datetime.now(timezone.utc) if now is None else now
    residue: dict[str, Any] | None = None
    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            raise IssueStartError("ISSUE_START_PAYLOAD_INVALID")
        request = parse_dispatch_payload(payload, cwd=cwd)
        # Issue #354 PR-3: 残留 worktree のある状態では**どの** dispatch も通さない
        # （managed / unmanaged を問わない＝#354 が実測した乗っ取りは `pr-reviewer`＝
        # unmanaged 側で起きたため）。台帳が読めなければ fail-close。
        residue = assert_no_worktree_residue(
            repo_root=ledger_root if ledger_root is not None else cwd, now=stamp
        )
        if request is None:
            # unmanaged dispatch でも残留判定は走っている（3 で判定済み）。ALLOW（deny しない）
            # 経路をそのまま黙って返すと、判定が実行されたこと自体が事後に確認できない
            # （F-354-08：#354 が実測した乗っ取りはまさにこの unmanaged 側で起きた）。
            # stdout は汚さず（unmanaged は素通しのまま）、stderr にだけ evidence を残す。
            stderr.write(
                json.dumps(
                    {
                        "schema_version": "issue-start-evidence/1",
                        "policy_version": ISSUE_START_POLICY_VERSION,
                        "result": "UNMANAGED",
                        "worktree_residue": residue,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
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
    evidence["worktree_residue"] = residue
    evidence["ledger"] = record_open_entry(
        payload if isinstance(payload, Mapping) else {},
        request,
        now=stamp,
        repo_root=ledger_root if ledger_root is not None else cwd,
    )
    # allow は stdout を空に保ち、hook protocol を汚さず evidence を harness log に残す。
    stderr.write(json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


def main() -> int:
    return run(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
