"""Content-bound, ordered event chain; not a cryptographic actor signature."""

import hashlib
import json

from .record_fields import CHANGERS, EVENT_FIELDS, MOVES


def digest(value: object) -> str:
    body = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def payload(record: dict) -> dict:
    return {key: value for key, value in record.items() if key != "history"}


def append_event(record: dict, action: str, previous_status: str,
                 actor: str, at: str, reason: str) -> None:
    events = record["history"]
    event = {
        "action": action, "from_status": previous_status,
        "to_status": record["status"], "actor": actor, "at": at,
        "reason": reason, "previous": events[-1]["digest"] if events else "",
        "payload_digest": digest(payload(record)),
    }
    event["digest"] = digest(event)
    events.append(event)


def validate_events(record: dict) -> list[str]:
    events, errors = record.get("history"), []
    if not isinstance(events, list) or not events:
        return ["history must be a nonempty array"]
    if record.get("revision") != len(events):
        errors.append("revision must equal history count")
    previous, state = "", ""
    for index, event in enumerate(events):
        if not isinstance(event, dict) or set(event) != set(EVENT_FIELDS):
            errors.append(f"invalid history fields at {index}")
            continue
        if event["previous"] != previous or event["digest"] != digest({
            key: val for key, val in event.items() if key != "digest"
        }):
            errors.append(f"broken event digest chain at {index}")
        action, source, target = event["action"], event["from_status"], event["to_status"]
        if (action not in CHANGERS or source != state
                or (index == 0 and (action != "create" or target != "open"))
                or (index > 0 and action == "create")):
            errors.append(f"invalid history action at {index}")
        if index > 0 and action in ("amend", "transition", "promote"):
            if (action == "amend" and target != state
                    or action == "transition" and target not in MOVES.get(state, set())
                    or action == "promote" and (state != "triaged" or target != "promoted")):
                errors.append(f"invalid state transition at {index}")
        if event["actor"] != "main-thread" or not event["reason"].strip():
            errors.append(f"invalid actor or reason at {index}")
        previous, state = event["digest"], target
    if state != record.get("status"):
        errors.append("history final state does not match record")
    if events[-1].get("payload_digest") != digest(payload(record)):
        errors.append("record changed without matching final event")
    return errors
