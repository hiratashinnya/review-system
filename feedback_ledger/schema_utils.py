"""Small helpers for schema consumers."""

from __future__ import annotations

from .schema_types import DocSpec
from .schema_values import OVERRIDDEN_ROLES, OVERRIDDEN_ROLE_SKILL_RE

def filename_for(spec: DocSpec, document_id: str) -> str:
    return f"{document_id}.toml"


def valid_overridden_role(value: str) -> bool:
    return value in OVERRIDDEN_ROLES or bool(OVERRIDDEN_ROLE_SKILL_RE.match(value))
