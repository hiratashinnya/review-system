"""Project API 呼び出し前に snapshot の健全性と鮮度を検査する。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from blocker_gate.snapshot import RepositorySnapshotError, parse_repository_snapshot

from .model import Abort, MAX_SNAPSHOT_AGE_SECONDS


def check_snapshot(
    raw: Any,
    *,
    now: datetime,
    max_age_seconds: int = MAX_SNAPSHOT_AGE_SECONDS,
) -> tuple[dict[str, Any] | None, Abort | None]:
    """snapshot 単体で決まる fail-close をすべてここで確定させる。"""
    try:
        snapshot = parse_repository_snapshot(raw)
    except RepositorySnapshotError as exc:
        detail = f"{exc.reason}: {exc.detail}" if exc.detail else exc.reason
        return None, Abort("SNAPSHOT_INVALID", detail)

    if not snapshot["pages_complete"] or snapshot["errors"]:
        return snapshot, Abort(
            "SNAPSHOT_DEGRADED",
            f"pages_complete={snapshot['pages_complete']} errors={','.join(snapshot['errors']) or '-'}",
        )

    age = (now - snapshot["generated_at_datetime"]).total_seconds()
    if age > max_age_seconds:
        return snapshot, Abort(
            "SNAPSHOT_STALE",
            f"generated_at={snapshot['generated_at']} age={int(age)}s limit={max_age_seconds}s",
        )
    return snapshot, None
