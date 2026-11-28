"""Reject uncommitted tracked changes only for the read-only finding triager."""

import subprocess


def require_clean_tracked(worktree):
    """Reject staged and unstaged modifications to tracked files."""
    try:
        subprocess.run(["git", "-C", str(worktree), "diff", "--quiet", "HEAD", "--"],
                       check=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        raise ValueError("triager worktree has uncommitted tracked changes or git diff failed") from error
