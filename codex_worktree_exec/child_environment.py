"""Codex の起動・認証とローカル実行に必要な環境だけを子へ渡す。"""

from typing import Mapping

from .nesting_guard import NESTING_MARKER

CODEX_CHILD_ENVIRONMENT_ALLOWLIST = frozenset({
    "PATH", "HOME", "USER", "LOGNAME", "SHELL",
    "LANG", "LC_ALL", "LC_CTYPE", "TERM", "TZ",
    "TMPDIR", "TEMP", "TMP", "CODEX_HOME",
    "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME",
})


def build_codex_child_environment(environ: Mapping[str, str]) -> dict[str, str]:
    """許可名だけを継承し、再帰検知の標識をラッパーが設定する。"""
    return {
        **{name: value for name, value in environ.items()
           if name in CODEX_CHILD_ENVIRONMENT_ALLOWLIST},
        NESTING_MARKER: "1",
    }
