"""Switch to the verified exact OID and bind upstream afterwards."""
from branch_source.policy import BranchSourceError
from .adopt_models import _ALREADY_CHECKED_OUT_MARKERS
from .adopt_git import _run_git, _require_ok
def _checkout(request, *, workdir, runner):
    # 5. checkout（検証済み exact OID を明示。current HEAD を暗黙継承しない）。
    switched = _run_git(
        ["git", "switch", "--create", request.branch_name, request.expected_oid],
        cwd=workdir,
        runner=runner,
    )
    if switched.returncode != 0:
        stderr = (switched.stderr or "").lower()
        if any(marker in stderr for marker in _ALREADY_CHECKED_OUT_MARKERS):
            raise BranchSourceError(
                "BRANCH_ADOPT_ALREADY_CHECKED_OUT",
                f"{request.branch_name}（先行 worktree を `python3 -m gitgate collect-worktree` "
                "で解放してから再実行する）",
            )
        raise BranchSourceError("BRANCH_GIT_ERROR", "switch")

    # 6. upstream 束縛（以後の push/status が origin/<branch> を基準に読める）。
    _require_ok(
        _run_git(
            [
                "git",
                "branch",
                f"--set-upstream-to=origin/{request.branch_name}",
                request.branch_name,
            ],
            cwd=workdir,
            runner=runner,
        ),
        "BRANCH_GIT_ERROR",
        "set-upstream",
    )
