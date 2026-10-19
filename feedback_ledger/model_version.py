"""Version-specific ledger schema and vocabulary validation."""

from .model_constants import ERROR
from .model_types import Finding
from .schema_version import (
    LEDGER_POLICY_MINOR, LEDGER_SCHEMA_MAJOR, LEDGER_THEME_INTRODUCED_MINOR,
    parse_ledger_schema, theme_is_available,
)


def check_ledger_version(data: dict, locus: str, schema_prefix: str) -> list[Finding]:
    findings = []
    schema = data.get("schema")
    version = parse_ledger_schema(schema)
    if version is None or version[0] != LEDGER_SCHEMA_MAJOR:
        return [Finding(
            "L1", ERROR, f"{locus}::schema",
            f"schema は {schema_prefix} または同 major の minor でなければならない: {schema!r}",
        )]
    if (
        data.get("theme") in LEDGER_THEME_INTRODUCED_MINOR
        and not theme_is_available(schema, data["theme"])
    ):
        findings.append(Finding(
            "L1", ERROR, f"{locus}::theme",
            f"theme は schema {schema!r} では使用できない",
        ))
    for field, introduced_values in (
        ("decision_point", ("policy",)), ("divergence", ("approval",)),
    ):
        if data.get(field) in introduced_values and version[1] < LEDGER_POLICY_MINOR:
            findings.append(Finding(
                "L1", ERROR, f"{locus}::{field}",
                f"{field} の値 {data[field]!r} は schema {schema!r} では使用できない",
            ))
    return findings
