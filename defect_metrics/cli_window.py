"""Resolve report timestamps and windows."""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from .model import Window, parse_timestamp
from .collect import DEFAULT_FETCH_LIMIT, CollectionError, fetch_issues, fetch_pulls, load_issues, load_pulls, read_json_file
from .model import IssueRecord, PullRequestRecord


def resolve_now(explicit: str | None) -> datetime:
    """現在時刻。``--now`` があればそれを使う（本パッケージ唯一の wall clock 読み取り）。"""
    if explicit:
        return parse_timestamp(explicit)
    return datetime.now(timezone.utc)


def resolve_window(
    now: datetime,
    start: str | None,
    end: str | None,
    days: float,
) -> Window:
    """``--window-start`` / ``--window-end`` / ``--window-days`` から窓を決める。

    両端が省略されたときだけ ``now`` を終端に採る（窓を明示すれば決定的になる）。
    """
    span = timedelta(days=days)
    if start and end:
        return Window(start=parse_timestamp(start), end=parse_timestamp(end))
    if start:
        begin = parse_timestamp(start)
        return Window(start=begin, end=begin + span)
    if end:
        finish = parse_timestamp(end)
        return Window(start=finish - span, end=finish)
    return Window(start=now - span, end=now)


def gather(
    repository: str,
    issues_json: str | None,
    pulls_json: str | None,
    limit: int,
) -> tuple[list[IssueRecord], list[PullRequestRecord]]:
    issues = (
        load_issues(read_json_file(issues_json)) if issues_json else fetch_issues(repository, limit)
    )
    pulls = (
        load_pulls(read_json_file(pulls_json)) if pulls_json else fetch_pulls(repository, limit)
    )
    return issues, pulls
