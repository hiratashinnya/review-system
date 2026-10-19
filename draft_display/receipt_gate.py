"""Prevent the gh-create-issue agent from forging SubagentStop receipts."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import TextIO

from .handoff import AGENT_TYPE, HANDOFF_DIR_REL, RECEIPT_SUFFIX

_RECEIPT_NAME = re.compile(
    r"gh-create-issue--[A-Za-z0-9][A-Za-z0-9._-]*\.md" + re.escape(RECEIPT_SUFFIX)
)


def _is_receipt_candidate(path: str, project_root: Path) -> bool | None:
    """Match lexical and resolved paths; None means the path could not be verified."""
    try:
        root = project_root.resolve(strict=False)
        supplied = Path(path)
        if not supplied.is_absolute():
            supplied = root / supplied
        lexical = Path(os.path.abspath(supplied))
        resolved = Path(os.path.realpath(lexical))
        handoff_dir = root / HANDOFF_DIR_REL
        for candidate in (lexical, resolved):
            try:
                relative = candidate.relative_to(handoff_dir)
            except ValueError:
                continue
            if len(relative.parts) == 1 and _RECEIPT_NAME.fullmatch(relative.name):
                return True
        return False
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


def _deny(stdout: TextIO, reason: str) -> int:
    stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False) + "\n")
    return 0


def run(*, stdin: TextIO, stdout: TextIO, project_root: Path) -> int:
    try:
        payload = json.loads(stdin.read())
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    agent = payload.get("agent_type") or payload.get("subagent_type")
    if agent != AGENT_TYPE:
        return 0
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if tool_name not in {"Write", "Edit"} or not isinstance(tool_input, dict):
        return _deny(
            stdout,
            "Cannot verify gh-create-issue file write; retry with a valid Write/Edit request.",
        )
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return _deny(stdout, "Cannot verify gh-create-issue file path; write is denied.")
    candidate = _is_receipt_candidate(file_path, project_root)
    if candidate is None:
        return _deny(stdout, "Cannot safely resolve gh-create-issue file path; write is denied.")
    if candidate:
        return _deny(
            stdout,
            "Only the SubagentStop hook may create or edit gh-create-issue receipt files.",
        )
    return 0


if __name__ == "__main__":
    import sys

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    raise SystemExit(run(stdin=sys.stdin, stdout=sys.stdout, project_root=root))
