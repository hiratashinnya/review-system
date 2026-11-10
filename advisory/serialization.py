"""Deterministic TOML writer; verify by round-tripping through tomllib."""

import json
import tomllib

from .record_fields import EVENT_FIELDS, FIELDS


def encode(value: object) -> str:
    if type(value) is str:
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("TOML strings require Unicode scalar values")
        return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007f")
    if type(value) is int and value >= 0:
        return str(value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "[" + ", ".join(encode(item) for item in value) + "]"
    raise ValueError("unsupported canonical TOML value")


def render(record: dict) -> str:
    lines = [f"{key} = {encode(record[key])}" for key in FIELDS if key != "history"]
    for event in record["history"]:
        lines.extend(["", "[[history]]"])
        lines.extend(f"{key} = {encode(event[key])}" for key in EVENT_FIELDS)
    text = "\n".join(lines) + "\n"
    if tomllib.loads(text) != record:
        raise ValueError("TOML round-trip mismatch")
    return text
