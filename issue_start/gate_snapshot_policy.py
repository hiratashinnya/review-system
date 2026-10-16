from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .gate_support import (
    IssueStartError, SNAPSHOT_FALLBACK_REASON, SNAPSHOT_MAX_AGE_SECONDS,
)



def _assert_snapshot_fresh(
    snapshot: Mapping[str, Any], now: datetime | None
) -> None:
    """上限付き staleness を機械的に強制する。期限切れも未来時刻も fail-close。"""
    current = datetime.now(timezone.utc) if now is None else now.astimezone(timezone.utc)
    age = (current - snapshot["generated_at_datetime"]).total_seconds()
    if age < 0:
        raise IssueStartError(
            "ISSUE_START_SNAPSHOT_FUTURE",
            f"generated_at={snapshot['generated_at']}; now={current.isoformat()}",
        )
    if age > SNAPSHOT_MAX_AGE_SECONDS:
        raise IssueStartError(
            "ISSUE_START_SNAPSHOT_STALE",
            f"age={int(age)}s; max={SNAPSHOT_MAX_AGE_SECONDS}s;"
            f" generated_at={snapshot['generated_at']}",
        )


def _snapshot_fallback_required(
    blocker: Mapping[str, Any], collected: Mapping[str, Any]
) -> bool:
    """当該 invocation が GitHub を**一度も観測できていない**ときだけ真を返す。

    条件は3つの AND であり、どれか一つでも欠ければ従来どおり ERROR のまま
    fail-close する。

    1. verdict が ``ERROR`` である。
    2. ``reasons`` に ``API_UNREACHABLE`` を含む。``primary_reason`` ではなく
       membership で見るのは、到達不能環境の実測形が
       ``["API_UNREACHABLE", "RELATION_TARGET_UNREADABLE"]`` であり canonical
       sort の先頭が別 reason になるため（この理由は F-345-01 の是正後も有効）。
    3. **収集できた node が1つも無い。** reasons membership だけを引き金にすると、
       API へ到達できている環境で1 node が一過性 timeout / URLError を起こした
       だけでも fallback が起動し、本来 fail-close だった invocation が最大10分
       stale な材料で ALLOW になりうる（F-345-01）。1 node でも読めていれば
       その invocation は GitHub provenance を観測している＝「到達不能」では
       ないので、stale な材料を使う理由がない。

    3 は「空である」ことを**積極的に確認**する（key 欠落・型不正では真を返さない）。
    fallback は許容側の経路なので、観測できないときは開かない。
    """
    reasons = blocker.get("reasons")
    nodes = collected.get("nodes")
    return (
        blocker.get("result") == "ERROR"
        and isinstance(reasons, list)
        and SNAPSHOT_FALLBACK_REASON in reasons
        and isinstance(nodes, dict)
        and not nodes
    )
