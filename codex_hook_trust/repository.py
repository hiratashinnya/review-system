"""Resolve repository paths used for Codex trust lookups."""

from __future__ import annotations

import subprocess
from pathlib import Path


def resolve_main_checkout(repo: Path) -> Path:
    """Resolve shared trust keys; keep the input path on Git failure to preserve behavior."""
    try:
        result = subprocess.run(
            [
                "git", "-C", str(repo), "rev-parse", "--path-format=absolute",
                "--git-common-dir",
            ],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
            stdin=subprocess.DEVNULL,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return repo

    if result.returncode != 0 or not result.stdout.strip():
        return repo
    try:
        common_dir = Path(result.stdout.strip()).resolve(strict=True)
    except (OSError, RuntimeError):
        return repo
    checkout = common_dir.parent
    return checkout if checkout.is_dir() else repo
