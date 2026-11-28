"""Read Git metadata and identify the checkout's GitHub repository."""

import os
import subprocess

from branch_source.source_git import _remote_repository
from branch_source.validation import BranchSourceError


def read_git(repo, *args):
    outcome = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repo), *args],
        check=False, capture_output=True, timeout=30,
    )
    if outcome.returncode:
        raise ValueError(f"git {args[0]} が失敗しました")
    return os.fsdecode(outcome.stdout).removesuffix("\n")


def verify_repository(root, repository):
    try:
        origin = _remote_repository(read_git(root, "remote", "get-url", "origin"))
    except (ValueError, BranchSourceError) as exc:
        raise ValueError("ローカルの origin が対象 GitHub リポジトリか確認できません") from exc
    if origin.lower() != repository.lower():
        raise ValueError("ローカルの origin と --repository が一致しません")
