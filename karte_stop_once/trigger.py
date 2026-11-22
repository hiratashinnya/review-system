"""Bind a successful Karte command to the issue named in its tool result."""
import json
import re

from karte_notify.trigger import extract_commands

_VERB = re.compile(r"\bpython3?\s+-m\s+karte\s+(ingest-reviewer|ingest-review|append|close-attempt|decide|status)\b")
_ISSUE = re.compile(r"(?<![\w-])--issue(?:=|\s+)([1-9][0-9]*)\b")
_RESULT = re.compile(r"===\s+(?:ingest-review|append|close-attempt|status):\s*issue-([1-9][0-9]*)\b")


def issue_from_result(payload: dict) -> int | None:
    """Never guess from repository-global active.json (shared across sessions)."""
    input_data = payload.get("tool_input")
    if not isinstance(input_data, dict):
        return None
    commands = extract_commands(payload.get("tool_name"), input_data)
    commands = [c for c in commands if _VERB.search(c)]
    if len(commands) != 1:
        return None
    explicit = _ISSUE.search(commands[0])
    response = payload.get("tool_response")
    if isinstance(response, dict):
        chunks = [response.get("stdout"), response.get("text"), response.get("content")]
        lines = "\n".join(x for x in chunks if isinstance(x, str))
    elif isinstance(response, str):
        lines = response
    else:
        lines = ""
    observed = _RESULT.search(lines)
    if observed:
        result_issue = int(observed.group(1))
    else:
        # "karte status --json" prints a bare status payload, not a text header.
        if _VERB.search(commands[0]).group(1) != "status":
            return None
        try:
            result = json.loads(lines)
        except json.JSONDecodeError:
            return None
        if not isinstance(result, dict) or not isinstance(result.get("verdict"), str):
            return None
        result_issue = result.get("issue")
        if type(result_issue) is not int or result_issue < 1:
            return None
    if explicit and int(explicit.group(1)) != result_issue:
        return None
    return result_issue
