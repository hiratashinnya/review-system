"""進行中の取り込みと現在の Git 状態の照合、および衝突解消の stage。

衝突ファイル以外の tracked 修正・新規ファイルは、呼び出し元が `gitgate add` で
明示的に stage すれば解消の一部として確定できる（Issue #706）。
"""

from pathlib import Path

from .base_error import require
from .base_git import foreign_operation, git, leftover_changes, merge_head, output, unmerged_paths
from .base_state import load

MARKERS = (b"<<<<<<< ", b">>>>>>> ", b"||||||| ")


def pending_operation(workspace, branch):
    """gitgate が開始した merge がそのまま続いていることを確かめる。"""
    record = load(workspace)
    require(record is not None, "BASE_OPERATION_MISSING")
    require(branch == record["branch"]
            and output(workspace, "rev-parse", "HEAD") == record["original_head"]
            and merge_head(workspace) == record["request"]["base"]
            and not foreign_operation(workspace), "BASE_PENDING_MERGE_STATE_INVALID")
    return record


def with_markers(workspace, names):
    found = []
    for name in names:
        path = Path(workspace) / name
        if path.is_file() and not path.is_symlink() and any(
                line.startswith(MARKERS) for line in path.read_bytes().splitlines()):
            found.append(name)
    return found


def stage_resolution(workspace, record):
    """記録済み衝突ファイルだけを自動 stage し、取り残しがあれば確定しない。"""
    marked = with_markers(workspace, record["conflicts"])
    require(not marked, "BASE_CONFLICT_MARKERS_STOP: " + ", ".join(marked))
    unresolved = unmerged_paths(workspace)
    require(set(unresolved) <= set(record["conflicts"]),
            "BASE_UNRESOLVED_INDEX: " + ", ".join(unresolved))
    if unresolved:
        git(workspace, "add", "--", *unresolved)
    require(not unmerged_paths(workspace), "BASE_UNRESOLVED_INDEX")
    leftover = leftover_changes(workspace)
    require(not leftover, "BASE_UNSTAGED_CHANGES_REMAIN: " + ", ".join(leftover))
