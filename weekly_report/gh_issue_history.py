"""Verify ordering and map the terminal close to the Issue's effective timestamp."""

from datetime import timedelta

CLOSE_REASONS = ("completed", "not_planned", "duplicate")
TRANSITIONS = ("closed", "reopened")
CLOSE_EVENT_DELAY = timedelta(seconds=2)


def verified_events(issue, rows):
    transitions = sorted((row for row in rows if row["event"] in TRANSITIONS),
                         key=lambda row: (row["created_at"], row["id"]))
    tail = transitions[-1] if transitions else None
    terminal_close = issue["state"] == "closed"
    if terminal_close and not _has_terminal_close(issue, transitions):
        return None
    if not terminal_close and (issue["closed_at"] is not None or (tail and tail["event"] != "reopened")):
        return None
    expected, previous_time = "closed", issue["created_at"]
    result = []
    for row in transitions:
        linked_close = terminal_close and row is tail
        effective = issue["closed_at"] if linked_close else row["created_at"]
        if row["event"] != expected or not previous_time <= effective <= issue["updated_at"]:
            return None
        result.append(_with_reason(issue, row, effective, linked_close))
        expected = "reopened" if expected == "closed" else "closed"
        previous_time = effective
    return result


def _has_terminal_close(issue, rows):
    """Allow a bounded write delay for an unambiguous terminal closed event."""
    closed_at = issue["closed_at"]
    if not rows or rows[-1]["event"] != "closed" or closed_at is None:
        return False
    matching = [row for row in rows if row["event"] == "closed"
                and timedelta(0) <= row["created_at"] - closed_at <= CLOSE_EVENT_DELAY]
    return len(matching) == 1 and matching[0] is rows[-1]


def _with_reason(issue, event, effective, linked_close):
    reason, source = None, None
    if event["event"] == "closed":
        if event["state_reason"] in CLOSE_REASONS:
            reason, source = event["state_reason"], "issue_event"
        elif linked_close and issue["state_reason"] in CLOSE_REASONS:
            reason, source = issue["state_reason"], "latest_issue_at_same_close"
    return {**event, "number": issue["number"], "title": issue["title"], "state_reason": reason,
            "reason_source": source, "effective_at": effective,
            "effective_source": "issue.closed_at" if linked_close else "issue_event.created_at"}


def event_time(event):
    return event.get("effective_at", event["created_at"])
