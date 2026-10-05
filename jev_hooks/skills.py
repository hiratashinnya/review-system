"""Independent Skill inspection schema; completion requires observed success."""
import json
from pathlib import Path
from .fingerprints import contract_fingerprint, fingerprint, matches, successful


def inspect_skills(event, state, config):
    missing, statuses = [], {}
    root = Path(event.get("cwd", ".")).resolve()
    saved = state.setdefault("skills", {})
    for filename in config["skill_definitions"]:
        definition = json.loads(Path(filename).read_text())
        name = definition["id"]
        skill_path = (root / definition["skill_path"]).resolve()
        if not skill_path.is_relative_to(root) or not skill_path.is_file():
            statuses[name] = "unknown"
            continue
        activated = name in state.setdefault("active_skills", []) or any(call["name"] == "Read" and
            Path(call["input"].get("file_path", "")).resolve() == skill_path and
            identifier in state["results"] and not state["results"][identifier].get("is_error")
            and not state["results"][identifier].get("error")
            and bool(state["results"][identifier].get("content"))
            for identifier, call in state["calls"].items())
        if not activated:
            statuses[name] = "unknown"
            continue
        statuses[name] = "active"
        if name not in state["active_skills"]:
            state["active_skills"].append(name)
        progress = saved.setdefault(name, {})
        _update_progress(definition, event, state, progress, root)
        operation = next((op for op in definition["operations"] if matches(
            op, event.get("tool_name"), event.get("tool_input", {}))), None)
        recovery = any(matches(op, event.get("tool_name"), event.get("tool_input", {}))
            for op in definition.get("recovery", []) + [s["evidence"] for s in definition["steps"]])
        if recovery:
            operation = None
        needed = operation.get("requires", []) if operation else []
        if event["hook_event_name"] == "Stop":
            needed = definition.get("stop_requires", [])
        for step in definition["steps"]:
            if step["id"] not in needed or step.get("kind") == "optional":
                continue
            condition = step.get("when")
            if condition and not (root / condition["path_exists"]).exists():
                continue
            if step["id"] not in progress:
                missing.append(f"{name}:{step['id']}")
    return missing, statuses


def _update_progress(definition, event, state, progress, root):
    latest = state.setdefault("latest_attempts", {}).setdefault(definition["id"], {})
    for step in definition["steps"]:
        key, patterns = step["id"], step.get("watch", [])
        current = {"fingerprint": fingerprint(root, patterns), "contract": contract_fingerprint(step)}
        if key in progress and any(progress[key].get(field) != value for field, value in current.items()):
            del progress[key]
        identifier = event.get("tool_use_id")
        pending = state.setdefault("pending", {})
        attempt = definition["id"] + ":" + str(identifier) + ":" + key
        if event["hook_event_name"] == "PreToolUse" and identifier and matches(
                step["evidence"], event.get("tool_name"), event.get("tool_input", {})):
            progress.pop(key, None)
            latest[key] = identifier
            pending.setdefault(attempt, current)
        if event["hook_event_name"] == "PostToolUseFailure" and identifier:
            pending.pop(attempt, None)
        # Only the latest started attempt can certify this exact snapshot and contract.
        if event["hook_event_name"] != "PostToolUse" or not identifier:
            continue
        before = pending.pop(attempt, None)
        if latest.get(key) != identifier or before != current:
            continue
        call = state["calls"].get(identifier, {})
        if matches(step["evidence"], call.get("name"), call.get("input", {})) and successful(
                state["results"].get(identifier, {})):
            progress[key] = dict(current, tool_use_id=identifier)
