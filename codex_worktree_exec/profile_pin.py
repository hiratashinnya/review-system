"""worktree の permission profile が `origin/main` の版と同一であることを確かめる（Issue #538 D1）。

Codex は worktree の project-local `.codex/config.toml` から profile を読む。呼び出し側が
その場で書き換えた profile で起動しないよう、blob の OID を `origin/main` と突き合わせる。
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import Callable

from .errors import CodexExecError

CONFIG_RELPATH = ".codex/config.toml"
BASE_REF = "origin/main"
Runner = Callable[..., subprocess.CompletedProcess]


def _git_oid(worktree: Path, args: list[str], runner: Runner) -> str | None:
    completed = runner(
        ["git", "-C", str(worktree), *args],
        capture_output=True, text=True, shell=False, check=False,
    )
    oid = completed.stdout.strip() if completed.returncode == 0 else ""
    return oid or None


def _defines_profile(config: Path, role: str) -> bool:
    try:
        tables = tomllib.loads(config.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return False
    permissions = tables.get("permissions")
    return isinstance(permissions, dict) and isinstance(permissions.get(role), dict)


def verify_profile_pinned(worktree: Path, role: str, *, runner: Runner = subprocess.run) -> None:
    """差分・欠落・未定義をそれぞれ別の識別子で拒否する。"""
    config = worktree / CONFIG_RELPATH
    if config.is_symlink() or not config.is_file():
        raise CodexExecError("CODEX_EXEC_PROFILE_MISSING", str(config))
    base = _git_oid(
        worktree, ["rev-parse", "--verify", "--quiet", f"{BASE_REF}:{CONFIG_RELPATH}"], runner
    )
    if base is None:
        raise CodexExecError("CODEX_EXEC_PROFILE_BASE_UNRESOLVED", f"{BASE_REF}:{CONFIG_RELPATH}")
    current = _git_oid(worktree, ["hash-object", "--", CONFIG_RELPATH], runner)
    if current is None:
        raise CodexExecError("CODEX_EXEC_GIT_FAILED", f"hash-object {CONFIG_RELPATH}")
    if current != base:
        raise CodexExecError(
            "CODEX_EXEC_PROFILE_DRIFT", f"{CONFIG_RELPATH} {current} != {BASE_REF} {base}"
        )
    if not _defines_profile(config, role):
        raise CodexExecError("CODEX_EXEC_PROFILE_UNDEFINED", f"[permissions.{role}]")
