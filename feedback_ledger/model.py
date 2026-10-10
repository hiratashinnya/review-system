"""Compatibility API for feedback document normalization and validation."""

from __future__ import annotations

from . import schema as schema_module
from .allowlist import is_allowlisted
from .model_constants import (
    ASSERTION_TERMS, ERROR, INFERRED_MARKER, SPECULATION_TERMS, WARN,
)
from .model_errors import DocumentError
from .model_field import _normalize_field
from .model_identity import _check_document_identity
from .model_narrative import _lint_narrative
from .model_normalize import normalize_document
from .model_subtable import _normalize_subtable
from .model_types import Finding
from .model_values import (
    _is_plain_date, normalize_line, normalize_strlist, normalize_text, parse_toml,
)
from .schema_types import DocSpec, Field
from .slugify_ref import SlugifyReferenceError, slugify_topic
from .tomlwrite import DATE, INT, LINE, OPTDATE, STRLIST, TEXT


def check_document_identity(spec: DocSpec, data: dict, locus: str) -> list[Finding]:
    return _check_document_identity(spec, data, locus, slugify_topic)
