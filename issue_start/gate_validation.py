from __future__ import annotations

from typing import Any, Mapping

from .gate_support import IssueStartError



def _validate_tool_input_shape(
    tool_input: Mapping[str, Any], transport: Mapping[str, Any]
) -> None:
    """manifest が宣言する harness 固有 field の必須・混在禁止を検証する。"""
    required = transport.get("required_tool_input_fields")
    forbidden = transport.get("forbidden_tool_input_fields")
    for fields in (required, forbidden):
        if (
            not isinstance(fields, list)
            or not fields
            or not all(isinstance(field, str) and field for field in fields)
            or len(fields) != len(set(fields))
        ):
            raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    if set(required) & set(forbidden):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    missing = [field for field in required if field not in tool_input]
    mixed = [field for field in forbidden if field in tool_input]
    if missing or mixed:
        detail = "missing=" + ",".join(missing) + ";mixed=" + ",".join(mixed)
        raise IssueStartError("ISSUE_START_TOOL_INPUT_SHAPE_INVALID", detail)
    _validate_isolation(tool_input, transport)


def _validate_isolation(
    tool_input: Mapping[str, Any], transport: Mapping[str, Any]
) -> None:
    """manifest transport に worktree 分離を強制する（Issue #350）。

    `issue-implementer` は「isolated worktree で実装する」契約だが、その分離は
    role 側では実現できない——gitgate に worktree を作成・移動する
    verb は無く、agent-command-gate の
    層2 が `cd` を deny するため、仮に worktree を作れてもそこへ潜れない。分離を
    与えられるのは dispatch 側だけで、Claude harness では Agent tool の `isolation`
    パラメータがそれを担う（cwd が `.claude/worktrees/agent-<id>` の locked worktree
    になり、呼び出し元の main worktree は branch switch されない）。

    指定を欠いた dispatch は main worktree を共有したまま branch switch する＝
    呼び出し元の作業ツリーを巻き込むので、dispatch 自体を fail-close で拒否する。
    """
    if "required_isolation" not in transport:
        return
    expected = transport.get("required_isolation")
    if not isinstance(expected, str) or not expected:
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    actual = tool_input.get("isolation")
    if actual != expected:
        raise IssueStartError(
            "ISSUE_START_ISOLATION_NOT_WORKTREE",
            f"expected isolation={expected}; actual={actual!r}",
        )
