"""Validate same-repository OPEN PR head evidence."""
from __future__ import annotations
from typing import Any, Mapping
from .validation import BranchSourceError, _validate_oid

def _nested_string(raw: Mapping[str, Any], *path: str) -> str:
    value: Any = raw
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise BranchSourceError("BRANCH_API_PARTIAL_RESPONSE")
        value = value[key]
    if not isinstance(value, str) or not value:
        raise BranchSourceError("BRANCH_API_PARTIAL_RESPONSE")
    return value


def _pull_head_oid(pull: Mapping[str, Any], repository: str) -> str:
    """stacked PR の open/same-repository/head binding を閉じて読む。"""
    if pull.get("state") != "open":
        raise BranchSourceError("BRANCH_BASE_PR_NOT_OPEN")
    head_repo = _nested_string(pull, "head", "repo", "full_name")
    base_repo = _nested_string(pull, "base", "repo", "full_name")
    if head_repo.lower() != repository.lower() or base_repo.lower() != repository.lower():
        raise BranchSourceError("BRANCH_BASE_PR_CROSS_REPOSITORY")
    return _validate_oid(
        _nested_string(pull, "head", "sha"), "BRANCH_PR_HEAD_OID_INVALID"
    )
