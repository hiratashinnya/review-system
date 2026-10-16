"""read-only工程をworktree所有台帳へ混ぜず専用入力で検証する。"""
from .gate_manifest import _entries, _managed_entries, _isolation_only_entries
from .gate_markers import _marker_payload
from .gate_support import IssueStartError
from .gate_transport import _managed_transport, _require_transport_available
from .gate_validation import _validate_tool_input_shape
from .phase_dispatch import validate_phase_dispatch
from .readonly_phase_ack import ReadOnlyPhaseAck


def parse_readonly_phase(tool_name, tool_input, agent_type, cwd):
    entries = _entries("readonly", required=False)
    readonly = {entry.get("agent_type") for entry in entries}
    writers = {entry.get("agent_type") for entry in _managed_entries() + _isolation_only_entries()}
    if readonly & writers:
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    if agent_type not in readonly:
        return None
    entry, harness, transport = _managed_transport(tool_name, agent_type, entries)
    _require_transport_available(harness, transport)
    _validate_tool_input_shape(tool_input, transport)
    if harness != "claude" or tool_input.get(transport["agent_type_field"]) != agent_type:
        raise IssueStartError("ISSUE_START_TARGET_UNKNOWN")
    raw = _marker_payload(tool_input, transport, transport["phase_binding_marker"])
    validate_phase_dispatch(raw, agent_type, cwd)
    return ReadOnlyPhaseAck(agent_type, entry["entrypoint"])
