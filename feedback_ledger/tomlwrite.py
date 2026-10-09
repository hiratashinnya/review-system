"""Canonical TOML document serializer."""

from __future__ import annotations

from .schema_values import LEDGER
from .schema_version import is_legacy_ledger_without_theme
from .tomlwrite_values import (
    DATE, INT, LINE, OPTDATE, STRLIST, TEXT, VALUE_KINDS, TomlWriteError,
    escape_basic, render_value,
)


def dumps(spec, data: dict) -> str:
    """Serialize fields in schema order, including legacy ledger shape."""
    lines: list[str] = []
    for table in spec.tables:
        if table.name == "":
            for field in table.fields:
                if (
                    spec.kind == LEDGER and field.name == "theme"
                    and field.name not in data
                    and is_legacy_ledger_without_theme(data.get("schema"))
                ):
                    continue
                lines.append(f"{field.name} = {render_value(field.kind, data[field.name])}")
            continue
        if table.repeated:
            if not data[table.name]:
                lines.append(f"{table.name} = []")
                continue
            for item in data[table.name]:
                lines.append("")
                lines.append(f"[[{table.name}]]")
                for field in table.fields:
                    lines.append(f"{field.name} = {render_value(field.kind, item[field.name])}")
            continue
        lines.append("")
        lines.append(f"[{table.name}]")
        for field in table.fields:
            body = data[table.name][field.name]
            lines.append(f"{field.name} = {render_value(field.kind, body)}")
    return "\n".join(lines) + "\n"
