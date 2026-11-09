"""Verify an exact default-branch OID from a fresh origin fetch."""
from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Callable
from .source_git import _run_git
from .validation import BranchSourceError, NewBranchRequest, _validate_oid


def verify_default_source(request: NewBranchRequest, default_branch: str, *,
                          cwd: Path, runner: Callable[..., subprocess.CompletedProcess[str]]) -> None:
    local_ref = "refs/review-system/branch-source/default"
    refspec = f"+refs/heads/{default_branch}:{local_ref}"
    _run_git(["git", "fetch", "--force", "--no-tags", "origin", refspec],
             cwd=cwd, runner=runner)
    observed = _validate_oid(
        _run_git(["git", "rev-parse", "--verify", f"{local_ref}^{{commit}}"],
                 cwd=cwd, runner=runner),
        "BRANCH_REMOTE_OID_INVALID",
    )
    if observed != request.base_oid:
        raise BranchSourceError("BRANCH_BASE_OID_MISMATCH")
