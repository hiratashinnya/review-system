from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
from typing import Any, Callable, Mapping, Sequence

from .gate_markers import _fix_binding, _marker_payload
from .gate_support import IssueStartError, IsolationOnlyAck
from .gate_transport import _managed_transport, _require_transport_available
from .gate_validation import _validate_tool_input_shape
from .phase_dispatch import validate_phase_dispatch
from .phase_target_binding import validate_phase_target
from .author_continuation import validate_author_continuation



def _parse_isolation_only(
    tool_name: str,
    tool_input: Mapping[str, Any],
    agent_type: str,
    entries: Sequence[Mapping[str, Any]],
    *,
    payload: Mapping[str, Any],
    cwd: Path | None,
    now: datetime,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> IsolationOnlyAck:
    """`isolation_only` 区分の dispatch を検証する（GitHub API へは一切行かない）。

    managed 経路と**同じ** :func:`_validate_tool_input_shape` を通すので、
    `required_isolation` の強制（`ISSUE_START_ISOLATION_NOT_WORKTREE`）は分岐で
    弱まらない——ここが本区分の存在理由（分離だけを課したい）そのものだから。
    """
    entry, harness, transport = _managed_transport(tool_name, agent_type, entries)
    _require_transport_available(harness, transport)
    approval = None
    if transport.get("phase_binding_marker"):
        approval = validate_phase_dispatch(_marker_payload(tool_input, transport, transport["phase_binding_marker"]), agent_type, cwd)
    _validate_tool_input_shape(tool_input, transport)
    expected_field = transport.get("agent_type_field")
    if expected_field not in {"agent_type", "subagent_type"} or tool_input.get(expected_field) != agent_type:
        raise IssueStartError("ISSUE_START_TARGET_UNKNOWN")
    entrypoint = entry.get("entrypoint")
    if not isinstance(entrypoint, str):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    if harness != "claude":
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    raw = _marker_payload(tool_input, transport, transport.get("binding_marker"))
    ack = _fix_binding(raw, entrypoint=entrypoint, agent_type=agent_type)
    if approval is not None:
        validate_phase_target(approval, raw, cwd)
    validate_author_continuation(tool_input, transport, ack, cwd, runner)
    return ack
