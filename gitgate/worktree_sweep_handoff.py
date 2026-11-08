"""Find only the owning agent's unambiguous handoff (Issue #423)."""

from .worktree_models import WorktreeError
from .worktree_path_validation import resolve_within
from .worktree_handoff_paths import HANDOFF_DIR_PARTS, HANDOFF_FILENAME_RE
from pathlib import Path

def _own_handoff(repo_root, entry) -> tuple:
    """エントリの worktree から**その dispatch 自身の** handoff を1つに決める。

    返り値は ``(相対パス | None, how)``。``how`` は ``unique`` / ``empty`` / ``ambiguous`` /
    ``unreadable`` / ``unidentifiable``。判定規則は
    ``issue_start/subagent_hooks.py::_discover_handoff`` と同一（``<agent_type>--issue-<N>``
    に一致するものだけを自分の成果物とみなす）で、委譲先エージェントの handoff を自分のものと
    取り違えない（Issue #423 の実測）。**規則は同一だが実装は共有しない**——フック側は
    「``gitgate`` を import せず起動するだけ」という境界を保つために独自に組み立てており、
    こちらは ``gitgate`` 側の正本である :data:`HANDOFF_FILENAME_RE` をそのまま使う。
    """
    agent_type = entry.get("agent_type")
    issue = entry.get("issue")
    relative = entry.get("worktree_path")
    if not isinstance(agent_type, str) or not agent_type:
        return None, "unidentifiable"
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        return None, "unidentifiable"
    try:
        worktree_dir = resolve_within(repo_root, relative)
    except WorktreeError:
        return None, "unreadable"
    directory = worktree_dir / HANDOFF_DIR_PARTS[0] / HANDOFF_DIR_PARTS[1]
    if directory.is_symlink():
        return None, "unreadable"
    if not directory.exists():
        return None, "empty"
    if not directory.is_dir():
        return None, "unreadable"
    try:
        names = sorted(child.name for child in directory.iterdir() if not child.is_dir())
    except OSError:
        return None, "unreadable"
    mine = []
    for name in names:
        match = HANDOFF_FILENAME_RE.fullmatch(name)
        if match is None:
            continue
        if match.group("agent") != agent_type or int(match.group("issue")) != issue:
            continue
        mine.append(name)
    if not mine:
        return None, "empty"
    if len(mine) > 1:
        return None, "ambiguous"
    return f"{'/'.join(HANDOFF_DIR_PARTS)}/{mine[0]}", "unique"
