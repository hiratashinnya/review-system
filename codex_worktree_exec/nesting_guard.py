"""Codex の中からの再帰起動を拒否する（Issue #538 D6 の二枚目。一枚目は `.codex/rules/default.rules`）。"""

from __future__ import annotations

from typing import Mapping

from .errors import CodexExecError

# ラッパーが起動する Codex に自分で渡す印。Codex の子コマンドへ継承される。
NESTING_MARKER = "CODEX_WORKTREE_EXEC_ACTIVE"
# Codex が sandbox 内のコマンドに設定する環境変数。どれが実際に付くかは実起動検証項目。
CODEX_SANDBOX_MARKERS = ("CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED")


def refuse_nested_launch(environ: Mapping[str, str]) -> None:
    """Codex の内側で動いている印が1つでもあれば `CODEX_EXEC_NESTED` で止める。"""
    found = [
        name for name in (NESTING_MARKER, *CODEX_SANDBOX_MARKERS) if environ.get(name)
    ]
    if found:
        raise CodexExecError("CODEX_EXEC_NESTED", ",".join(found))
