"""Codex がこのリポジトリを trust 済みであることを起動前に確かめる（Issue #538 要設計2）。

未 trust だと project-local の profile が読まれない。Codex 自身も未 trust では
`default_permissions` の解決に失敗して止まるが、理由を識別子で返すため先に確かめる。
trust の記録キーは main checkout の絶対パスで、その特定は `codex_hook_trust` の関数を再利用する。
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Mapping

from codex_hook_trust.repository import resolve_main_checkout

from .errors import CodexExecError

TRUSTED = "trusted"


def codex_home(environ: Mapping[str, str]) -> Path:
    """Codex と同じ規則で設定ディレクトリを決める（`CODEX_HOME`、無ければ `~/.codex`）。"""
    configured = environ.get("CODEX_HOME")
    return Path(configured) if configured else Path.home() / ".codex"


def _trust_level(config: Path, project: Path) -> object:
    try:
        tables = tomllib.loads(config.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise CodexExecError("CODEX_EXEC_TRUST_UNRESOLVED", f"{config}: {error}") from None
    projects = tables.get("projects")
    entry = projects.get(str(project)) if isinstance(projects, dict) else None
    return entry.get("trust_level") if isinstance(entry, dict) else None


def verify_project_trusted(worktree: Path, home: Path) -> None:
    """main checkout を特定できなければ判定不能、trust_level が trusted 以外なら未 trust で止める。"""
    resolution = resolve_main_checkout(worktree)
    if not resolution.identified:
        raise CodexExecError("CODEX_EXEC_TRUST_UNRESOLVED", f"main checkout of {worktree}")
    level = _trust_level(home / "config.toml", resolution.path)
    if level != TRUSTED:
        raise CodexExecError(
            "CODEX_EXEC_PROJECT_UNTRUSTED", f"{resolution.path}: trust_level={level!r}"
        )
