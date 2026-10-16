from __future__ import annotations

import json
from typing import Any, Mapping

from .gate_support import (
    IssueStartError, IsolationOnlyAck, _BRANCH, _HANDOFF_PATH, _OID, _REPOSITORY,
)



def _marker_payload(
    tool_input: Mapping[str, Any], transport: Mapping[str, Any], marker: str
) -> Mapping[str, Any]:
    """prompt から binding marker 行をちょうど1つ取り出して JSON として読む。"""
    prompt_field = transport.get("prompt_field")
    if not isinstance(prompt_field, str) or not isinstance(marker, str) or not marker:
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    prompt = tool_input.get(prompt_field)
    if not isinstance(prompt, str):
        raise IssueStartError("ISSUE_START_BINDING_MISSING")
    lines = [line for line in prompt.splitlines() if line.startswith(marker)]
    if len(lines) != 1:
        raise IssueStartError("ISSUE_START_BINDING_MISSING_OR_DUPLICATE")
    try:
        raw = json.loads(lines[0][len(marker):])
    except json.JSONDecodeError as exc:
        raise IssueStartError("ISSUE_START_BINDING_INVALID_JSON") from exc
    if not isinstance(raw, dict):
        raise IssueStartError("ISSUE_START_BINDING_INVALID_JSON")
    return raw


def _fix_binding(
    raw: Mapping[str, Any], *, entrypoint: str, agent_type: str
) -> IsolationOnlyAck:
    """`ISSUE_FIX_BINDING_V1` marker（exact 6 field）を検証して ack を返す。

    `base_*` を欠くのは、この区分が **GitHub API を叩かない**から——blocker 判定と
    branch-source 判定の材料はどちらもここでは行わない。一方 `repository` は持つ：
    是正者は `gitgate adopt-branch --repository OWNER/REPO --expected-oid` で既存 PR
    ブランチを自分の worktree へ取得するが、是正者は生 `git remote` を deny されており
    OWNER/REPO を機械的に得る手段が無い（F-354-10）。`expected_oid` と同じ理由で、
    値の出所を dispatch 契約側に固定しておく（出所が曖昧なまま是正者に推測させると、
    掴む repository/commit が dispatch と食い違いうる）。
    """
    expected = {"issue", "round", "branch_name", "repository", "expected_oid", "handoff_path"}
    if set(raw) != expected:
        raise IssueStartError("ISSUE_START_BINDING_UNKNOWN_FIELD")
    issue = raw.get("issue")
    round_ = raw.get("round")
    branch_name = raw.get("branch_name")
    repository = raw.get("repository")
    expected_oid = raw.get("expected_oid")
    handoff_path = raw.get("handoff_path")
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        raise IssueStartError("ISSUE_START_ISSUE_INVALID")
    if not isinstance(round_, int) or isinstance(round_, bool) or round_ < 1:
        raise IssueStartError("ISSUE_START_ROUND_INVALID")
    if not isinstance(branch_name, str) or not _BRANCH.fullmatch(branch_name):
        raise IssueStartError("ISSUE_START_BRANCH_INVALID")
    if not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
        raise IssueStartError("ISSUE_START_REPOSITORY_INVALID")
    if not isinstance(expected_oid, str) or not _OID.fullmatch(expected_oid):
        raise IssueStartError("ISSUE_START_EXPECTED_OID_INVALID")
    match = _HANDOFF_PATH.fullmatch(handoff_path) if isinstance(handoff_path, str) else None
    if match is None:
        raise IssueStartError(
            "ISSUE_START_HANDOFF_PATH_INVALID",
            "expected tmp/_handoff/<name>.yaml (作業ツリールート相対)",
        )
    # ファイル名を `{agent_type}--issue-{issue}` に束縛する。境界の1文字（`-` か `.`）まで
    # 見るのは、`issue-354` の dispatch が `…--issue-3541.yaml`（別 Issue のファイル）を
    # 受理しないため（`.claude/agents/issue-fixer.md` と同じ検査を dispatch 側でも掛ける）。
    prefix = f"{agent_type}--issue-{issue}"
    name = match.group("name")
    if not (name == prefix or (name.startswith(prefix) and name[len(prefix)] in "-.")):
        raise IssueStartError(
            "ISSUE_START_HANDOFF_PATH_INVALID", f"expected file name to start with {prefix}"
        )
    return IsolationOnlyAck(
        entrypoint=entrypoint,
        agent_type=agent_type,
        issue=issue,
        round=round_,
        branch_name=branch_name,
        handoff_path=handoff_path,
        expected_oid=expected_oid,
        repository=repository,
    )
