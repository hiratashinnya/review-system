"""実行 checkout の同定。ロール・ハーネス・dispatch 台帳には依存しない（Issue #706）。"""

from pathlib import Path

from branch_source.policy import _remote_repository
from .base_error import require
from .base_git import git, output


def bind(cwd):
    """cwd を含む作業ツリーの root・origin repository・current branch を返す。"""
    workspace = Path(output(Path(cwd), "rev-parse", "--show-toplevel")).resolve(strict=True)
    branch = git(workspace, "symbolic-ref", "--quiet", "--short", "HEAD", allow_failure=True)
    require(branch.returncode == 0, "BASE_DETACHED_HEAD")
    return {"workspace": str(workspace),
            "repository": _remote_repository(output(workspace, "remote", "get-url", "origin")),
            "branch": branch.stdout.decode().strip()}
