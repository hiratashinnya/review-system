"""Coordinate a single event transaction and retain only non-content metadata."""
import time
import hashlib
import json
from pathlib import Path
from .replay import replay_key
from .evidence import collect, question_cancelled
from .policy import decide, questions, violations
from .skills import inspect_skills
from .state import session_state
from .configuration_failure import ConfigurationFault, configuration_failure, fault_decision
from .audit_records import record


def run_event(event, config, evaluator):
    started = time.monotonic()
    session = event.get("session_id")
    if not session or not isinstance(session, str):
        return {}
    root = str(Path(event.get("cwd", ".")).resolve())
    scope = root + "\0" + session
    with session_state(config["state_dir"], scope, config["audit_retention"]) as (state, audit):
        key_decision, key_fault = configuration_failure(event, config)
        replay = replay_key(event, config)
        if replay and key_fault:
            replay += ":" + key_fault
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
        observations = []
        missing, statuses = inspect_skills(event, state, config, evidence,
                                          None if key_fault else evaluator, observations)
        if replay and event.get("hook_event_name") == "Stop":
            progress = json.dumps([state.get("skills"), state.get("active_skills"),
                                   state.get("question_cancelled"), state.get("turn_key")], sort_keys=True)
            replay += hashlib.sha256(progress.encode()).hexdigest()
            if replay in state["replays"]:
                return state["replays"][replay]
        fault = key_fault
        try:
            identifiers = questions(event, evidence)
            answers = {} if key_fault else evaluator.evaluate(evidence, identifiers)
            observations.extend((key, answers.get(key, {"value": None, "confidence": 0, "fault": fault}))
                                for key in identifiers)
        except ConfigurationFault:
            answers, fault = {}, "missing_api_key"
            key_fault, key_decision = fault, fault_decision(event, config)
        except Exception:
            answers, fault = {}, "evaluator_failure"
            observations.extend((key, {"value": None, "confidence": 0, "fault": fault}) for key in identifiers)
        found = violations(event, evidence, answers, missing, config)
        decision = decide(event, found, state, config)
        if key_fault:
            decision = key_decision
            state["denied_rules"] = []
        # Cache no reason text: all reasons are code-owned constant messages or schema IDs.
        if replay:
            state["replays"][replay] = decision
        audit(record(event, evidence, observations, found, state, config, fault,
            round((time.monotonic()-started)*1000), replay, statuses, bool(decision), getattr(evaluator, "last_model", config["model"])))
        return decision
