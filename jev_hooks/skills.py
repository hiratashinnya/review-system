"""Independent Skill inspection schema; completion requires observed success."""
import json
from pathlib import Path
from .fingerprints import fingerprint, matches, successful


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
    for step in definition["steps"]:
        key, patterns = step["id"], step.get("watch", [])
        current = fingerprint(root, patterns)
        if key in progress and progress[key]["fingerprint"] != current:
            del progress[key]
        identifier = event.get("tool_use_id")
        pending = state.setdefault("pending", {})
        if event["hook_event_name"] == "PreToolUse" and identifier and matches(
                step["evidence"], event.get("tool_name"), event.get("tool_input", {})):
            progress.pop(key, None)
            pending.setdefault(definition["id"] + ":" + identifier + ":" + key, current)
        if event["hook_event_name"] == "PostToolUseFailure" and identifier:
            pending.pop(definition["id"] + ":" + identifier + ":" + key, None)
        # Only newly observed post-success can certify this exact code snapshot.
        if event["hook_event_name"] != "PostToolUse" or not identifier:
            continue
        call = state["calls"].get(identifier, {})
        if matches(step["evidence"], call.get("name"), call.get("input", {})) and successful(
                state["results"].get(identifier, {})):
            if pending.pop(definition["id"] + ":" + identifier + ":" + key, None) != current:
                continue
            progress[key] = {"fingerprint": current, "tool_use_id": identifier}
