"""Classify checked-out holders; ledger lookups are best-effort diagnostics."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path
from typing import Callable
from .adopt_git import _run_git
HOLDER_PRIMARY = "primary"
HOLDER_AGENT = "agent-worktree"
HOLDER_LINKED = "linked-worktree"
HOLDER_UNKNOWN = "unknown"

# `.claude/worktrees/agent-<id>` の形（`issue_start.worktree_ledger.WORKTREE_PATH_RE` と同じ
# 形状だが、ここでは絶対パスの末尾に対する部分一致で使うので独立に持つ）。
_AGENT_WORKTREE_SUFFIX = re.compile(r"\.claude/worktrees/agent-[A-Za-z0-9_-]{1,64}$")


def _branch_holder(
    branch_name: str, *, cwd: Path, runner: Callable[..., subprocess.CompletedProcess]
) -> tuple[str | None, str | None]:
    """``branch_name`` を checked out している worktree を種別つきで返す（Issue #502）。

    返り値は ``(種別, パス)``。種別は :data:`HOLDER_PRIMARY`（porcelain の先頭レコード＝
    メインワークツリー）／:data:`HOLDER_AGENT`（``.claude/worktrees/agent-<id>``）／
    :data:`HOLDER_LINKED`（その他の linked worktree）／:data:`HOLDER_UNKNOWN`
    （``git worktree list`` が失敗＝判定不能）／``None``（どこも掴んでいない）。

    到達不能・異常終了は「わからない」を「安全（checked out されていない）」に潰さず、
    :data:`HOLDER_UNKNOWN` にする——fail-close。stray ref の自動回収は「明確に無害と確認
    できたときだけ」行う契約なので、判定不能を無害側に倒さない。
    """
    completed = _run_git(
        ["git", "worktree", "list", "--porcelain"], cwd=cwd, runner=runner
    )
    if completed.returncode != 0:
        return HOLDER_UNKNOWN, None
    target = f"branch refs/heads/{branch_name}"
    index = -1
    path: str | None = None
    for line in (completed.stdout or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("worktree "):
            index += 1
            path = stripped[len("worktree "):].strip()
            continue
        if stripped != target:
            continue
        if index == 0:
            return HOLDER_PRIMARY, path
        if path and _AGENT_WORKTREE_SUFFIX.search(path.replace("\\", "/")):
            return HOLDER_AGENT, path
        return HOLDER_LINKED, path
    return None, None


def _ledger_entry_for_worktree(holder_path: str | None, *, cwd: Path):
    """掴んでいる worktree に対応する台帳エントリ（best-effort・引けなければ ``None``）。

    診断文言を厚くするためだけの参照であり、**判定（fail-close）には一切使わない**。
    台帳が読めない・パスが main worktree の外・そもそも台帳が無い、のいずれでも黙って
    ``None`` を返す（ここで例外を外へ出すと、診断のために adopt が別の理由で落ちる）。
    """
    if not holder_path:
        return None
    try:
        from issue_start.worktree_ledger import main_worktree_root

        from .worktree import find_entry

        root = Path(main_worktree_root(cwd))
        relative = Path(holder_path).resolve().relative_to(root.resolve()).as_posix()
        return find_entry(root, worktree_path=relative)
    except Exception:  # noqa: BLE001 - 診断が引けないことで adopt を落とさない
        return None
