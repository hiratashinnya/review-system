"""Fail-closed adopt argument parser."""
from __future__ import annotations
from typing import Sequence
from branch_source.policy import BranchSourceError, validate_branch_ref, validate_repository
from .adopt_models import AdoptBranchRequest, _ADOPT_OID, _POSITIVE_INT
def parse_adopt_branch_args(args: Sequence[str]) -> AdoptBranchRequest:
    """固定 schema の adopt-branch 引数を parse する。未知/重複 flag は拒否（git は実行しない）。"""
    if not args:
        raise BranchSourceError("BRANCH_ARGUMENT_INVALID", "missing branch name")
    name = validate_branch_ref(args[0], "BRANCH_NAME_INVALID")
    values: dict[str, str] = {}
    allowed = {"--repository", "--expected-oid", "--pr"}
    index = 1
    while index < len(args):
        flag = args[index]
        if flag not in allowed or flag in values or index + 1 >= len(args):
            raise BranchSourceError("BRANCH_ARGUMENT_INVALID", flag)
        values[flag] = args[index + 1]
        index += 2
    required = {"--repository", "--expected-oid"}
    if not required.issubset(values):
        missing = ",".join(sorted(required - set(values)))
        raise BranchSourceError("BRANCH_ARGUMENT_INVALID", f"missing {missing}")

    raw_oid = values["--expected-oid"]
    normalized_oid = raw_oid.lower()
    if not _ADOPT_OID.fullmatch(normalized_oid):
        raise BranchSourceError("BRANCH_ADOPT_OID_INVALID", raw_oid)

    pr: int | None = None
    if "--pr" in values:
        raw_pr = values["--pr"]
        if not _POSITIVE_INT.fullmatch(raw_pr):
            raise BranchSourceError("BRANCH_ADOPT_PR_INVALID", raw_pr)
        pr = int(raw_pr)

    return AdoptBranchRequest(
        branch_name=name,
        repository=validate_repository(values["--repository"]),
        expected_oid=normalized_oid,
        pr=pr,
    )
