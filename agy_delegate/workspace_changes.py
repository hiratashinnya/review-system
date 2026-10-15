"""gitを用いずworkspaceの通常ファイルとsymlinkを実行前後で比較する。"""

import hashlib
import os
from pathlib import Path

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
    def on_error(error):
        raise ValueError("workspace_snapshot_incomplete") from error
    for directory, names, files in os.walk(workspace, followlinks=False, onerror=on_error):
        parent = Path(directory)
        names[:] = [name for name in names if name != ".git" and
                    parent / name != workspace / "tmp" / "agy"]
        for name in [name for name in files if name != ".git"] + [
                name for name in names if (parent / name).is_symlink()]:
            path = parent / name
            key = path.relative_to(workspace).as_posix()
            try:
                if path.is_symlink():
                    result[key] = "symlink:" + os.readlink(path)
                elif path.is_file():
                    digest = hashlib.sha256()
                    with path.open("rb") as stream:
                        for block in iter(lambda: stream.read(1024 * 1024), b""):
                            digest.update(block)
                    result[key] = digest.hexdigest()
            except OSError as error:
                raise ValueError("workspace_snapshot_incomplete") from error
    return result


def changes(before: dict[str, str], after: dict[str, str]) -> list[dict[str, str]]:
    return [{"path": path, "change": "added" if path not in before else
             "deleted" if path not in after else "modified"}
            for path in sorted(before.keys() | after.keys()) if before.get(path) != after.get(path)]
