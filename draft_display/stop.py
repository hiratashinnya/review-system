"""SubagentStop（matcher ``gh-create-issue``）: handoff 本文を ``systemMessage`` でチャットへ表示する。

``systemMessage`` はモデルを経由せずオーナーへ届く。本文を主文脈が再出力しなくて済むので
トークンの二重消費にならない。停止は決してブロックしない（可視化専用・fail-open）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TextIO

from . import handoff
from .payload import load_payload, string_field


def _evidence(stderr: TextIO, **fields: Any) -> None:
    stderr.write(
        json.dumps({"hook": "draft-display-stop", **fields}, ensure_ascii=False, sort_keys=True) + "\n"
    )


def run(*, stdin: TextIO, stdout: TextIO, stderr: TextIO, project_root: Path) -> int:
    payload = load_payload(stdin)
    if payload is None:
        return 0
    if string_field(payload, "agent_type", "subagent_type") != handoff.AGENT_TYPE:
        return 0
    rel = handoff.find_handoff_rel(string_field(payload, "last_assistant_message") or "")
    if rel is None:
        _evidence(stderr, result="skip", reason="NO_HANDOFF_LINE")
        return 0
    path = handoff.resolve_handoff(project_root, rel)
    loaded = handoff.read_for_display(path) if path is not None else None
    if path is None or loaded is None:
        _evidence(stderr, result="skip", reason="HANDOFF_UNREADABLE", handoff=rel)
        return 0
    body, truncated = loaded
    message = f"[gh-create-issue サブエージェントの成果物: {rel}]\n\n{body}"
    if truncated:
        message += f"\n\n…（{handoff.MAX_DISPLAY_BYTES} バイトで切詰め。全文は {rel}）"
    json.dump({"systemMessage": message}, stdout, ensure_ascii=False)
    stdout.write("\n")
    _evidence(stderr, result="displayed", handoff=rel, truncated=truncated)
    return 0
