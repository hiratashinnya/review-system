"""Issue #317: fresh-evidence new-branch verification; stable public facade."""
from __future__ import annotations
import subprocess
import urllib.request
from pathlib import Path
from typing import Callable
from blocker_gate.auth import resolve_github_token
from .arguments import parse_new_branch_args
from .github_client import API_VERSION, GitHubBranchClient
from .model import BranchApi, BranchSourceResult, POLICY_VERSION
from .source_default import verify_default_source
from .source_git import _HTTPS_REMOTE, _SSH_REMOTE, _remote_repository, _run_git
from .source_pr import _nested_string, _pull_head_oid
from .source_stacked import verify_stacked_source
from .validation import (BranchSourceError, NewBranchRequest, _validate_branch,
                         _validate_oid, _validate_repository)


def validate_repository(value: str) -> str:
    """Validate and return OWNER/REPO."""
    return _validate_repository(value)


def validate_branch_ref(value: str, reason: str) -> str:
    """Validate and return a safe git branch name."""
    return _validate_branch(value, reason)


def verify_branch_source(
    request: NewBranchRequest, *, cwd: Path | None = None,
    api: BranchApi | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> BranchSourceResult:
    """Validate fresh API/git evidence without creating a local branch."""
    workdir = Path.cwd() if cwd is None else cwd
    remote_url = _run_git(["git", "remote", "get-url", "origin"],
                          cwd=workdir, runner=runner)
    if _remote_repository(remote_url).lower() != request.repository.lower():
        raise BranchSourceError("BRANCH_REPOSITORY_MISMATCH")
    client = api or GitHubBranchClient(resolve_github_token())
    repository_data = client.repository(request.repository)
    full_name = _nested_string(repository_data, "full_name")
    default_branch = _validate_branch(
        _nested_string(repository_data, "default_branch"), "BRANCH_DEFAULT_REF_INVALID"
    )
    if full_name.lower() != request.repository.lower():
        raise BranchSourceError("BRANCH_REPOSITORY_MISMATCH")
    if default_branch != request.base_ref:
        raise BranchSourceError("BRANCH_DEFAULT_REF_MISMATCH")
    if request.base_pr is None:
        verify_default_source(request, default_branch, cwd=workdir, runner=runner)
        source_kind = "default-branch"
    else:
        verify_stacked_source(request, api=client, cwd=workdir, runner=runner)
        source_kind = "same-repository-open-pr"
    return BranchSourceResult(
        repository=request.repository, default_branch=default_branch,
        source_oid=request.base_oid, source_kind=source_kind, base_pr=request.base_pr,
    )


def create_branch(
    request: NewBranchRequest, *, cwd: Path | None = None,
    api: BranchApi | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> BranchSourceResult:
    """Create a branch at the verified exact OID."""
    workdir = Path.cwd() if cwd is None else cwd
    result = verify_branch_source(request, cwd=workdir, api=api, runner=runner)
    _run_git(["git", "switch", "-c", request.branch_name, result.source_oid],
             cwd=workdir, runner=runner)
    return result
