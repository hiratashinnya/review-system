"""Fresh remote fetch, exact OID verification, and finite timeout."""
import subprocess
from branch_source.policy import BranchSourceError
from .adopt_models import FETCH_TIMEOUT_SECONDS, _ADOPT_OID
from .adopt_git import _run_git, _fetch_env, _require_ok
def _verify_remote(request, *, workdir, runner):
    # 1. fresh fetch（判定材料をローカルの古い ref に依存させない）。
    # timeout/env は Issue #426・F-426-05 の是正——到達不能/認証待ちの origin で無期限に
    # ハングせず、他の fetch 失敗と同じ fail-close（BRANCH_GIT_ERROR）で有限時間に落ちる。
    try:
        fetch_completed = _run_git(
            ["git", "fetch", "--prune", "origin"],
            cwd=workdir,
            runner=runner,
            timeout=FETCH_TIMEOUT_SECONDS,
            env=_fetch_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise BranchSourceError(
            "BRANCH_GIT_ERROR", f"fetch timed out after {FETCH_TIMEOUT_SECONDS}s"
        ) from exc
    _require_ok(fetch_completed, "BRANCH_GIT_ERROR", "fetch")

    # 2. remote 先端 == 期待 OID。
    remote_ref = f"refs/remotes/origin/{request.branch_name}"
    observed = _require_ok(
        _run_git(
            ["git", "rev-parse", "--verify", f"{remote_ref}^{{commit}}"],
            cwd=workdir,
            runner=runner,
        ),
        "BRANCH_ADOPT_REMOTE_MISSING",
        remote_ref,
    ).lower()
    if not _ADOPT_OID.fullmatch(observed):
        raise BranchSourceError("BRANCH_ADOPT_REMOTE_OID_INVALID", observed)
    if observed != request.expected_oid:
        raise BranchSourceError(
            "BRANCH_ADOPT_OID_MISMATCH",
            f"expected {request.expected_oid}; observed {observed}",
        )
    return observed
