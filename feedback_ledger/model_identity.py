"""Document identity checks for schema constants and derived IDs."""

from __future__ import annotations

import datetime

from . import schema as schema_module
from .model_constants import ERROR
from .model_types import Finding
from .schema_types import DocSpec
from .schema_values import has_unsafe_ledger_slug_character
from .schema_version import (
    LEDGER_SCHEMA_MAJOR, LEDGER_THEME_INTRODUCED_MINOR,
    parse_ledger_schema, theme_is_available,
)
from .slugify_ref import SlugifyReferenceError

def _check_document_identity(spec: DocSpec, data: dict, locus: str, slugify_topic):
    """``schema`` 定数・``id`` 書式・``overridden_role`` 拡張形（L1 の残り）。"""
    findings: list[Finding] = []
    if spec.kind == schema_module.LEDGER:
        version = parse_ledger_schema(data.get("schema"))
        if version is None or version[0] != LEDGER_SCHEMA_MAJOR:
            findings.append(Finding(
                "L1", ERROR, f"{locus}::schema",
                f"schema は {spec.schema_const} または同 major の minor でなければならない: "
                f"{data.get('schema')!r}",
            ))
        elif (
            data.get("theme") in LEDGER_THEME_INTRODUCED_MINOR
            and not theme_is_available(data.get("schema"), data["theme"])
        ):
            findings.append(Finding(
                "L1", ERROR, f"{locus}::theme",
                f"theme は schema {data.get('schema')!r} では使用できない",
            ))
    elif data.get("schema") != spec.schema_const:
        findings.append(Finding(
            "L1", ERROR, f"{locus}::schema",
            f"schema は {spec.schema_const!r} でなければならない: {data.get('schema')!r}",
        ))
    if spec.kind == schema_module.LEDGER:
        role = data.get("overridden_role", "")
        if role and not schema_module.valid_overridden_role(role):
            findings.append(Finding(
                "L1", ERROR, f"{locus}::overridden_role",
                f"語彙外の値: {role!r}"
                f"（許可: {', '.join(schema_module.OVERRIDDEN_ROLES)}, skill:<name>）",
            ))
    if spec.kind in (schema_module.LEDGER, schema_module.PROPOSAL):
        match = spec.id_re.match(data.get("id", ""))
        if match:
            if (
                spec.kind == schema_module.LEDGER
                and has_unsafe_ledger_slug_character(match.group("slug"))
            ):
                findings.append(Finding(
                    "L1", ERROR, f"{locus}::id",
                    "id の slug に制御・書式・サロゲート・私用・未割当文字を含められない",
                ))
            stamp = match.group("date")
            try:
                datetime.date(int(stamp[0:4]), int(stamp[4:6]), int(stamp[6:8]))
            except ValueError:
                findings.append(Finding(
                    "L1", ERROR, f"{locus}::id",
                    f"id の日付部分が実在しない日付: {stamp}",
                ))
    if spec.kind == schema_module.LEDGER:
        topic = data.get("topic", "")
        if isinstance(topic, str) and len(topic) > 30:
            findings.append(Finding(
                "L1", ERROR, f"{locus}::topic",
                f"topic は30字以内でなければならない: {len(topic)}字",
            ))
        occurred_at = data.get("occurred_at")
        if isinstance(occurred_at, datetime.date) and not isinstance(
            occurred_at, datetime.datetime
        ) and isinstance(topic, str):
            try:
                stamp = (
                    f"{occurred_at.year:04d}{occurred_at.month:02d}"
                    f"{occurred_at.day:02d}"
                )
                expected_id = f"FBK-{stamp}-{slugify_topic(topic)}"
            except (SlugifyReferenceError, UnicodeEncodeError) as exc:
                findings.append(Finding(
                    "L1", ERROR, f"{locus}::id",
                    f"slugify を実行できず id を検証できない: {exc}",
                ))
            else:
                if data.get("id") != expected_id:
                    findings.append(Finding(
                        "L1", ERROR, f"{locus}::id",
                        f"topic と occurred_at から導出した id と一致しない"
                        f"（期待: {expected_id}）",
                    ))
    return findings
