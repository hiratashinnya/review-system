"""Regression tests for supported ledger schema versions and CLI failures."""

import io
import unittest
from contextlib import redirect_stderr

from feedback_ledger.cli import EXIT_ERROR
from feedback_ledger.model import ERROR, check_document_identity, normalize_document
from feedback_ledger.schema import LEDGER_SPEC
from feedback_ledger.schema_version import (
    LEDGER_CURRENT_SCHEMA, LEDGER_SCHEMA_PATTERN, parse_ledger_schema,
)
from test_feedback_ledger import ENTRY_ID, FeedbackLedgerTestCase, ledger_data


class LedgerVersionReviewTests(FeedbackLedgerTestCase):
    def test_new_entry_rejects_legacy_future_and_overlong_versions(self):
        versions = (
            "feedback-ledger/v1", "feedback-ledger/v1.0", "feedback-ledger/v1.7",
            "feedback-ledger/v1." + "9" * 5000,
        )
        for version in versions:
            with self.subTest(version=version[:40]):
                draft = self.write_draft(LEDGER_SPEC, ledger_data(schema=version))
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    code, _ = self.run_cli("new-entry", "--from", draft)
                self.assertEqual(code, EXIT_ERROR)
                self.assertIn(f"schema を {LEDGER_CURRENT_SCHEMA} に直してください", stderr.getvalue())
                self.assertFalse(self.stored("ledger", ENTRY_ID).exists())

    def test_parser_rejects_future_and_overlong_minor_without_conversion_error(self):
        for version in ("feedback-ledger/v1.7", "feedback-ledger/v1." + "9" * 5000):
            with self.subTest(length=len(version)):
                self.assertIsNone(parse_ledger_schema(version))
                self.assertFalse(LEDGER_SCHEMA_PATTERN.fullmatch(version))

    def test_existing_supported_ledger_versions_remain_valid(self):
        for version in ("feedback-ledger/v1", "feedback-ledger/v1.0", LEDGER_CURRENT_SCHEMA):
            data = ledger_data(schema=version)
            if version != LEDGER_CURRENT_SCHEMA:
                data.pop("theme")
            normalized, findings = normalize_document(LEDGER_SPEC, data, "entry.toml")
            if normalized is not None:
                findings.extend(check_document_identity(LEDGER_SPEC, normalized, "entry.toml"))
            with self.subTest(version=version):
                self.assertIsNotNone(normalized)
                self.assertFalse([item for item in findings if item.level == ERROR])


if __name__ == "__main__":
    unittest.main()
