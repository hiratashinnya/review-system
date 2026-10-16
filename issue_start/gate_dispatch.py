from __future__ import annotations

from datetime import datetime, timezone
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping

from .gate_caller import _caller_agent_type
from .gate_isolation_dispatch import _parse_isolation_only
from .gate_manifest import (
    _agent_types,
    _claude_request,
    _isolation_only_entries,
    _managed_entries,
)
from .gate_markers import _marker_payload
from .gated_roles import GATED_ROLES
from .gate_support import (
    IssueStartError, IssueStartRequest, IsolationOnlyAck,
)
from .gate_transport import _managed_transport, _require_transport_available
from .gate_validation import _validate_tool_input_shape
from .phase_dispatch import validate_phase_dispatch
from .readonly_phase_dispatch import parse_readonly_phase



def parse_dispatch_payload(
    payload: Mapping[str, Any],
    *,
    cwd: Path | None = None,
    now: datetime | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> IssueStartRequest | IsolationOnlyAck | None:
    """Parse Claude dispatch payloads and return the matching binding."""
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        raise IssueStartError("ISSUE_START_PAYLOAD_INVALID")
    caller_agent_type = _caller_agent_type(payload)
    if caller_agent_type in GATED_ROLES:
        raise IssueStartError(
            "ISSUE_START_GATED_ROLE_TASK_DENIED",
            f"caller agent_type={caller_agent_type} may not dispatch Task/Agent "
            "(GATED_ROLES must not spawn subagents; this closes the "
            "agent-command-gate.sh allowlist-bypass route recorded in Issue #517)",
        )
    targets = [tool_input.get(field) for field in ("agent_type", "subagent_type")]
    present_targets = [target for target in targets if target is not None]
    if len(present_targets) != 1 or not isinstance(present_targets[0], str) or not present_targets[0]:
        raise IssueStartError("ISSUE_START_TARGET_UNKNOWN")
    agent_type = present_targets[0]
    readonly = parse_readonly_phase(tool_name, tool_input, agent_type, cwd)
    if readonly is not None:
        return readonly
    managed_types = _agent_types(_managed_entries())
    isolation_only_entries = _isolation_only_entries()
    isolation_only_types = _agent_types(isolation_only_entries)
    # 同じ agent_type が両区分に載っていたら、どちらの契約で判定すべきか一意に決まらない。
    # 「厳しい方」を勝手に選ばず manifest 側の誤りとして fail-close する。
    if managed_types & isolation_only_types:
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    if agent_type in isolation_only_types:
        return _parse_isolation_only(
            tool_name,
            tool_input,
            agent_type,
            isolation_only_entries,
            payload=payload,
            cwd=cwd,
            now=datetime.now(timezone.utc) if now is None else now,
            runner=runner,
        )
    if agent_type not in managed_types:
        return None
    entry, harness, transport = _managed_transport(tool_name, agent_type)
    _require_transport_available(harness, transport)
    if transport.get("phase_binding_marker"):
        validate_phase_dispatch(_marker_payload(tool_input, transport, transport["phase_binding_marker"]), agent_type, cwd)
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
    request = _claude_request(raw)
    if request.entrypoint != entrypoint:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN", request.entrypoint)
    return request
