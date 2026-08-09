"""GitHub read-only API 用の共通認証解決。"""

from __future__ import annotations

import os
import subprocess
from typing import Callable, Mapping


GH_AUTH_TIMEOUT_SECONDS = 3.0
_GH_AUTH_COMMAND = ("gh", "auth", "token", "--hostname", "github.com")


def resolve_github_token(
    *,
    environ: Mapping[str, str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> str | None:
    """環境変数を優先し、既存 ``gh`` credential へ安全にフォールバックする。

    ``gh`` の不在、未認証、timeout、空/異常応答は匿名 read を許すため ``None``
    に正規化する。credential の値や subprocess の例外詳細は外へ出さない。
    """
    values = os.environ if environ is None else environ
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        value = values.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()

    invoke = subprocess.run if runner is None else runner
    try:
        completed = invoke(
            list(_GH_AUTH_COMMAND),
            text=True,
            capture_output=True,
            shell=False,
            timeout=GH_AUTH_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0 or not isinstance(completed.stdout, str):
        return None
    token = completed.stdout.strip()
    return token or None
