"""Bounded Git subprocesses for PR-base integration."""

import os
import subprocess
from pathlib import Path

from .base_error import BaseIntegrationError, require


def git(workspace, *args, allow_failure=False):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env.update(GIT_TERMINAL_PROMPT="0", GIT_MERGE_AUTOEDIT="no")
    try:
        result = subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgSign=false",
             "-c", "rerere.enabled=false", *args], cwd=workspace, env=env,
            capture_output=True, timeout=60, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BaseIntegrationError("BASE_GIT_UNAVAILABLE") from exc
    require(allow_failure or result.returncode == 0,
            "BASE_GIT_FAILED: " + args[0])
    return result


def output(workspace, *args):
    return os.fsdecode(git(workspace, *args).stdout).strip()


def git_path(workspace, name):
    value = Path(output(workspace, "rev-parse", "--git-path", name))
    return value if value.is_absolute() else Path(workspace) / value


def merge_head(workspace):
    path = git_path(workspace, "MERGE_HEAD")
    require(not path.is_symlink(), "BASE_MERGE_HEAD_SYMLINK")
    return path.read_text().strip() if path.exists() else None


def foreign_operation(workspace):
    return any(git_path(workspace, name).exists() for name in (
        "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "sequencer"))


def process_alive(pid, token):
    if type(pid) is not int or not isinstance(token, str):
        return False
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return fields[0] != "Z" and fields[19] == token
    except (OSError, IndexError):
        return False


def process_token():
    return Path(f"/proc/{os.getpid()}/stat").read_text().rsplit(")", 1)[1].split()[19]
