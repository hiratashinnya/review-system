"""Combine delayed transcripts with the current authoritative hook event."""
import hashlib
import json
from .transcript import normalize, read_transcript


def collect(event, state, config):
    records, complete = read_transcript(event.get("transcript_path"))
    if any(r.get("type") == "summary" or r.get("subtype") == "compact_boundary"
           or r.get("isCompactSummary") for r in records):
        complete = False
    current_ids, turn_key, user_request = [], None, []
    for index, record in enumerate(records):
        message = record.get("message", {})
        blocks = message.get("content", [])
        if isinstance(blocks, str):
            blocks = [{"type": "text", "text": blocks}]
        if message.get("role") == "user" and any(b.get("type") == "text" for b in blocks):
            current_ids = []
            user_request = [b.get("text", "") for b in blocks if b.get("type") == "text"]
            turn_key = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
        current_ids.extend(b.get("id") for b in blocks if b.get("type") == "tool_use")
        if event.get("hook_event_name") == "PreToolUse" and any(
                b.get("id") == event.get("tool_use_id") and b.get("type") == "tool_use" for b in blocks):
            end = next(i for i, b in enumerate(blocks) if b.get("id") == event.get("tool_use_id"))
            record = dict(record, message=dict(message, content=blocks[:end + 1]))
            records = records[:index] + [record]
            break
    if turn_key and turn_key != state.get("turn_key"):
        state["turn_key"], state["blocks"], state["question_cancelled"] = turn_key, {}, False
    public, calls, results = normalize(records)
    state["calls"].update(calls)
    state["results"].update(results)
    name, identifier = event.get("tool_name"), event.get("tool_use_id")
    kind = event.get("hook_event_name")
    if identifier and name:
        if identifier not in current_ids:
            current_ids.append(identifier)
        state["calls"][identifier] = {"name": name, "input": event.get("tool_input", {})}
    if identifier and kind in {"PostToolUse", "PostToolUseFailure"}:
        state["results"][identifier] = {"content": event.get("tool_response"),
            "is_error": kind == "PostToolUseFailure", "error": bool(event.get("error"))}
    # A matching pending call establishes that all pre-question public speech was read.
    current_visible = identifier in calls if identifier else any(
        call == {"name": name, "input": event.get("tool_input", {})} for call in calls.values())
    last = event.get("last_assistant_message")
    if kind == "Stop":
        current_visible = bool(public and last == public[-1] and turn_key)
    if kind == "Stop" and isinstance(last, str):
        if not public or public[-1] != last:
            public.append(last)
    return {"user_request": user_request, "current_turn_tool_ids": current_ids, "public_messages": public, "last_assistant_message": last,
        "executed_question_ids": [i for i in current_ids if i in state["results"]
            and not state["results"][i].get("is_error") and state["results"][i].get("content")],
        "tool_calls": state["calls"], "tool_results": state["results"],
        "current_tool_input": event.get("tool_input", {}),
        "research_tools": config["research_tools"],
        "history_complete": complete and current_visible,
        "hook_event_name": kind}


def question_cancelled(evidence):
    for identifier, result in evidence["tool_results"].items():
        if identifier not in evidence.get("current_turn_tool_ids", []) and identifier != "cancelled":
            continue
        call = evidence["tool_calls"].get(identifier, {})
        content = result.get("content")
        if call.get("name") == "AskUserQuestion" and (
            result.get("is_error") or isinstance(content, dict) and content.get("cancelled")):
            return True
    return False
