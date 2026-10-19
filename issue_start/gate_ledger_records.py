from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from . import worktree_ledger
from .gate_ledger_metadata import _ledger_metadata
from .gate_support import IssueStartRequest, IsolationOnlyAck



def record_open_entry(
    payload: Mapping[str, Any],
    request: IssueStartRequest,
    *,
    now: datetime,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """ALLOW した dispatch を worktree 所有台帳へ ``open`` 起票する（Issue #309・PR-1）。

    **この関数は dispatch を deny しない。** 台帳の書込に失敗しても例外を投げず、
    ``{"entry_id": None, "error": "<reason>"}`` を返して呼び出し側は ALLOW のまま進む
    （本 PR は fail-open）。deny へ倒すのは PR-3（統制の発効）——「統制を先に、付与は別 PR」
    と同じ理由で、**観測が正確になったことを実測してから** deny を有効にする。

    ``round`` / ``handoff_path`` は現行の ``ISSUE_START_BINDING_V1`` marker schema に無いので
    ``None`` のまま起票する（marker 拡張は PR-4）。
    """
    try:
        root = worktree_ledger.main_worktree_root(
            Path.cwd() if repo_root is None else Path(repo_root)
        )
        agent_type, branch_name = _ledger_metadata(payload)
        if agent_type is None:
            return {"entry_id": None, "error": "LEDGER_AGENT_TYPE_UNREADABLE"}
        entry_id = worktree_ledger.open_entry(
            root,
            issue=request.issue,
            agent_type=agent_type,
            round=None,
            branch_name=branch_name,
            handoff_path=None,
            now=now,
        )
        return {"entry_id": entry_id, "error": None}
    except worktree_ledger.LedgerError as exc:
        return {"entry_id": None, "error": exc.reason, "detail": exc.detail}
    except Exception as exc:  # 台帳の事故で dispatch を止めない（本 PR は fail-open）
        return {"entry_id": None, "error": type(exc).__name__}


def record_isolation_only_entry(
    ack: IsolationOnlyAck,
    *,
    now: datetime,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """`isolation_only` の ALLOW を worktree 所有台帳へ ``open`` 起票する（Issue #354 PR-4）。

    **起票は省略できない**——`isolation: "worktree"` を課した以上、是正ラウンドも
    `.claude/worktrees/agent-<id>/` を占有する。`open` エントリが無いと
    `SubagentStart`（`worktree_ledger.bind_agent`）が束縛先を見つけられず、その worktree は
    台帳のどのエントリにも紐づかない＝次の dispatch が `ISSUE_START_WORKTREE_UNCLAIMED` で
    deny される（統制が機能不全ではなく**過剰 deny**として現れる）。

    managed 側（:func:`record_open_entry`）と違い ``round`` / ``handoff_path`` を
    **推測せず marker の値で埋める**（FR-W4 の完全化）。台帳の書込失敗は dispatch を
    止めない（fail-open）＝managed 側と同じ扱い。
    """
    try:
        root = worktree_ledger.main_worktree_root(
            Path.cwd() if repo_root is None else Path(repo_root)
        )
        entry_id = worktree_ledger.open_entry(
            root,
            issue=ack.issue,
            agent_type=ack.agent_type,
            round=ack.round,
            branch_name=ack.branch_name,
            handoff_path=ack.handoff_path,
            now=now,
        )
        return {"entry_id": entry_id, "error": None}
    except worktree_ledger.LedgerError as exc:
        return {"entry_id": None, "error": exc.reason, "detail": exc.detail}
    except Exception as exc:
        return {"entry_id": None, "error": type(exc).__name__}
