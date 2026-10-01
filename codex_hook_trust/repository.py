"""Resolve repository paths used for Codex trust lookups."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _first_worktree_path(output: bytes) -> Path | None:
    """Read the main worktree path from git's first NUL-separated entry."""
    first_entry = next((entry for entry in output.split(b"\0\0") if entry), b"")
    fields = first_entry.split(b"\0")
    if not fields or b"bare" in fields:
        return None
    prefix = b"worktree "
    path = next(
        (field[len(prefix):] for field in fields if field.startswith(prefix)), b"",
    )
    return Path(os.fsdecode(path)) if path else None


def resolve_main_checkout(repo: Path) -> Path:
    """Resolve the main worktree; keep the input path on Git failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "worktree", "list", "--porcelain", "-z"],
            check=False,
            capture_output=True,
            text=False,
            shell=False,
            stdin=subprocess.DEVNULL,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return repo

    if result.returncode != 0:
        return repo

    worktree_path = _first_worktree_path(result.stdout)
    if worktree_path is None:
        return repo
    try:
        checkout = worktree_path.resolve(strict=True)
    except (OSError, RuntimeError):
        return repo
    if not checkout.is_dir() or not (checkout / ".git").exists():
        return repo
    return checkout
