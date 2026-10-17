"""Dispatch 自身の handoff による完了判定。"""

from pathlib import Path
import re

HANDOFF_DIR_REL = "tmp/_handoff"


def own_handoff_pattern(agent_type: str, issue: int) -> re.Pattern:
    """所有ロール・Issue 番号・suffix 境界が一致する名前だけを受理する。"""
    return re.compile(
        rf"^{re.escape(agent_type)}--issue-{int(issue)}(-[A-Za-z0-9._-]*)?\.yaml$"
    )


def discover_handoff(repo_root: Path, worktree_path: str, *, agent_type: str, issue) -> tuple:
    """回収対象を一意に決め、欠落と観測不能を別の理由で返す。"""
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        return None, "unidentifiable"
    directory = Path(repo_root) / worktree_path / HANDOFF_DIR_REL
    if directory.is_symlink():
        return None, "unreadable"
    if not directory.exists():
        return None, "empty"
    if not directory.is_dir():
        return None, "unreadable"
    try:
        children = sorted(child for child in directory.iterdir() if not child.is_dir())
    except OSError:
        return None, "unreadable"
    pattern = own_handoff_pattern(agent_type, issue)
    mine = [child for child in children if pattern.fullmatch(child.name)]
    if not mine:
        return None, "empty"
    if len(mine) > 1:
        return None, "ambiguous"
    return f"{HANDOFF_DIR_REL}/{mine[0].name}", "unique"
