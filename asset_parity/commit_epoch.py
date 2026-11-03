"""Fail-soft last-commit observation for informational staleness."""

import subprocess
from pathlib import Path


def git_last_commit_epoch(path: Path, root: Path) -> int | None:
    """Unix-epoch seconds of the last commit touching `path`, or None (fail-soft).

    None covers: not a git repo, file untracked/never committed, or git unavailable —
    this is an informational signal, never a hard error.
    """
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    try:
        shallow = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=root, capture_output=True, text=True, timeout=10, check=False,
        )
        if shallow.returncode != 0 or shallow.stdout.strip() != "false":
            return None
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(rel)],
            cwd=root, capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    out = (proc.stdout or "").strip()
    return int(out) if proc.returncode == 0 and out.isdigit() else None


