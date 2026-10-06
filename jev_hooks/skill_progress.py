"""Only the latest paired successful attempt certifies its snapshot and contract."""
import hashlib
import json
from .fingerprints import contract_fingerprint, fingerprint, successful
from .skill_semantics import related


def update_progress(definition, event, state, progress, root, evidence, evaluator, observations, threshold=.9):
    latest = state.setdefault("latest_attempts", {}).setdefault(definition["id"], {})
    for step in definition["steps"]:
        key = step["id"]
        current = {"fingerprint": fingerprint(root, step.get("watch", [])),
                   "contract": contract_fingerprint(step)}
        if key in progress and any(progress[key].get(field) != value for field, value in current.items()):
            del progress[key]
        identifier = event.get("tool_use_id")
        pending = state.setdefault("pending", {})
        attempt = definition["id"] + ":" + str(identifier) + ":" + key
        call_hash = hashlib.sha256(json.dumps([event.get("tool_name"), event.get("tool_input", {})],
                                             sort_keys=True).encode()).hexdigest()
        snapshot = dict(current, call=call_hash)
        if event["hook_event_name"] == "PreToolUse" and identifier and related(
                step["evidence"], event, definition, evidence, evaluator, observations, "step", threshold):
            progress.pop(key, None)
            latest[key] = identifier
            pending.setdefault(attempt, snapshot)
        if event["hook_event_name"] == "PostToolUseFailure" and identifier:
            pending.pop(attempt, None)
        if event["hook_event_name"] != "PostToolUse" or not identifier:
            continue
        before = pending.pop(attempt, None)
        if latest.get(key) == identifier and before == snapshot and successful(state["results"].get(identifier, {})):
            progress[key] = dict(current, tool_use_id=identifier)
