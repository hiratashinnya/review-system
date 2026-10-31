"""進行中の取り込みを中止する。`merge --abort` が消す編集は先に退避する。

防ぐ失敗：中止で衝突解消の編集が黙って失われること、および gitgate が開始して
いない merge を取り違えて中止すること。
"""

import os
import tarfile
import time
from pathlib import Path

from .base_error import BaseIntegrationError, require
from .base_git import git, git_path, merge_head, output, paths
from .base_resolution import pending_operation
from .base_state import clear, load


def recovery_dir(workspace):
    common = Path(output(workspace, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    directory = common / "gitgate-base-recovery"
    directory.mkdir(mode=0o700, exist_ok=True)
    return directory


def save_recovery(workspace):
    """HEAD から変わった tracked・新規ファイルと merge 状態を tar に保存して返す。"""
    names = paths(workspace, "diff", "--name-only", "--no-renames", "-z", "HEAD") + paths(
        workspace, "ls-files", "--others", "--exclude-standard", "-z")
    target = recovery_dir(workspace) / f"{time.strftime('%Y%m%dT%H%M%S')}-{os.getpid()}.tar"
    with tarfile.open(target, "x") as archive:
        for name in names:
            path = Path(workspace) / name
            if path.exists() or path.is_symlink():
                archive.add(path, arcname="worktree/" + name, recursive=False)
        for name in ("MERGE_HEAD", "MERGE_MSG"):
            if git_path(workspace, name).is_file():
                archive.add(git_path(workspace, name), arcname="git/" + name)
    return str(target)


def abort(binding):
    workspace = binding["workspace"]
    record = load(workspace)
    if record is not None and merge_head(workspace) is None:
        clear(workspace)
        return {"status": "cleared", "head": output(workspace, "rev-parse", "HEAD")}
    record = pending_operation(workspace, binding["branch"])
    recovery = save_recovery(workspace)
    result = git(workspace, "merge", "--abort", allow_failure=True)
    if result.returncode != 0:
        raise BaseIntegrationError("BASE_ABORT_FAILED: recovery=" + recovery)
    require(output(workspace, "rev-parse", "HEAD") == record["original_head"]
            and merge_head(workspace) is None, "BASE_ABORT_RESULT_INVALID: recovery=" + recovery)
    clear(workspace)
    return {"status": "aborted", "recovery": recovery}
