"""new-branch の固定スキーマ引数を解析する。"""

from __future__ import annotations

from typing import Sequence

from .validation import (
    BranchSourceError, NewBranchRequest, _validate_branch, _validate_oid,
    _validate_repository,
)


def parse_new_branch_args(args: Sequence[str]) -> NewBranchRequest:
    """固定 schema の new-branch 引数を parse する。未知/重複 flag は拒否。"""
    if not args:
        raise BranchSourceError("BRANCH_ARGUMENT_INVALID", "missing branch name")
    name = _validate_branch(args[0], "BRANCH_NAME_INVALID")
    values: dict[str, str] = {}
    allowed = {"--repository", "--base-ref", "--base-oid", "--base-pr"}
    index = 1
    while index < len(args):
        flag = args[index]
        if flag not in allowed or flag in values or index + 1 >= len(args):
            raise BranchSourceError("BRANCH_ARGUMENT_INVALID", flag)
        values[flag] = args[index + 1]
        index += 2
    required = {"--repository", "--base-ref", "--base-oid"}
    if not required.issubset(values):
        missing = ",".join(sorted(required - set(values)))
        raise BranchSourceError("BRANCH_ARGUMENT_INVALID", f"missing {missing}")
    base_pr: int | None = None
    if "--base-pr" in values:
        raw_pr = values["--base-pr"]
        try:
            base_pr = int(raw_pr) if len(raw_pr) <= 4300 and raw_pr.isascii() and raw_pr.isdigit() else 0
        except ValueError:
            base_pr = 0
        if base_pr < 1:
            raise BranchSourceError("BRANCH_BASE_PR_INVALID", raw_pr)
    return NewBranchRequest(
        branch_name=name,
        repository=_validate_repository(values["--repository"]),
        base_ref=_validate_branch(values["--base-ref"], "BRANCH_BASE_REF_INVALID"),
        base_oid=_validate_oid(values["--base-oid"]),
        base_pr=base_pr,
    )


