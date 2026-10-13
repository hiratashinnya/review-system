"""UTC timestamp parsing and formatting."""

from __future__ import annotations
from datetime import datetime, timezone


def parse_timestamp(text: str) -> datetime:
    """ISO8601 文字列を UTC の aware datetime にする。

    ``2026-08-02`` のような日付のみの指定は ``2026-08-02T00:00:00Z`` として扱う。
    末尾 ``Z`` は :func:`datetime.fromisoformat` の古い実装が扱えないため明示変換する。
    tz 指定が無い入力は UTC とみなす（本ツールの窓定義は常に UTC・上記 docstring）。
    """
    raw = text.strip()
    if not raw:
        raise ValueError("空のタイムスタンプは解釈できない")
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    """UTC の ``YYYY-MM-DDTHH:MM:SSZ`` 表記にする（レポートの時刻表記を1つに固定する）。"""
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
