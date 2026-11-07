"""Non-fatal cleanup of a local branch ref after worktree removal."""

import subprocess
from typing import Callable
from .worktree_config import FETCH_TIMEOUT_SECONDS
from .worktree_git_runtime import _run_git, _fetch_env
from .worktree_ledger_access import _note

def _cleanup_branch_ref(repo_root, entry, *, now, runner: Callable[..., subprocess.CompletedProcess]) -> None:
    """Delete only when the local tip is contained in the freshly fetched remote tip."""
    if entry is None:
        return
    branch_name = entry.get("branch_name")
    entry_id = entry.get("entry_id")
    if not branch_name or entry_id is None:
        return

    def _skip(reason: str) -> None:
        _note(
            repo_root,
            entry_id,
            now=now,
            note=(
                f"worktree-release: ローカルブランチ ref {branch_name} の削除を"
                f"スキップした（{reason}）"
            ),
        )

    try:
        fetch_result = _run_git(
            ["git", "fetch", "--prune", "origin"],
            cwd=repo_root,
            runner=runner,
            timeout=FETCH_TIMEOUT_SECONDS,
            env=_fetch_env(),
        )
    except subprocess.TimeoutExpired:
        # フェイルオープン: 到達不能/認証待ちの origin で無期限にハングしない
        # （Issue #426・F-426-05）。worktree_release() 自体は失敗させず、理由だけ記録する。
        _skip(f"origin の fetch がタイムアウトした（{FETCH_TIMEOUT_SECONDS}秒）")
        return
    except Exception as exc:  # noqa: BLE001 - フェイルオープン: 記録するだけで再送出しない
        _skip(f"origin の fetch に失敗: {str(exc)[:200]}")
        return
    if fetch_result.returncode != 0:
        _skip(f"origin の fetch に失敗: {(fetch_result.stderr or '').strip()[:200]}")
        return

    try:
        ancestor_check = _run_git(
            [
                "git", "merge-base", "--is-ancestor",
                f"refs/heads/{branch_name}", f"refs/remotes/origin/{branch_name}",
            ],
            cwd=repo_root,
            runner=runner,
        )
    except Exception as exc:  # noqa: BLE001 - フェイルオープン: 記録するだけで再送出しない
        _skip(f"origin 包含の判定に失敗: {str(exc)[:200]}")
        return
    if ancestor_check.returncode != 0:
        _skip(f"origin/{branch_name} に含まれない、または判定不能")
        return

    try:
        result = _run_git(["git", "branch", "-D", branch_name], cwd=repo_root, runner=runner)
        ok = result.returncode == 0
        detail = "" if ok else (result.stderr or "").strip()[:200]
    except Exception as exc:  # noqa: BLE001 - フェイルオープン: 記録するだけで再送出しない
        ok = False
        detail = str(exc)[:200]
    if ok:
        note = f"worktree-release: ローカルブランチ ref {branch_name} を削除した"
    else:
        note = f"worktree-release: ローカルブランチ ref {branch_name} の削除に失敗した（{detail}）"
    _note(repo_root, entry_id, now=now, note=note)
