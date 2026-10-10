"""Shared CLI output, status codes, and argument conversion."""

from __future__ import annotations

import argparse
import datetime
import sys

from . import schema as schema_module
from .model import ERROR, Finding

EXIT_OK = 0
EXIT_NOT_FOUND = 2
EXIT_ERROR = 4
TRIAGE_DRAFT_TEMPLATE_VERDICT = "need-more-evidence"

def _parse_date(value: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        pass
    try:
        return datetime.datetime.fromisoformat(value).date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"ISO 8601 の日付/日時として読めない: {value!r}"
        ) from exc


def _print(findings, stream=None) -> None:
    handle = stream or sys.stdout
    for finding in findings:
        print(finding.render(), file=handle)


def _errors(findings) -> list[Finding]:
    return [finding for finding in findings if finding.level == ERROR]


def _fail(findings) -> int:
    _print(findings, stream=sys.stderr)
    return EXIT_ERROR


def _require_proposal(store, proposal_id):
    document = store.by_id(schema_module.PROPOSAL, proposal_id)
    if document is None:
        print(f"ERROR: 改訂案が見つからない: {proposal_id}", file=sys.stderr)
        return None
    return document
