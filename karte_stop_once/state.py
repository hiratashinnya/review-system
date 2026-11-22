"""Session-local one-shot latch, protected against parallel PreToolUse calls."""
import fcntl
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path

DENIALS_PER_EVENT = 1  # Increase only after measured non-compliance.
_SESSION = re.compile(r"[A-Za-z0-9_-]{8,128}\Z", re.ASCII)
_SAFE_TOOLS = {"AskUserQuestion", "TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet"}


def _file(root: Path, session: str) -> Path | None:
    if not isinstance(session, str) or not _SESSION.fullmatch(session):
        return None
    name = hashlib.sha256(session.encode("ascii")).hexdigest()
    return root / "tmp" / "_karte" / "stop-once" / (name + ".json")


@contextmanager
def _locked(path: Path, create: bool):
    if not path.parent.is_dir():
        if not create:
            yield None
            return
        path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path) + ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if not isinstance(value, dict):
            raise ValueError("invalid one-shot state")
        yield value
        temp = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                             prefix=".stop-", delete=False) as stream:
                temp = stream.name
                json.dump(value, stream, ensure_ascii=False)
            os.replace(temp, path)
        finally:
            if temp is not None and os.path.exists(temp):
                os.unlink(temp)
    finally:
        os.close(fd)


def _events(data: dict) -> dict:
    """Keep one independent STOP history per Issue within a session."""
    if "digest" in data:  # Migrate existing one-Issue trial state.
        previous = data.copy()
        data.clear()
        data.update(events={str(previous["issue"]): previous}, active_issue=str(previous["issue"]))
    return data.setdefault("events", {})


def arm(root: Path, session: str, issue: int, event: dict | None) -> bool:
    path = _file(root, session)
    if path is None:
        return False
    with _locked(path, create=event is not None) as data:
        if data is None:
            return False
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
    path = _file(root, session)
    if path is None or not path.is_file():
        return None
    with _locked(path, create=False) as data:
        if data is None:
            return None
        event = _events(data).get(data.get("active_issue"))
        if not event or "digest" not in event:
            return None
        if tool in _SAFE_TOOLS:
            event["denied"] = DENIALS_PER_EVENT  # Correct next step; no denial.
            return None
        if event["denied"] < DENIALS_PER_EVENT:
            event["denied"] += 1
            return event.copy()
        if len(event["followup_tools"]) < 8:
            event["followup_tools"].append(tool)
    return None
