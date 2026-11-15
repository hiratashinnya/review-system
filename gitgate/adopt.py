"""Public adopt-branch facade; see .ai/rationale/gitgate-adopt.md."""
from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Callable
from blocker_gate.auth import resolve_github_token
from branch_source.policy import (
    BranchApi, BranchSourceError, GitHubBranchClient,
    validate_branch_ref, validate_repository,
)
from .adopt_models import (
    ADOPT_POLICY_VERSION, FETCH_TIMEOUT_SECONDS, _ADOPT_OID, _POSITIVE_INT,
    _ALREADY_CHECKED_OUT_MARKERS, AdoptBranchRequest, AdoptBranchResult,
)
from .adopt_parse import parse_adopt_branch_args
from .adopt_git import _run_git, _fetch_env, _require_ok
from .adopt_holders import (
    HOLDER_PRIMARY, HOLDER_AGENT, HOLDER_LINKED, HOLDER_UNKNOWN,
    _AGENT_WORKTREE_SUFFIX, _branch_holder, _ledger_entry_for_worktree,
)
from .adopt_diagnostics import describe_local_ref_conflict, _holder_detail, _FOLLOWUP_AUTHOR_NOTE
from .adopt_pr import _string_at, _verify_pull_request
from .adopt_remote import _verify_remote
from .adopt_local import _check_local
from .adopt_checkout import _checkout

def adopt_branch(
    request: AdoptBranchRequest,
    *,
    cwd: Path | None = None,
    api: BranchApi | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> AdoptBranchResult:
    """Adopt only after remote, optional PR, and local safety gates."""
    workdir = Path.cwd() if cwd is None else cwd
    observed = _verify_remote(request, workdir=workdir, runner=runner)
    if request.pr is not None:
        client = api or GitHubBranchClient(resolve_github_token())
        _verify_pull_request(request, api=client)
    _check_local(request, workdir=workdir, runner=runner, observed=observed)
    _checkout(request, workdir=workdir, runner=runner)
    return AdoptBranchResult(
        branch_name=request.branch_name,
        repository=request.repository,
        expected_oid=request.expected_oid,
        pr=request.pr,
    )
