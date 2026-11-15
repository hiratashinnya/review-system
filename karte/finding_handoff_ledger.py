"""台帳の finding ブロックと申し送り記録の変換。"""

from .finding_handoff_keys import HANDOFF_KEYS
from .finding_handoff_record import HandoffRecord
from .value_codec import format_value


def record_from_block(block) -> HandoffRecord | None:
    values = {key: block.fields.get(key, "") for key in HANDOFF_KEYS}
    values = {key: value.strip() if isinstance(value, str) else "" for key, value in values.items()}
    return HandoffRecord(**values) if any(values.values()) else None


def emit_lines(record: HandoffRecord) -> list[str]:
    return [f"{key}: {format_value(getattr(record, key))}" for key in HANDOFF_KEYS]
