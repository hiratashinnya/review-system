"""Identify the origin repository and run fixed-argv git operations."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path
from typing import Callable, Sequence
from .validation import BranchSourceError, _validate_repository

_HTTPS_REMOTE = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")
_SSH_REMOTE = re.compile(r"^(?:git@github\.com:|ssh://git@github\.com/)([^/]+)/([^/]+?)(?:\.git)?/?$")
def _remote_repository(remote_url: str) -> str:
    for pattern in (_HTTPS_REMOTE, _SSH_REMOTE):
        match = pattern.fullmatch(remote_url.strip())
        if match:
            return _validate_repository(f"{match.group(1)}/{match.group(2)}")
    raise BranchSourceError("BRANCH_REMOTE_AMBIGUOUS")


def _run_git(
    argv: Sequence[str],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    completed = runner(
        list(argv),
        cwd=str(cwd),
        text=True,
        capture_output=True,
        shell=False,
    )
    if completed.returncode != 0:
        raise BranchSourceError("BRANCH_GIT_ERROR", argv[1] if len(argv) > 1 else "git")
    return completed.stdout.strip()
