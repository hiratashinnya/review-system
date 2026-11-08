"""Open PR head identity verification with fail-closed API evidence."""
from __future__ import annotations
from typing import Any, Mapping
from branch_source.policy import BranchApi, BranchSourceError
from .adopt_models import AdoptBranchRequest
def _string_at(raw: Mapping[str, Any], *path: str) -> str:
    value: Any = raw
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise BranchSourceError("BRANCH_API_PARTIAL_RESPONSE", "/".join(path))
        value = value[key]
    if not isinstance(value, str) or not value:
        raise BranchSourceError("BRANCH_API_PARTIAL_RESPONSE", "/".join(path))
    return value
def _verify_pull_request(
    request: AdoptBranchRequest, *, api: BranchApi
) -> None:
    """``--pr`` 指定時、その PR が open かつ head が期待 OID/ブランチであることを再検証する。

    remote 先端の OID 一致だけだと「その OID が今も PR の head である」ことは言えない
    （force-push や PR クローズの直後を掴みうる）。到達不能は :class:`BranchSourceError`
    （``API_UNREACHABLE``）として client 側から送出され、ここで握り潰さない＝fail-close。
    """
    pull = api.pull_request(request.repository, int(request.pr))
    if not isinstance(pull, dict):
        raise BranchSourceError("BRANCH_API_PARTIAL_RESPONSE", "pull_request")
    if pull.get("state") != "open":
        raise BranchSourceError("BRANCH_ADOPT_PR_NOT_OPEN", str(request.pr))
    head_ref = _string_at(pull, "head", "ref")
    head_sha = _string_at(pull, "head", "sha").lower()
    if head_ref != request.branch_name:
        raise BranchSourceError(
            "BRANCH_ADOPT_PR_HEAD_MISMATCH", f"head.ref={head_ref}"
        )
    if head_sha != request.expected_oid:
        raise BranchSourceError(
            "BRANCH_ADOPT_PR_HEAD_MISMATCH", f"head.sha={head_sha}"
        )
