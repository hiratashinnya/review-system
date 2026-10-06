"""Independent Skill inspection schema; completion requires observed success."""
import json
from pathlib import Path
from .fingerprints import matches
from .skill_progress import update_progress
from .skill_semantics import applicable, related


def inspect_skills(event, state, config, evidence=None, evaluator=None, observations=None):
    evidence, observations = evidence or {}, observations if observations is not None else []
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
        semantic_allowed = applicable(definition, evidence, evaluator, observations, config["confidence_threshold"])
        semantic_evaluator = evaluator if semantic_allowed else None
        update_progress(definition, event, state, progress, root, evidence, semantic_evaluator, observations, config["confidence_threshold"])
        operation = next((op for op in definition["operations"] if related(
            op, event, definition, evidence, semantic_evaluator, observations, "operation", config["confidence_threshold"])), None) if event["hook_event_name"] == "PreToolUse" else None
        recoveries = definition.get("recovery", []) + [s["evidence"] for s in definition["steps"]]
        recovery = any(not op.get("semantic") and matches(op, event.get("tool_name"), event.get("tool_input", {}))
                       for op in recoveries)
        if operation and not recovery:
            for op in recoveries:
                related(op, event, definition, evidence, evaluator, observations, "recovery", config["confidence_threshold"])
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
