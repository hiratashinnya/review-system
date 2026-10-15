"""Fetch issue and pull request data with the GitHub CLI."""

from __future__ import annotations
import json
import subprocess
from collections.abc import Callable
from .collect_load import CollectionError, load_issues, load_pulls
from .model import IssueRecord, PullRequestRecord

DEFAULT_FETCH_LIMIT = 2000
ISSUE_FIELDS = "number,createdAt,closedAt,body"
PULL_FIELDS = "number,mergedAt"


def _run_gh(args: list[str]) -> object:
    try:
        completed = subprocess.run(
            ["gh", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:  # gh 未導入の環境
        raise CollectionError("gh CLI が見つからない（GitHub Actions では既定で導入済み）") from exc
    if completed.returncode != 0:
        raise CollectionError(
            f"`gh {' '.join(args)}` が exit {completed.returncode}: {completed.stderr.strip()}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CollectionError(f"`gh {' '.join(args)}` の出力が JSON ではない: {exc}") from exc


def _ensure_not_truncated(kind: str, payload: object, limit: int) -> None:
    """取得件数が ``--limit`` に達していたら :class:`CollectionError` にする。

    ちょうど ``limit`` 件のときは「全件がたまたま ``limit`` 件」なのか「打ち切られた」のかを
    区別できない。区別できない側は**打ち切り扱い**にする（誤った数字を publish するより、
    レポートを作らずに止まる方が安全＝fail-close）。
    """
    if isinstance(payload, list) and len(payload) >= limit:
        raise CollectionError(
            f"{kind} の取得件数が --limit ({limit}) に達した。"
            "`gh ... list` は新しい側から打ち切るため古い側が黙って落ち、基線窓の再現も"
            "派生判定の参照先 PR も誤る。--limit を十分大きい値へ上げて再実行すること"
            "（誤った数字を publish しないための fail-close）。"
        )


def fetch_issues(
    repository: str,
    limit: int = DEFAULT_FETCH_LIMIT,
    *,
    runner: Callable[[list[str]], object] | None = None,
) -> list[IssueRecord]:
    payload = (runner if runner is not None else _run_gh)(
        [
            "issue",
            "list",
            "--repo",
            repository,
            "--state",
            "all",
            "--limit",
            str(limit),
            "--json",
            ISSUE_FIELDS,
        ]
    )
    _ensure_not_truncated("issue", payload, limit)
    return load_issues(payload)


def fetch_pulls(
    repository: str,
    limit: int = DEFAULT_FETCH_LIMIT,
    *,
    runner: Callable[[list[str]], object] | None = None,
) -> list[PullRequestRecord]:
    payload = (runner if runner is not None else _run_gh)(
        [
            "pr",
            "list",
            "--repo",
            repository,
            "--state",
            "merged",
            "--limit",
            str(limit),
            "--json",
            PULL_FIELDS,
        ]
    )
    # 打ち切り判定は正規化前の生 payload で行う（load_pulls は未 merge 行を落とすため、
    # 正規化後の件数で比べると打ち切りを見逃す）。
    _ensure_not_truncated("pull request", payload, limit)
    return load_pulls(payload)
