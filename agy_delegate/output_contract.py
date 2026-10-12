"""agy 1.3.3 の成功・拒否・timeout・ERROR 実測に基づく出力契約。"""

import math

REQUIRED = {"status", "conversation_id", "response", "duration_seconds", "num_turns", "usage"}
OPTIONAL = {"denied_actions", "error"}
TOKENS = {"input_tokens", "output_tokens", "thinking_tokens", "cache_read_tokens", "total_tokens"}


def contract_reasons(data: dict) -> list[str]:
    """未実測キーを拒否し、数値の算術関係は推測しない。"""
    reasons = []
    for name in ("status", "conversation_id", "response"):
        if not isinstance(data.get(name), str):
            reasons.append(f"field_invalid:{name}")
    duration = data.get("duration_seconds")
    if (type(duration) not in (int, float) or duration < 0
            or (isinstance(duration, float) and not math.isfinite(duration))):
        reasons.append("field_invalid:duration_seconds")
    if not _nonnegative_integer(data.get("num_turns")):
        reasons.append("field_invalid:num_turns")
    usage = data.get("usage")
    if (not isinstance(usage, dict) or set(usage) != TOKENS
            or not all(_nonnegative_integer(value) for value in usage.values())):
        reasons.append("field_invalid:usage")
    if "denied_actions" in data and not _valid_denials(data["denied_actions"]):
        reasons.append("field_invalid:denied_actions")
    if "error" in data and not isinstance(data["error"], str):
        reasons.append("field_invalid:error")
    if not set(data) <= REQUIRED | OPTIONAL:
        reasons.append("unknown_output_fields")
    return reasons


def _nonnegative_integer(value: object) -> bool:
    return type(value) is int and value >= 0


def _valid_denials(value: object) -> bool:
    return (isinstance(value, list) and all(
        isinstance(item, dict) and set(item) == {"action", "display_name"}
        and all(isinstance(text, str) and bool(text) for text in item.values())
        for item in value))
