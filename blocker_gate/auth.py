"""GitHub read-only API 用の共通認証解決。"""

from __future__ import annotations

import os
import subprocess
from typing import Callable, Mapping


GH_AUTH_TIMEOUT_SECONDS = 3.0
_GH_AUTH_COMMAND = ("gh", "auth", "token", "--hostname", "github.com")

# GitHub API が返す全応答（成功・失敗を問わない）に付く request 追跡 header。
# api.github.com まで実際に届いた応答かどうかの provenance 証拠として使う。
GITHUB_PROVENANCE_HEADER = "x-github-request-id"


def _header_present(headers: Mapping[str, str], name: str) -> bool:
    return any(
        isinstance(key, str) and key.lower() == name and str(value).strip()
        for key, value in headers.items()
    )


def github_api_failure_reason(
    status: int, headers: Mapping[str, str]
) -> str | None:
    """GitHub API の共通 auth/availability/reachability failure を reason へ分類する。

    Issue #345［B］: 401/403 を一律 ``API_PERMISSION`` に写像すると、
    **GitHub まで届いていない応答**（手前の proxy が生成した拒否）まで
    「権限がない」と表示してしまう。実測（Claude Code on the web）では
    Anthropic 側の GitHub 専用 proxy が Issue 系 endpoint を endpoint 単位で
    遮断し、``documentation_url`` が ``docs.anthropic.com`` の 403 body を
    返す——GitHub がその応答を生成することはない。token を替えても結果は
    変わらないので、これは認証・権限の問題ではなく到達性の問題である。

    切り分けは vendor 固有の文言ではなく **provenance** で行う：GitHub API の
    応答には成功・失敗を問わず ``X-GitHub-Request-Id`` が付く。これを欠く
    401/403 は「GitHub が下した認可判断」ではありえないので ``API_UNREACHABLE``
    とする。逆に header を伴う 401/403 は従来どおり ``API_PERMISSION`` のまま
    残す（真の権限エラー）。

    どちらへ誤っても fail-close は緩まない：両者とも ERROR / exit 20 であり、
    ``API_UNREACHABLE`` が追加で引く snapshot fallback（``issue_start.gate``）も
    実グラフを上限付き staleness 下で評価するので「読めないときに通す」経路は
    生まれない。rate limit 由来の 403 は ``X-RateLimit-Remaining`` 自体が
    GitHub provenance なので、先に ``API_UNAVAILABLE`` として確定させる。
    """
    if status == 403 and any(
        isinstance(name, str)
        and name.lower() == "x-ratelimit-remaining"
        and str(value).strip() == "0"
        for name, value in headers.items()
    ):
        return "API_UNAVAILABLE"
    if status in {401, 403}:
        if not _header_present(headers, GITHUB_PROVENANCE_HEADER):
            return "API_UNREACHABLE"
        return "API_PERMISSION"
    if status == 429 or status >= 500:
        return "API_UNAVAILABLE"
    return None


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
