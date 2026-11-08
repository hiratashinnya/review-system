"""Worktree lifecycle CLI execution and stderr result contracts."""
import sys
from .worktree import (
    collect_worktree, default_repo_root, parse_collect_worktree_args,
    parse_worktree_forget_args, parse_worktree_release_args,
    parse_worktree_sweep_args, sweep_abandoned_running,
    worktree_forget, worktree_release,
)
def run_worktree_verb(verb, args, *, now):
    """`worktree-*` verb を実行し、実施内容を stderr に1行残して 0 を返す。"""
    repo_root = default_repo_root()
    if verb == "worktree-release":
        request = parse_worktree_release_args(args)
        outcome = worktree_release(
            repo_root,
            request.worktree_path,
            entry_id=request.entry_id,
            force_uncollected=request.force_uncollected,
            reason=request.reason,
            now=now(),
        )
        sys.stderr.write(
            f"gitgate: worktree-release {outcome.worktree_path} "
            f"entry={outcome.entry_id or '-'} removed={'yes' if outcome.removed else 'no'} "
            f"status={outcome.status}\n"
        )
        return 0
    if verb == "collect-worktree":
        request = parse_collect_worktree_args(args)
        outcome = collect_worktree(
            repo_root,
            entry_id=request.entry_id,
            worktree_path=request.worktree_path,
            handoff_path=request.handoff_path,
            into=request.into,
            allow_missing_handoff=request.allow_missing_handoff,
            reason=request.reason,
            now=now(),
        )
        sys.stderr.write(
            f"gitgate: collect-worktree {outcome.worktree_path} "
            f"entry={outcome.entry_id or '-'} collected_to={outcome.collected_to or '-'} "
            f"released={'yes' if outcome.released else 'no'}\n"
        )
        return 0
    if verb == "worktree-sweep-abandoned":
        request = parse_worktree_sweep_args(args)
        outcomes = sweep_abandoned_running(
            repo_root,
            now=now(),
            reason=request.reason,
            no_live_dispatch=request.no_live_dispatch,
        )
        released = sum(1 for item in outcomes if item.action == "released")
        for item in outcomes:
            sys.stderr.write(
                f"gitgate: worktree-sweep-abandoned {item.worktree_path} "
                f"entry={item.entry_id} action={item.action}"
                + (f" detail={item.detail}" if item.detail else "")
                + "\n"
            )
        sys.stderr.write(
            f"gitgate: worktree-sweep-abandoned candidates={len(outcomes)} "
            f"released={released}\n"
        )
        return 0
    request = parse_worktree_forget_args(args)
    entry = worktree_forget(
        repo_root, request.entry_id, reason=request.reason, now=now()
    )
    sys.stderr.write(
        f"gitgate: worktree-forget {request.entry_id} status={entry.get('status')} "
        "(worktree は削除していない)\n"
    )
    return 0
