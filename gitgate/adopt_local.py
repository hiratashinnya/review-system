"""Fail-closed local ref ownership and safe stray-ref reclaim."""
from branch_source.policy import BranchSourceError
from .adopt_git import _run_git
from .adopt_holders import HOLDER_AGENT, HOLDER_LINKED, _branch_holder, _ledger_entry_for_worktree
from .adopt_diagnostics import describe_local_ref_conflict
def _check_local(request, *, workdir, runner, observed):
    # Safety rationale: .ai/rationale/gitgate-adopt.md
    local_ref = f"refs/heads/{request.branch_name}"
    local = _run_git(
        ["git", "rev-parse", "--verify", "--quiet", local_ref],
        cwd=workdir,
        runner=runner,
    )
    if local.returncode == 0:
        local_tip = (local.stdout or "").strip().lower()
        # tip 一致（追加の git 呼び出し不要・段2 で確認済みの `observed` を再利用）を
        # 先に見る——不一致ならこの時点で衝突確定であり、worktree list を呼ぶ意味が無い。
        if local_tip != observed:
            raise BranchSourceError(
                "BRANCH_ADOPT_LOCAL_EXISTS",
                describe_local_ref_conflict(
                    request.branch_name,
                    holder_kind=None,
                    local_tip=local_tip,
                    remote_tip=observed,
                ),
            )
        holder_kind, holder_path = _branch_holder(
            request.branch_name, cwd=workdir, runner=runner
        )
        if holder_kind is not None:
            # 掴んでいる主体を失敗文言に載せて復旧手順へ直結させる（Issue #502）。
            # 台帳参照は best-effort で、引けなくても fail-close の判定は変わらない。
            entry = (
                _ledger_entry_for_worktree(holder_path, cwd=workdir)
                if holder_kind in (HOLDER_AGENT, HOLDER_LINKED)
                else None
            )
            raise BranchSourceError(
                "BRANCH_ADOPT_LOCAL_EXISTS",
                describe_local_ref_conflict(
                    request.branch_name,
                    holder_kind=holder_kind,
                    holder_path=holder_path,
                    entry=entry,
                ),
            )
        deleted = _run_git(
            ["git", "branch", "-D", request.branch_name], cwd=workdir, runner=runner
        )
        if deleted.returncode != 0:
            raise BranchSourceError(
                "BRANCH_ADOPT_LOCAL_EXISTS",
                f"{request.branch_name}（無害な残留 ref と判定したが `git branch -D` に"
                f"失敗した: {(deleted.stderr or '').strip()[:200]}）",
            )
