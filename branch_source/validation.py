"""分岐元要求の値と検証。"""

from __future__ import annotations

import re
from dataclasses import dataclass

_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")
_OID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class BranchSourceError(Exception):
    """分岐元を一意かつ fresh に証明できない場合の fail-close error。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class NewBranchRequest:
    branch_name: str
    repository: str
    base_ref: str
    base_oid: str
    base_pr: int | None = None


def _validate_repository(value: str) -> str:
    if not _REPOSITORY.fullmatch(value):
        raise BranchSourceError("BRANCH_REPOSITORY_INVALID", value)
    return value


def _validate_branch(value: str, reason: str) -> str:
    if (
        not value
        or value.startswith(("-", "/"))
        or value.endswith(("/", "."))
        or not _BRANCH.fullmatch(value)
        or ".." in value
        or "//" in value
        or "@{" in value
        or any(
            not part or part.startswith(".") or part.endswith(".lock")
            for part in value.split("/")
        )
    ):
        raise BranchSourceError(reason, value)
    return value


def _validate_oid(value: str, reason: str = "BRANCH_BASE_OID_INVALID") -> str:
    normalized = value.lower()
    if not _OID.fullmatch(normalized):
        raise BranchSourceError(reason, value)
    return normalized


