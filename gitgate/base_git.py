"""PR base 取り込みが使う、引数固定の Git subprocess と Git 状態の読取。"""

import os
import subprocess
from pathlib import Path

from .base_error import BaseIntegrationError, require


def git(workspace, *args, allow_failure=False):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env.update(GIT_TERMINAL_PROMPT="0", GIT_MERGE_AUTOEDIT="no")
    try:
        result = subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgSign=false",
             "-c", "rerere.enabled=false", *args], cwd=workspace, env=env,
            capture_output=True, timeout=60, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BaseIntegrationError("BASE_GIT_UNAVAILABLE") from exc
    require(allow_failure or result.returncode == 0,
            "BASE_GIT_FAILED: " + args[0])
    return result


def output(workspace, *args):
    return os.fsdecode(git(workspace, *args).stdout).strip()


def paths(workspace, *args):
    raw = git(workspace, *args).stdout
    return sorted({os.fsdecode(item) for item in raw.split(b"\0") if item})


def git_path(workspace, name):
    value = Path(output(workspace, "rev-parse", "--git-path", name))
    return value if value.is_absolute() else Path(workspace) / value


def merge_head(workspace):
    path = git_path(workspace, "MERGE_HEAD")
    return path.read_text().strip() if path.exists() else None


def foreign_operation(workspace):
    return any(git_path(workspace, name).exists() for name in (
        "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "sequencer"))


def unmerged_paths(workspace):
    return paths(workspace, "diff", "--name-only", "--diff-filter=U", "-z")


def leftover_changes(workspace):
    """index に載っていない tracked 変更と、ignore されていない新規ファイル。"""
    return sorted(paths(workspace, "diff", "--name-only", "--no-renames", "-z")
                  + paths(workspace, "ls-files", "--others", "--exclude-standard", "-z"))


def is_clean(workspace):
    return not git(workspace, "status", "--porcelain=v1", "-z",
                   "--untracked-files=all").stdout
