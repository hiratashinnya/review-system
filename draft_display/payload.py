"""フック stdin payload の読み取り（SubagentStop／PostToolUse 共通）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, TextIO

TRANSCRIPT_TAIL_BYTES = 256 * 1024


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


def transcript_tail(payload: Mapping[str, Any]) -> str:
    """``agent_transcript_path`` の末尾（読めなければ空文字）。最終応答が payload に無い版の保険。"""
    raw = string_field(payload, "agent_transcript_path")
    if raw is None:
        return ""
    try:
        with Path(raw).open("rb") as stream:
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size - TRANSCRIPT_TAIL_BYTES))
            return stream.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
