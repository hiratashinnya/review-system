"""Abandon a stale entry while retaining its ledger record and worktree."""

from issue_start.worktree_ledger import LedgerError, add_note
from .worktree_models import WorktreeError
from .worktree_arg_common import _validate_entry_id, _validate_reason
from .worktree_ledger_access import find_entry, _mark

def worktree_forget(repo_root, entry_id: str, *, reason: str, now) -> dict:
    """回収不能な ``stale`` エントリを ``abandoned`` へ逃がす（**worktree は消さない**）。

    PR-3 の deny が恒久的にパイプラインを止めるのを防ぐ唯一の逃げ道なので、``reason`` を
    必須にして「なぜ諦めたか」を必ず残す。**エントリは削除しない**（PR8 区分1＝保全対象）。

    ディスク上に実体が残っている場合は、この verb の**後で** :func:`worktree_release` を
    呼んで削除する（``abandoned`` のまま実体だけ消える）。この2手順以外に実体を消す経路は
    無い——回収の記録（``abandoned`` の理由）と実体の削除を1つの verb に混ぜない。
    """
    _validate_entry_id(entry_id)
    _validate_reason(reason)
    entry = find_entry(repo_root, entry_id=entry_id)
    if entry is None:
        raise WorktreeError("WORKTREE_ENTRY_NOT_FOUND", entry_id)
    if entry.get("status") == "abandoned":
        # 冪等: 既に abandoned なら理由を1行足すだけ（状態機械は進めない）。
        try:
            add_note(repo_root, entry_id, now=now, note=f"worktree-forget (repeat): {reason}")
        except LedgerError as exc:
            raise WorktreeError(exc.reason, exc.detail) from exc
        return find_entry(repo_root, entry_id=entry_id)
    _mark(repo_root, entry_id, "abandoned", now=now, note=f"worktree-forget: {reason}")
    return find_entry(repo_root, entry_id=entry_id)


# --- verb: worktree-sweep-abandoned ---------------------------------------------

# 掃引で台帳へ残す marker（notes を grep すれば「なぜ解放されたか」が後から辿れる）。
SWEEP_MARKER = "worktree-sweep-abandoned"
