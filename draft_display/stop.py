"""SubagentStop hook that displays bounded handoffs and records a caller receipt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TextIO

from . import handoff
from .payload import load_payload, string_field


MAX_HOOK_OUTPUT_CHARS = 9_000


def _evidence(stderr: TextIO, **fields: Any) -> None:
    stderr.write(json.dumps({"hook": "draft-display-stop", **fields}, ensure_ascii=False) + "\n")


def _emit(stdout: TextIO, message: str) -> bool:
    serialized = json.dumps({"systemMessage": message}, ensure_ascii=False)
    if len(serialized) > MAX_HOOK_OUTPUT_CHARS:
        return False
    stdout.write(serialized + "\n")
    return True


def _fail(
    stderr: TextIO, reason: str, project_root: Path, rel: str | None = None
) -> int:
    if rel:
        handoff.write_receipt(project_root, rel, status="fallback_required", reason=reason)
    _evidence(stderr, result="skip", reason=reason, handoff=rel)
    return 0


def run(*, stdin: TextIO, stdout: TextIO, stderr: TextIO, project_root: Path) -> int:
    payload = load_payload(stdin)
    if payload is None or string_field(payload, "agent_type", "subagent_type") != handoff.AGENT_TYPE:
        return 0
    rel = handoff.find_handoff_rel(string_field(payload, "last_assistant_message") or "")
    if rel is None:
        _evidence(stderr, result="skip", reason="NO_HANDOFF_LINE")
        return 0
    path = handoff.resolve_handoff(project_root, rel)
    loaded = handoff.read_for_display(project_root, rel) if path is not None else None
    if path is None or loaded is None:
        return _fail(stderr, "HANDOFF_UNREADABLE", project_root, rel)
    body, truncated = loaded
    message = f"[gh-create-issue 成果物: {rel}]\n\n{body}"
    if truncated or not _emit(stdout, message):
        return _fail(stderr, "HOOK_OUTPUT_LIMIT", project_root, rel)
    handoff.write_receipt(project_root, rel, status="displayed")
    _evidence(stderr, result="displayed", handoff=rel)
    return 0
