"""Construct bounded metadata notices and rule outcomes without retaining content."""
import math
import os
import re
import uuid
from .questions import QUESTIONS, QUESTION_VERSION
from .policy import RULE_VERSION
from .redaction import known_secrets, redact_text

FAULTS = {"timeout", "evaluation_error", "invalid_response", "uncertain", "insufficient_evidence",
          "evaluator_failure", "missing_api_key"}
EVENTS = {"PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop"}


def summarize_answers(observations, threshold):
    summaries = []
    for question, answer in observations:
        if question not in QUESTIONS:
            continue
        value, confidence = answer.get("value"), answer.get("confidence")
        if type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            confidence = 0
        fault = answer.get("fault") if answer.get("fault") in FAULTS else None
        low = confidence < threshold
        summaries.append({"question": question, "rule": question[:2].upper(),
            "value": value if type(value) is bool and not fault and not low else None,
            "confidence": confidence, "fault": fault, "low_confidence": low})
    return summaries


def record(event, evidence, observations, found, state, config, fault, elapsed, request_id, statuses, denied, model):
    secrets = known_secrets(config, os.environ.get(config["api_key_env"], ""))
    model = redact_text(model, secrets) if isinstance(model, str) else "unknown"
    model = model if re.fullmatch(r"mock|jev-[0-9]+\.[0-9]+\.[0-9]+", model) else "unknown"
    answers = summarize_answers(observations, config["confidence_threshold"])
    evaluated = {answer["rule"] for answer in answers}
    if "active" in statuses.values():
        evaluated.add("R4")
    outcomes, notices = {}, []
    for rule in sorted(evaluated):
        relevant = [answer for answer in answers if answer["rule"] == rule]
        outcomes[rule] = {"candidate": rule in found, "denied": rule in state.get("denied_rules", []),
            "unknown": any(a["value"] is None for a in relevant),
            "fault": bool(fault) or any(a["fault"] in FAULTS - {"uncertain", "insufficient_evidence"} for a in relevant)}
    for answer in answers:
        if answer["value"] is None:
            technical = answer["fault"] in FAULTS - {"uncertain", "insufficient_evidence"}
            notices.append({"kind": "api_failure" if technical else ("low_confidence" if answer["low_confidence"] else "unknown"),
                            "rule": answer["rule"], "question": answer["question"], "fault": answer["fault"]})
    if fault:
        notices.append({"kind": fault if fault in FAULTS else "evaluator_failure"})
    return {"schema_version": 1, "record_id": uuid.uuid4().hex, "request_id": request_id or uuid.uuid4().hex,
        "event": event.get("hook_event_name") if event.get("hook_event_name") in EVENTS else "unknown",
        "question_version": QUESTION_VERSION, "rule_version": RULE_VERSION, "model": model, "mode": config["mode"], "latency_ms": elapsed,
        "fault": fault if fault in FAULTS else None, "answers": answers, "outcomes": outcomes,
        "rules": sorted(found), "denied": denied,
        "skills": {status: list(statuses.values()).count(status) for status in {"active", "unknown"}},
        "history_complete": bool(evidence.get("history_complete")),
        "notices": notices, "notice_delivery": "not_connected"}
