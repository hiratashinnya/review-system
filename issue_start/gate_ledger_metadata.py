from __future__ import annotations

import json
from typing import Mapping

from .gate_support import BINDING_MARKER



def _ledger_metadata(payload: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """台帳起票に載せる付随情報（``agent_type`` / ``branch_name``）を best-effort で読む。

    ここは**判定に使わない**（起票の材料にするだけ）。`parse_dispatch_payload` が既に
    受理した payload を読み直しているので厳格な検証はせず、読めなければ ``None`` を返す。
    ``branch_name`` は稼働中のClaude markerから得る。
    """
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, Mapping):
        return None, None
    agent_type = None
    for field in ("agent_type", "subagent_type"):
        value = tool_input.get(field)
        if isinstance(value, str) and value:
            agent_type = value
            break
    branch_name = None
    prompt = tool_input.get("prompt")
    if isinstance(prompt, str):
        lines = [line for line in prompt.splitlines() if line.startswith(BINDING_MARKER)]
        if len(lines) == 1:
            try:
                raw = json.loads(lines[0][len(BINDING_MARKER):])
            except json.JSONDecodeError:
                raw = None
            if isinstance(raw, dict) and isinstance(raw.get("branch_name"), str):
                branch_name = raw["branch_name"]
    return agent_type, branch_name
