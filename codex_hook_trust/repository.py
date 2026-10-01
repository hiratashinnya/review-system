"""Resolve repository paths used for Codex trust lookups."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _first_worktree_path(output: str) -> Path | None:
    """Read the main worktree path from git's first porcelain entry."""
    first_entry = next((entry for entry in output.split("\n\n") if entry.strip()), "")
    lines = first_entry.splitlines()
    if not lines or "bare" in lines:
        return None
    worktree_line = next((line for line in lines if line.startswith("worktree ")), "")
    path = worktree_line.removeprefix("worktree ").strip()
    return Path(path) if path else None


def resolve_main_checkout(repo: Path) -> Path:
    """Resolve the main worktree; keep the input path on Git failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
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
