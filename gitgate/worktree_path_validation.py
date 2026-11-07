"""Validate linked worktree paths and symlink-safe resolution."""

from __future__ import annotations
from pathlib import Path
from issue_start.worktree_ledger import WORKTREE_PATH_RE
from .worktree_models import WorktreeError
from .worktree_arg_common import _reject_control_chars

def validate_worktree_path(value: str) -> str:
    """``.claude/worktrees/agent-<id>`` ちょうどの repo-root 相対パスだけを受理する。

    **正規化より先に ``..`` を見る**（正規化で吸収させない）。絶対パス・``~``・
    バックスラッシュ区切り・サブディレクトリ・要素4つ以上はすべて拒否する。
    ここは純粋な構文検査で、FS には一切触れない（symlink 等の検査は
    :func:`resolve_within` が担う）。
    """
    if not isinstance(value, str) or not value:
        raise WorktreeError("WORKTREE_PATH_EMPTY", repr(value))
    _reject_control_chars(value, "worktree path")
    if value.startswith("~"):
        raise WorktreeError("WORKTREE_PATH_NOT_RELATIVE", value)
    if value.startswith("/"):
        raise WorktreeError("WORKTREE_PATH_NOT_RELATIVE", value)
    if len(value) > 1 and value[1] == ":":
        raise WorktreeError("WORKTREE_PATH_NOT_RELATIVE", value)
    if "\\" in value:
        raise WorktreeError("WORKTREE_PATH_SEPARATOR_INVALID", value)
    raw_parts = value.split("/")
    if any(part == ".." for part in raw_parts):
        raise WorktreeError("WORKTREE_PATH_PARENT_REF", value)
    parts = [part for part in raw_parts if part not in ("", ".")]
    normalized = "/".join(parts)
    if len(parts) != 3 or not WORKTREE_PATH_RE.fullmatch(normalized):
        raise WorktreeError("WORKTREE_PATH_SHAPE_INVALID", value)
    return normalized

def resolve_within(root, relative: str, *, error: str = "WORKTREE_PATH_SYMLINK") -> Path:
    """``root`` 配下の ``relative`` を、**構成要素に symlink が無いこと**を確認しながら解決する。

    symlink 越しに repo 外へ誘導された読み書き／削除を許さない。実体解決後もなお ``root``
    配下であることを最後に確かめる（``root`` 自身が symlink 経由で与えられた場合の保険）。
    """
    base = Path(root).resolve()
    current = base
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise WorktreeError(error, str(current))
    try:
        current.resolve().relative_to(base)
    except ValueError:
        raise WorktreeError("WORKTREE_PATH_ESCAPES_ROOT", str(current)) from None
    return current


# --- git 実行 ------------------------------------------------------------------
