"""gitを用いずworkspaceの通常ファイルとsymlinkを実行前後で比較する。"""

import hashlib
import os
import stat
from pathlib import Path

from .image_source import FILE_FLAGS, held_directory

LIMITATIONS = (
    "before_after_only_transient_changes_not_observable",
    "concurrent_actor_changes_not_attributable_to_agy",
    "git_metadata_and_wrapper_records_excluded",
    "symlink_targets_not_followed_special_files_not_read",
    "metadata_only_changes_and_empty_directories_not_observed",
)


def snapshot(workspace: Path) -> dict[str, str]:
    workspace = workspace.resolve()
    result = {}
    try:
        with held_directory(workspace, "workspace_snapshot_incomplete") as directory_fd:
            _snapshot_directory(directory_fd, Path(), result)
    except OSError as error:
        raise ValueError("workspace_snapshot_incomplete") from error
    return result


def _snapshot_directory(directory_fd: int, relative: Path, result: dict[str, str]) -> None:
    for name in os.listdir(directory_fd):
        path = relative / name
        if name == ".git" or path == Path("tmp/agy"):
            continue
        mode = os.stat(name, dir_fd=directory_fd, follow_symlinks=False).st_mode
        if stat.S_ISLNK(mode):
            result[path.as_posix()] = "symlink:" + os.readlink(name, dir_fd=directory_fd)
        elif stat.S_ISDIR(mode):
            with held_directory(name, "workspace_snapshot_incomplete", dir_fd=directory_fd) as child_fd:
                _snapshot_directory(child_fd, path, result)
        elif stat.S_ISREG(mode):
            result[path.as_posix()] = _regular_digest(directory_fd, name)


def _regular_digest(directory_fd: int, name: str) -> str:
    descriptor = os.open(name, FILE_FLAGS, dir_fd=directory_fd)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("workspace_snapshot_incomplete")
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
        return digest.hexdigest()


def changes(before: dict[str, str], after: dict[str, str]) -> list[dict[str, str]]:
    return [{"path": path, "change": "added" if path not in before else
             "deleted" if path not in after else "modified"}
            for path in sorted(before.keys() | after.keys()) if before.get(path) != after.get(path)]
