"""Select bounded public evidence and omit sensitive file and shell output."""
from .redaction import redact, redact_text
from .outbound_inputs import project_input, sensitive_input, shell_tool
from .outbound_context import project_context

PUBLIC_FIELDS = {"user_request", "public_messages", "last_assistant_message",
                 "current_tool_input", "research_tools", "history_complete", "hook_event_name",
                 "current_turn_tool_ids", "executed_question_ids", "skill_context"}


def bounded(value, depth=0):
    if depth > 12:
        return "[OMITTED]"
    if isinstance(value, str):
        return value[:8000] + ("[TRUNCATED]" if len(value) > 8000 else "")
    if isinstance(value, dict):
        return {key: bounded(item, depth + 1) for key, item in list(value.items())[:64]}
    if isinstance(value, list):
        return [bounded(item, depth + 1) for item in value[-64:]]
    return value


def outbound_evidence(evidence, secrets):
    selected = {key: redact(value, secrets) for key, value in evidence.items() if key in PUBLIC_FIELDS}
    if "current_tool_input" in evidence:
        selected["current_tool_input"] = project_input(evidence["current_tool_input"], secrets)
    if "skill_context" in evidence:
        selected["skill_context"] = project_context(evidence["skill_context"], secrets)
    calls, results = {}, {}
    identifiers = evidence.get("current_turn_tool_ids")
    for identifier, call in evidence.get("tool_calls", {}).items():
        if not isinstance(identifier, str) or redact_text(identifier, secrets) != identifier:
            continue
        if identifiers is not None and identifier not in identifiers:
            continue
        name, inputs = call.get("name", ""), call.get("input", {})
        sensitive, shell = sensitive_input(inputs), shell_tool(name)
        calls[identifier] = {"name": redact_text(name, secrets), "input": project_input(inputs, secrets, name)}
        result = evidence.get("tool_results", {}).get(identifier)
        if isinstance(result, dict):
            results[identifier] = {"is_error": bool(result.get("is_error"))}
            if sensitive or shell:
                results[identifier]["content"] = "[OMITTED: sensitive file or shell output]"
            else:
                results[identifier]["content"] = redact(result.get("content"), secrets)
    selected.update(tool_calls=calls, tool_results=results)
    if not evidence.get("tool_calls") and not evidence.get("tool_results"):
        selected = {key: value for key, value in selected.items() if key not in {"tool_calls", "tool_results"}}
    return bounded(selected)


def outbound_questions(questions, secrets):
    return {identifier: {"type": spec.get("type"),
                        "instructions": redact_text(spec.get("instructions", ""), secrets),
                        "criteria": {choice: redact_text(text, secrets)
                                     for choice, text in spec.get("criteria", {}).items()}}
            for identifier, spec in questions.items()}
