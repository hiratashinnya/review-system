"""Version rules for feedback-ledger entries."""

from __future__ import annotations

import re

LEDGER_SCHEMA_MAJOR = 1
LEDGER_CURRENT_MINOR = 1
LEDGER_SCHEMA_PREFIX = f"feedback-ledger/v{LEDGER_SCHEMA_MAJOR}"
LEDGER_CURRENT_SCHEMA = f"{LEDGER_SCHEMA_PREFIX}.{LEDGER_CURRENT_MINOR}"
LEDGER_THEME_INTRODUCED_MINOR = {
    "目的・評価": 1,
    "開発工程": 1,
    "実行体制": 1,
    "品質原則": 1,
    "検証・追跡": 1,
    "AI判定": 1,
    "記録管理": 1,
}
LEDGER_THEME_MINOR = min(LEDGER_THEME_INTRODUCED_MINOR.values())
LEDGER_SCHEMA_PATTERN = re.compile(
    rf"^{LEDGER_SCHEMA_PREFIX}(?:\.(?:0|[1-9][0-9]*))?$"
)


def parse_ledger_schema(value: object) -> tuple[int, int] | None:
    """Return the explicit major/minor, treating a bare major as minor zero."""
    if not isinstance(value, str) or not LEDGER_SCHEMA_PATTERN.fullmatch(value):
        return None
    version = value.rsplit("/v", 1)[1]
    parts = version.split(".")
    return int(parts[0]), int(parts[1]) if len(parts) == 2 else 0


def is_legacy_ledger_without_theme(value: object) -> bool:
    """Whether a supported pre-theme ledger version may omit ``theme``."""
    version = parse_ledger_schema(value)
    return (
        version is not None
        and version[0] == LEDGER_SCHEMA_MAJOR
        and version[1] < LEDGER_THEME_MINOR
    )


def theme_is_available(value: object, theme: object) -> bool:
    """Whether a theme value was introduced by the entry's minor version."""
    version = parse_ledger_schema(value)
    introduced = LEDGER_THEME_INTRODUCED_MINOR.get(theme)
    return (
        version is not None
        and version[0] == LEDGER_SCHEMA_MAJOR
        and introduced is not None
        and version[1] >= introduced
    )
