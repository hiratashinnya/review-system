"""Temporary Git repository fixtures for Codex hook trust tests."""

import json
import os
from pathlib import Path
import shutil
import subprocess


def write_hooks(repo: Path, count: int) -> None:
    config = repo / ".codex" / "hooks.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    handlers = [{"command": f"handler-{index}"} for index in range(count)]
    config.write_text(
        json.dumps({"hooks": {"SessionStart": [{"hooks": handlers}]}}),
        encoding="utf-8",
    )


def run_git(repo: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise AssertionError(result.stderr)


def make_project_repository(directory: Path, source_repo: Path) -> Path:
    """Copy the current project's hook config into an isolated Git repo."""
    repo = directory / "project"
    repo.mkdir()
    run_git(repo, "init")
    source = source_repo / ".codex" / "hooks.json"
    target = repo / ".codex" / "hooks.json"
    target.parent.mkdir(parents=True)
    shutil.copyfile(source, target)
    return repo


def init_repository(repo: Path, hook_count: int) -> None:
    repo.mkdir(parents=True)
    run_git(repo, "init")
    run_git(repo, "config", "user.name", "Trust Test")
    run_git(repo, "config", "user.email", "trust-test@example.invalid")
    write_hooks(repo, hook_count)
    run_git(repo, "add", ".codex/hooks.json")
    run_git(repo, "commit", "-m", "Add hooks configuration")


def make_repository_pair(
    directory: Path,
    hook_count: int,
    *,
    main_name: str = "main",
    worktree_name: str = "linked-worktree",
) -> tuple[Path, Path]:
    main = directory / main_name
    worktree = directory / worktree_name
    init_repository(main, hook_count)
    run_git(main, "worktree", "add", "-b", "linked", str(worktree), "HEAD")
    return main, worktree


def make_separate_git_dir_pair(directory: Path, hook_count: int) -> tuple[Path, Path]:
    main = directory / "separate-main"
    git_dir = directory / "separate-git-dir"
    worktree = directory / "separate-linked-worktree"
    main.mkdir()
    run_git(directory, "init", "--separate-git-dir", str(git_dir), str(main))
    run_git(main, "config", "user.name", "Trust Test")
    run_git(main, "config", "user.email", "trust-test@example.invalid")
    write_hooks(main, hook_count)
    run_git(main, "add", ".codex/hooks.json")
    run_git(main, "commit", "-m", "Add hooks configuration")
    run_git(main, "worktree", "add", "-b", "separate-linked", str(worktree), "HEAD")
    return main, worktree


def init_bare_repository(repo: Path, hook_count: int) -> None:
    run_git(repo.parent, "init", "--bare", str(repo))
    write_hooks(repo, hook_count)


def read_trace(trace: Path) -> dict:
    records = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
    if len(records) != 1:
        raise AssertionError(f"expected one app-server trace entry, got {len(records)}")
    return records[0]


def make_failing_git_path(directory: Path) -> str:
    bin_dir = directory / "failing-git-bin"
    bin_dir.mkdir(exist_ok=True)
    git = bin_dir / "git"
    git.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    git.chmod(0o755)
    return str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
