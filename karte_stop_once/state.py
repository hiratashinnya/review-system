"""Session-local one-shot latch, protected against parallel PreToolUse calls."""
from pathlib import Path

from .store import locked, state_file

DENIALS_PER_EVENT = 1  # Increase only after measured non-compliance.
_QUESTION_TOOL = "AskUserQuestion"
_TODO_TOOLS = {"TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet"}


def _events(data: dict) -> dict:
    """Keep one independent STOP history per Issue within a session."""
    if "digest" in data:  # Migrate existing one-Issue trial state.
        previous = data.copy()
        data.clear()
        data.update(events={str(previous["issue"]): previous}, active_issue=str(previous["issue"]))
    events = data.setdefault("events", {})
    if not isinstance(events, dict) or not all(_valid_event(v) for v in events.values()):
        raise ValueError("invalid one-shot state")
    return events


def _valid_event(event) -> bool:
    return (isinstance(event, dict) and isinstance(event.get("digest"), str)
            and type(event.get("denied")) is int and event["denied"] >= 0
            and isinstance(event.get("followup_tools"), list)
            and type(event.get("issue")) is int and _valid_reasons(event.get("reasons")))


def _valid_reasons(reasons) -> bool:
    return isinstance(reasons, list) and all(
        isinstance(r, (list, tuple)) and len(r) == 2 and isinstance(r[0], str)
        and isinstance(r[1], list) for r in reasons)


def arm(root: Path, session: str, issue: int, read_event) -> bool:
    """Run read_event() under the state lock so a stale reading cannot overwrite a newer arm."""
    path = state_file(root, session)
    if path is None:
        return False
    with locked(path, create=True) as data:
        event = read_event()
        events = _events(data)
        key = str(issue)
        if event is None:
            events.pop(key, None)
            if data.get("active_issue") == key:
                data["active_issue"] = next(reversed(events), None)
            return False
        previous = events.get(key)
        data["active_issue"] = key
        if previous and previous.get("digest") == event["digest"]:
            return False
        events[key] = {**event, "denied": 0, "followup_tools": []}
        return True


def attempt(root: Path, session: str, tool: str) -> dict | None:
    path = state_file(root, session)
    if path is None or not path.is_file():
        return None
    with locked(path, create=False) as data:
        if data is None:
            return None
        event = _events(data).get(data.get("active_issue"))
        if not event or "digest" not in event:
            return None
        if tool == _QUESTION_TOOL:
            event["denied"] = DENIALS_PER_EVENT  # Asking the owner uses up this event's denial.
            return None
        if tool in _TODO_TOOLS:
            return None  # Allowed; the denial stays available for the next inappropriate tool.
        if event["denied"] < DENIALS_PER_EVENT:
            event["denied"] += 1
            return event.copy()
        if len(event["followup_tools"]) < 8:
            event["followup_tools"].append(tool)
    return None
