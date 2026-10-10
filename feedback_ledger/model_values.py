"""TOML parsing and canonical value normalization primitives."""

from __future__ import annotations

import datetime
import tomllib

from .model_errors import DocumentError

def parse_toml(text: str) -> dict:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise DocumentError(f"TOML として読めない: {exc}") from exc


def normalize_line(value: str) -> str:
    return value.strip()


def normalize_text(value: str) -> str:
    body = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in body.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    while lines and lines[0] == "":
        lines.pop(0)
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def normalize_strlist(value) -> list[str]:
    return sorted({item.strip() for item in value if str(item).strip()})


def _is_plain_date(value) -> bool:
    return isinstance(value, datetime.date) and not isinstance(value, datetime.datetime)
