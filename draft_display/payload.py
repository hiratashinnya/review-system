"""SubagentStop フック stdin payload の読み取り。

本 repo の他の SubagentStop フック（``issue_start/subagent_hooks.py``）が実際に使うキーだけを
読む: ``agent_type``・``last_assistant_message``（最終応答）。未実測のキーには依存しない。
"""

from __future__ import annotations

import json
from typing import Any, Mapping, TextIO


def load_payload(stdin: TextIO) -> dict | None:
    try:
        value = json.load(stdin)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError):
        return None
    return value if isinstance(value, dict) else None


def string_field(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None
