"""Parse and normalize issue and pull request inputs."""

from __future__ import annotations
import json
from .model import IssueRecord, PullRequestRecord, parse_timestamp

class CollectionError(RuntimeError):
    """Input collection or interpretation failed."""


def _optional_timestamp(value: object) -> "None | object":
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise CollectionError(f"タイムスタンプが文字列ではない: {value!r}")
    return parse_timestamp(value)


def load_issues(payload: object) -> list[IssueRecord]:
    """``gh issue list --json number,createdAt,closedAt,body`` 相当の配列を正規化する。"""
    if not isinstance(payload, list):
        raise CollectionError("issue payload が JSON 配列ではない")
    records: list[IssueRecord] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise CollectionError(f"issue entry が object ではない: {entry!r}")
        try:
            number = int(entry["number"])
            created_raw = entry["createdAt"]
        except (KeyError, TypeError, ValueError) as exc:
            raise CollectionError(f"issue entry に number/createdAt が無い: {entry!r}") from exc
        if not isinstance(created_raw, str):
            raise CollectionError(f"issue {number} の createdAt が文字列ではない")
        records.append(
            IssueRecord(
                number=number,
                created_at=parse_timestamp(created_raw),
                closed_at=_optional_timestamp(entry.get("closedAt")),  # type: ignore[arg-type]
                body=entry.get("body") or "",
            )
        )
    return records


def load_pulls(payload: object) -> list[PullRequestRecord]:
    """``gh pr list --state merged --json number,mergedAt`` 相当の配列を正規化する。

    ``mergedAt`` が空の行（merge されていない PR が混ざった場合）は無視する——
    分母は「merge された PR」であり、未 merge を数えると定義がぶれるため。
    """
    if not isinstance(payload, list):
        raise CollectionError("pull request payload が JSON 配列ではない")
    records: list[PullRequestRecord] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise CollectionError(f"pull request entry が object ではない: {entry!r}")
        merged_raw = entry.get("mergedAt")
        if merged_raw in (None, ""):
            continue
        try:
            number = int(entry["number"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CollectionError(f"pull request entry に number が無い: {entry!r}") from exc
        if not isinstance(merged_raw, str):
            raise CollectionError(f"PR {number} の mergedAt が文字列ではない")
        records.append(PullRequestRecord(number=number, merged_at=parse_timestamp(merged_raw)))
    return records


def read_json_file(path: str) -> object:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as exc:
        raise CollectionError(f"{path} を読めない: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CollectionError(f"{path} が JSON として壊れている: {exc}") from exc
