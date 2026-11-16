"""Bind a stacked branch to the exact PR head before and after fetch."""
from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Callable
from .model import BranchApi
from .source_git import _run_git
from .source_pr import _pull_head_oid
from .validation import BranchSourceError, NewBranchRequest, _validate_oid


def verify_stacked_source(request: NewBranchRequest, *, api: BranchApi,
                          cwd: Path, runner: Callable[..., subprocess.CompletedProcess[str]]) -> None:
    assert request.base_pr is not None
    pull_before = api.pull_request(request.repository, request.base_pr)
    head_oid = _pull_head_oid(pull_before, request.repository)
    if head_oid != request.base_oid:
        raise BranchSourceError("BRANCH_BASE_OID_MISMATCH")
    local_pr_ref = f"refs/remotes/origin/review-system-pr/{request.base_pr}"
    refspec = f"+refs/pull/{request.base_pr}/head:{local_pr_ref}"
    _run_git(["git", "fetch", "--force", "--no-tags", "origin", refspec],
             cwd=cwd, runner=runner)
    pull_after = api.pull_request(request.repository, request.base_pr)
    rebound_oid = _pull_head_oid(pull_after, request.repository)
    if rebound_oid != head_oid:
        raise BranchSourceError("BRANCH_BASE_PR_CHANGED")
    observed = _validate_oid(
        _run_git(["git", "rev-parse", "--verify", f"{local_pr_ref}^{{commit}}"],
                 cwd=cwd, runner=runner),
        "BRANCH_REMOTE_OID_INVALID",
    )
    if observed != rebound_oid:
        raise BranchSourceError("BRANCH_PR_HEAD_MISMATCH")
