"""Coordinate a single event transaction and retain only non-content metadata."""
import time
import hashlib
import json
from pathlib import Path
from .questions import QUESTION_VERSION
from .replay import replay_key
from .evidence import collect, question_cancelled
from .policy import decide, questions, violations
from .skills import inspect_skills
from .state import session_state


def run_event(event, config, evaluator):
    started = time.monotonic()
    session = event.get("session_id")
    if not session or not isinstance(session, str):
        return {}
    root = str(Path(event.get("cwd", ".")).resolve())
    scope = root + "\0" + session
    with session_state(config["state_dir"], scope) as (state, audit):
        replay = replay_key(event, config)
        if event.get("hook_event_name") != "Stop" and replay and replay in state["replays"]:
            return state["replays"][replay]
        evidence = collect(event, state, config)
        if event.get("tool_name") == "AskUserQuestion" and event.get("hook_event_name") == "PostToolUseFailure":
            state["question_cancelled"] = True
        if question_cancelled(evidence):
            state["question_cancelled"] = True
        if state.get("question_cancelled"):
            evidence["tool_calls"]["cancelled"] = {"name": "AskUserQuestion"}
            evidence["tool_results"]["cancelled"] = {"is_error": True}
        missing, statuses = inspect_skills(event, state, config)
        if replay and event.get("hook_event_name") == "Stop":
            progress = json.dumps([state.get("skills"), state.get("active_skills"),
                                   state.get("question_cancelled"), state.get("turn_key")], sort_keys=True)
            replay += hashlib.sha256(progress.encode()).hexdigest()
            if replay in state["replays"]:
                return state["replays"][replay]
        fault = None
        try:
            answers = evaluator.evaluate(evidence, questions(event, evidence))
        except Exception:
            answers, fault = {}, "evaluator_failure"
        found = violations(event, evidence, answers, missing, config)
        decision = decide(event, found, state, config)
        # Cache no reason text: all reasons are code-owned constant messages or schema IDs.
        if replay:
            state["replays"][replay] = decision
        audit({"event": event.get("hook_event_name"), "rules": list(found),
            "model": getattr(evaluator, "last_model", config["model"]), "rule_version": config["rule_version"],
            "question_version": QUESTION_VERSION, "mode": config["mode"], "latency_ms": round((time.monotonic()-started)*1000),
            "fault": fault, "answers": {key: {"value": value.get("value"),
            "confidence": value.get("confidence"), "fault": value.get("fault") if value.get("fault") in {"timeout", "evaluation_error",
            "invalid_response", "uncertain", "insufficient_evidence"} else None}
            for key, value in answers.items()}, "skills": statuses,
            "denied": bool(decision), "history_complete": evidence["history_complete"]})
        return decision
