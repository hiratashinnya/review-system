"""Select bounded public evidence and omit sensitive file and shell output."""
import json
import re
from .redaction import redact, redact_text

PUBLIC_FIELDS = {"user_request", "public_messages", "last_assistant_message",
                 "current_tool_input", "research_tools", "history_complete", "hook_event_name",
                 "current_turn_tool_ids", "executed_question_ids", "skill_context"}
SENSITIVE_FILE = re.compile(
    r"(?i)(?:^|[/\\\s'\"])(?:\.env(?:\.[\w-]+)?|\.envrc|\.ssh|\.aws|\.kube|\.npmrc|\.pypirc|\.netrc|\.git-credentials|"
    r"id_(?:rsa|dsa|ecdsa|ed25519)(?:\.pub)?|terraform\.tfstate|"
    r"credentials(?:\.[\w-]+)?|[^/\\\s'\"]*(?:secret|private[_-]?key)[^/\\\s'\"]*|"
    r"[^/\\\s'\"]+\.(?:pem|key|p12|pfx))(?:$|[/\\\s'\"])"
)
INPUT_FIELDS = {"questions", "query", "pattern", "url", "file_path", "path", "glob"}


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
    calls, results = {}, {}
    identifiers = evidence.get("current_turn_tool_ids")
    for identifier, call in evidence.get("tool_calls", {}).items():
        if not isinstance(identifier, str) or redact_text(identifier, secrets) != identifier:
            continue
        if identifiers is not None and identifier not in identifiers:
            continue
        name, inputs = call.get("name", ""), call.get("input", {})
        sensitive = bool(SENSITIVE_FILE.search(json.dumps(inputs, ensure_ascii=False)))
        shell = any(word in name.lower() for word in ("bash", "shell", "exec", "terminal"))
        inputs = inputs if isinstance(inputs, dict) else {}
        calls[identifier] = {"name": redact_text(name, secrets), "input": "[OMITTED]" if sensitive or shell else
                             {key: redact(value, secrets) for key, value in inputs.items() if key in INPUT_FIELDS}}
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
