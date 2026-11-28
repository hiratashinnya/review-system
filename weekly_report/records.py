"""Validate and project the fields used in weekly GitHub observations."""

from datetime import datetime
import re

from .gh_pull_records import pull_identity, run_pull_requests

OID = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")


def _number(value):
    if type(value) is not int or value <= 0:
        raise ValueError("positive GitHub id required")
    return value


def _text(value):
    if not isinstance(value, str):
        raise ValueError("text field required")
    return value


def _moment(value):
    parsed = datetime.fromisoformat(_text(value))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include an offset")
    return parsed


def _optional_moment(value):
    return _moment(value) if value is not None else None


def _oid(value):
    return value.lower() if isinstance(value, str) and OID.fullmatch(value) else None


def _item(row):
    state = row["state"]
    if state not in ("open", "closed"):
        raise ValueError("unknown issue or pull request state")
    return {
        "number": _number(row["number"]), "title": _text(row["title"]), "state": state,
        "created_at": _moment(row["created_at"]), "updated_at": _moment(row["updated_at"]),
        "closed_at": _optional_moment(row["closed_at"]),
    }


def issue(row):
    item = _item(row)
    reason = row.get("state_reason")
    children = row.get("sub_issues_summary")
    dependencies = row.get("issue_dependencies_summary")
    body = row["body"]
    return {
        **item, "state_reason": _text(reason) if reason is not None else None,
        "body": _text(body) if body is not None else body,
        "is_pull": "pull_request" in row,
        "labels": [_text(label["name"]) for label in row["labels"]],
        "sub_issues_summary": children if isinstance(children, dict) else None,
        "dependencies_summary": dependencies if isinstance(dependencies, dict) else None,
    }


def pull(row):
    item = _item(row)
    draft = row["draft"]
    if not isinstance(draft, bool):
        raise ValueError("draft must be a boolean")
    return {**item, "merged_at": _optional_moment(row["merged_at"]),
            "draft": draft, **pull_identity(row, _oid)}


def relation(row):
    if row["state"] not in ("open", "closed") or "pull_request" in row:
        raise ValueError("invalid related issue")
    return {"number": _number(row["number"]), "id": _number(row["id"]),
            "title": _text(row["title"]), "state": row["state"],
            "repository_url": _text(row["repository_url"]),
            "reason": row.get("state_reason")}


def workflow_run(row):
    return {"id": _number(row["id"]), "name": row.get("name"), "event": _text(row["event"]),
            "status": _text(row["status"]), "conclusion": row["conclusion"],
            "created_at": _moment(row["created_at"]), "head_sha": _oid(row.get("head_sha")),
            "pull_requests": run_pull_requests(row, _oid)}


def review(row):
    return {"id": _number(row["id"]), "state": _text(row["state"]),
            "submitted_at": _optional_moment(row.get("submitted_at")),
            "commit_id": _oid(row.get("commit_id"))}


def public_item(item):
    return {key: val for key, val in item.items() if key not in ("body", "is_pull")}
