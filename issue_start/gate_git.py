from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Sequence

from .gate_support import IssueStartError, _HTTPS_REMOTE, _REPOSITORY, _SSH_REMOTE, SNAPSHOT_GIT_TIMEOUT_SECONDS



def _run_git(
    argv: Sequence[str],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    try:
        completed = runner(
            list(argv), cwd=str(cwd), text=True, capture_output=True, shell=False
        )
    except OSError as exc:
        raise IssueStartError("ISSUE_START_GIT_ERROR", type(exc).__name__) from exc
    if completed.returncode != 0:
        raise IssueStartError("ISSUE_START_GIT_ERROR", argv[1] if len(argv) > 1 else "git")
    output = completed.stdout
    if not isinstance(output, str) or "\0" in output:
        raise IssueStartError("ISSUE_START_GIT_OUTPUT_INVALID")
    if output.endswith("\n"):
        output = output[:-1]
    if "\n" in output or "\r" in output:
        raise IssueStartError("ISSUE_START_GIT_OUTPUT_INVALID")
    return output


def _canonical_github_repository(remote_url: str) -> str:
    if "\n" in remote_url or "\r" in remote_url:
        raise IssueStartError("ISSUE_START_ORIGIN_INVALID")
    for pattern in (_HTTPS_REMOTE, _SSH_REMOTE):
        match = pattern.fullmatch(remote_url)
        if match:
            repository = f"{match.group(1)}/{match.group(2)}"
            if _REPOSITORY.fullmatch(repository):
                return repository
    raise IssueStartError("ISSUE_START_ORIGIN_INVALID")


def _git_output(
    argv: Sequence[str],
    *,
    cwd: Path | None,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    reason: str,
) -> str:
    """snapshot fallback 用の raw git 実行（複数行 stdout を許す）。"""
    try:
        completed = runner(
            list(argv),
            cwd=None if cwd is None else str(cwd),
            text=True,
            capture_output=True,
            shell=False,
            timeout=SNAPSHOT_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise IssueStartError(reason, type(exc).__name__) from exc
    if completed.returncode != 0 or not isinstance(completed.stdout, str):
        raise IssueStartError(reason, argv[1] if len(argv) > 1 else "git")
    return completed.stdout
