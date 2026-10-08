"""Parse public Claude JSONL messages without treating thinking as speech."""
import json
from pathlib import Path


def read_transcript(path):
    if not path:
        return [], False
    try:
        lines = Path(path).read_text().splitlines()
    except (OSError, UnicodeError):
        return [], False
    records, complete = [], True
    for line in lines:
        try:
            records.append(json.loads(line))
        except (ValueError, TypeError):
            complete = False
    return records, complete


def normalize(records):
    public, calls, results = [], {}, {}
    for record in records:
        message = record.get("message", {})
        role = message.get("role", record.get("type"))
        content = message.get("content", [])
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        if role == "user" and any(item.get("type") == "text" for item in content):
            public = []
        for block in content:
            kind = block.get("type")
            if role == "assistant" and kind == "text":
                public.append(block.get("text", ""))
            if role == "assistant" and kind == "tool_use" and block.get("id"):
                calls[block["id"]] = {"name": block.get("name"), "input": block.get("input", {})}
            if role == "user" and kind == "tool_result" and block.get("tool_use_id"):
                results[block["tool_use_id"]] = {
                    "content": block.get("content"), "is_error": block.get("is_error", False)}
    return public, calls, results
