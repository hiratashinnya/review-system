from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping

from .gate_git import _canonical_github_repository, _git_output
from .gate_support import (
    IssueStartError, SNAPSHOT_BRANCH, SNAPSHOT_PATH, SNAPSHOT_REMOTE_REF, _REPOSITORY,
)
from blocker_gate.snapshot import RepositorySnapshotError, parse_repository_snapshot



def read_repository_snapshot(
    *,
    repository: str,
    cwd: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> Mapping[str, Any]:
    """孤立ブランチ ``blocker-snapshot`` の ``snapshot.json`` を fetch して読む。

    ローカルの作業ツリーやローカル cache は材料にしない（改竄と stale を
    同時に許すため）。必ず ``origin`` から fetch した ref を読む。

    ``origin`` が invocation の repository を指すことを **fetch より前に**
    検証する（Issue #345 F-345-02）。これが無いと identity 束縛が snapshot の
    自己申告 ``repository`` field だけになり、origin を自分の管理下へ向けられる
    者が対象 repository を名乗る snapshot を配って ALLOW を作れてしまう
    ——policy §3.3.1 の「偽造には対象 repository への push 権限が要る」という
    論拠がその経路で成立しなくなる。正規化は Codex 経路
    （``_canonical_github_repository``）と同一とする。
    """
    top_level = _git_output(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        runner=runner,
        reason="ISSUE_START_SNAPSHOT_GIT_ERROR",
    ).strip()
    if not top_level:
        raise IssueStartError("ISSUE_START_SNAPSHOT_GIT_ERROR", "rev-parse")
    try:
        root = Path(top_level).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise IssueStartError("ISSUE_START_SNAPSHOT_GIT_ERROR", "toplevel") from exc
    # `_run_git` ではなく `_git_output` を使うのは、snapshot 経路の git 実行に
    # 揃えて timeout を掛けるため（到達不能環境で git がぶら下がると gate ごと
    # 止まる）。複数行・空文字は `_canonical_github_repository` が弾く。
    origin = _canonical_github_repository(
        _git_output(
            ["git", "remote", "get-url", "origin"],
            cwd=root,
            runner=runner,
            reason="ISSUE_START_SNAPSHOT_GIT_ERROR",
        ).strip()
    )
    if origin != repository:
        raise IssueStartError(
            "ISSUE_START_SNAPSHOT_ORIGIN_MISMATCH",
            f"origin={origin}; request={repository}",
        )
    _git_output(
        [
            "git",
            "fetch",
            "--no-tags",
            "--quiet",
            "origin",
            f"+refs/heads/{SNAPSHOT_BRANCH}:{SNAPSHOT_REMOTE_REF}",
        ],
        cwd=root,
        runner=runner,
        reason="ISSUE_START_SNAPSHOT_FETCH_FAILED",
    )
    raw = _git_output(
        ["git", "show", f"{SNAPSHOT_REMOTE_REF}:{SNAPSHOT_PATH}"],
        cwd=root,
        runner=runner,
        reason="ISSUE_START_SNAPSHOT_UNREADABLE",
    )
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise IssueStartError("ISSUE_START_SNAPSHOT_INVALID_JSON") from exc
    try:
        return parse_repository_snapshot(value)
    except RepositorySnapshotError as exc:
        raise IssueStartError("ISSUE_START_SNAPSHOT_INVALID", exc.reason) from exc
