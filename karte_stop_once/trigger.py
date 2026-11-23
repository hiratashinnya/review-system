"""Bind a successful Karte command to the issue named in its tool result."""
import json
import re

from karte_notify.trigger import extract_commands

_VERB = re.compile(r"\bpython3?\s+-m\s+karte\s+(ingest-reviewer|ingest-review|append|close-attempt|decide|status)\b")
_ISSUE = re.compile(r"(?<![\w-])--issue(?:=|\s+)([1-9][0-9]*)\b")
_RESULT = re.compile(r"(?m)^=== (ingest-review|append|close-attempt|status): issue-([1-9][0-9]*)\b")
_DECIDE = re.compile(r"(?m)^=== decide: (F-([1-9][0-9]*)-[0-9]+) ===")
_FINDING = re.compile(r"(?<![\w-])--finding(?:=|\s+)(F-[1-9][0-9]*-[0-9]+)\b")


def _result_texts(response) -> list[str]:
    """Accept Bash text and MCP text blocks, never error or image blocks."""
    if isinstance(response, str):
        return [response]
    if not isinstance(response, dict):
        return []
    if any(response.get(flag) for flag in ("isError", "is_error", "error", "interrupted")):
        return []
    for key in ("exit_code", "exitCode", "returncode"):
        if key in response and (type(response[key]) is not int or response[key] != 0):
            return []
    content = response.get("content")
    items = [response.get("stdout"), response.get("text")]
    if isinstance(content, str):
        items.append(content)
    elif isinstance(content, list):
        items.extend(block.get("text") for block in content if isinstance(block, dict)
                     and block.get("type", "text") == "text")
    return [item for item in items if isinstance(item, str)]



def issue_from_result(payload: dict) -> int | None:
    """Bind only a single Issue proven by the command and successful output."""
    inputs = payload.get("tool_input")
    if not isinstance(inputs, dict):
        return None
    commands = [(command, match.group(1))
                for command in extract_commands(payload.get("tool_name"), inputs)
                if (match := _VERB.search(command))]
    if len(commands) != 1:
        return None
    command, verb = commands[0]
    explicit = _ISSUE.search(command)
    finding = _FINDING.search(command) if verb == "decide" else None
    if verb == "decide" and not finding:
        return None

    matches = []
    for text in _result_texts(payload.get("tool_response")):
        for marker in _RESULT.finditer(text):
            expected = "ingest-review" if verb == "ingest-reviewer" else verb
            if marker.group(1) == expected:
                matches.append(int(marker.group(2)))
        if verb == "decide":
            for marker in _DECIDE.finditer(text):
                if marker.group(1) != finding.group(1):
                    return None
                matches.append(int(marker.group(2)))
        if verb == "status":
            try:
                parsed = json.loads(text)
            except ValueError:
                continue
            if isinstance(parsed, dict) and parsed.get("verdict") in (
                    "clean", "harmful-open", "no-harm-only"
            ) and type(parsed.get("issue")) is int and parsed["issue"] > 0:
                matches.append(parsed["issue"])
    if not matches or len(set(matches)) != 1:
        return None  # Missing/contradictory result: don't guess from active.json.
    issue = matches[0]
    if explicit and int(explicit.group(1)) != issue:
        return None
    return issue
