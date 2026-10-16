"""Detect unreleased or unclaimed worktrees before dispatch."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
from typing import Any, Callable

from . import worktree_ledger
from .gate_release import _finish_deferred_releases
from .gate_residue_helpers import _residue_items, _residue_root
from .gate_support import IssueStartError


def assert_no_worktree_residue(
    *,
    repo_root: Path | None = None,
    now: datetime,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """残留 worktree がある状態での次 dispatch を deny する（Issue #354・PR-3・候補C）。

    **`issue-implementer` に限らず全 `Task` dispatch へ掛ける。** #354 が実測した事象は
    「残留 worktree があるのに `pr-reviewer` を dispatch し、レビューアが古い作業ツリーを
    掴んだ」というものであり、managed dispatch だけを見張っていては正面から塞げない。
    過剰 deny の緩和は **deny 文言に必ず解消コマンドを載せる**ことと
    ``worktree-forget --reason`` の逃げ道で行う（deny を弱めることでは行わない）。

    判定の前に :func:`worktree_ledger.sweep_orphans` を1回走らせる。掃引は「占有を主張して
    いるのに worktree が実在しない」エントリだけを ``stale`` へ落とす状態→状態の照合で、
    落とす候補が無ければ台帳へ書き込まない（正常系では no-op）。

    掃引の直後に :func:`_finish_deferred_releases` を走らせる（Issue #464）。``SubagentStop``
    が handoff を回収したのに ``git worktree remove`` が worktree ロックで失敗して
    ``release_pending`` に留まったエントリの削除を、ロックの外れたこの地点でリトライする
    ——成功すれば ``released``、失敗しても dispatch は止めない（成果物は既に退避済み）。

    ==============================================  ===================================
    reason                                          条件
    ==============================================  ===================================
    ``ISSUE_START_WORKTREE_RESIDUE``                ``stale`` / ``stopped`` / ``collected``
                                                    のエントリが1件以上ある
                                                    （``release_pending`` は**含めない**
                                                    ——回収済みで削除だけ遅延・Issue #464）
    ``ISSUE_START_WORKTREE_UNCLAIMED``              ディスク上の ``agent-*`` が
                                                    ``running`` / ``stopped`` のどれにも
                                                    紐づかない
    ``ISSUE_START_WORKTREE_LEDGER_ERROR``           台帳が読めない／壊れている（fail-close）
    ==============================================  ===================================

    ``open`` / ``running`` / ``stopped`` の worktree は live もしくは回収処理中なので
    ``unclaimed`` としては扱わない。``stopped`` だけは **residue としても検出する**
    ——``SubagentStop`` が停止を記録したのに ``collected`` まで進んでいない＝回収段が
    失敗したか実行されていない、という意味だから（:func:`worktree_ledger.residue_report`
    の docstring に二重の性質の説明がある）。

    残留が無ければ組み立てた report を返す（呼び出し側が evidence に載せる）。
    """
    try:
        root = _residue_root(repo_root)
        swept = worktree_ledger.sweep_orphans(root, now=now)
        deferred_release_finished = _finish_deferred_releases(root, now=now, runner=runner)
        report = worktree_ledger.residue_report(root)
    except worktree_ledger.LedgerError as exc:
        raise IssueStartError(
            "ISSUE_START_WORKTREE_LEDGER_ERROR",
            f"{exc.reason}{': ' + exc.detail if exc.detail else ''}"
            "（台帳を一意に読めない間は dispatch を通さない＝fail-close）",
        ) from exc
    except Exception as exc:
        raise IssueStartError(
            "ISSUE_START_WORKTREE_LEDGER_ERROR", type(exc).__name__
        ) from exc

    if report["stale"]:
        raise IssueStartError(
            "ISSUE_START_WORKTREE_RESIDUE",
            f"未回収の worktree が残っている: {_residue_items(report['stale'])}"
            "。解消: python3 -m gitgate collect-worktree --entry <entry-id>"
            "（回収不能なら python3 -m gitgate worktree-forget --entry <entry-id>"
            " --reason <text>）",
        )
    if report["unclaimed"]:
        raise IssueStartError(
            "ISSUE_START_WORKTREE_UNCLAIMED",
            f"台帳のどのエントリにも紐づかない worktree がある: {', '.join(report['unclaimed'])}"
            "。解消: python3 -m gitgate worktree-release <path> --force-uncollected"
            " --reason <text>",
        )
    return {
        "swept": swept,
        "deferred_release_finished": deferred_release_finished,
        **report,
    }
