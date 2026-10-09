"""Feedback ledger minor schema compatibility and legacy rendering tests."""

import tomllib
import unittest

from feedback_ledger.cli import EXIT_ERROR, EXIT_OK
from feedback_ledger.model import ERROR, check_document_identity, normalize_document
from feedback_ledger.schema import LEDGER_SPEC
from feedback_ledger.schema_version import LEDGER_CURRENT_SCHEMA
from feedback_ledger.tomlwrite import dumps
from test_feedback_ledger import ENTRY_ID, FeedbackLedgerTestCase, ledger_data


class LedgerSchemaMinorTests(FeedbackLedgerTestCase):
    def validate_entry(self, data):
        normalized, findings = normalize_document(LEDGER_SPEC, data, "entry.toml")
        if normalized is not None:
            findings.extend(check_document_identity(LEDGER_SPEC, normalized, "entry.toml"))
        return normalized, findings

    def test_v1_and_v1_zero_accept_legacy_entries_without_theme(self):
        for version in ("feedback-ledger/v1", "feedback-ledger/v1.0"):
            data = ledger_data(schema=version)
            data.pop("theme")
            normalized, findings = self.validate_entry(data)
            with self.subTest(version=version):
                self.assertIsNotNone(normalized)
                self.assertFalse([item for item in findings if item.level == ERROR])
                canonical = dumps(LEDGER_SPEC, normalized)
                self.assertNotIn("theme =", canonical)
                self.assertEqual(tomllib.loads(canonical)["schema"], version)

    def test_v1_one_accepts_theme(self):
        normalized, findings = self.validate_entry(ledger_data())
        self.assertIsNotNone(normalized)
        self.assertFalse([item for item in findings if item.level == ERROR])

    def test_future_minor_of_supported_major_is_accepted(self):
        normalized, findings = self.validate_entry(ledger_data(schema="feedback-ledger/v1.7"))
        self.assertIsNotNone(normalized)
        self.assertFalse([item for item in findings if item.level == ERROR])

    def test_v2_and_malformed_versions_are_rejected(self):
        versions = ("feedback-ledger/v2", "feedback-ledger/v1.x", "feedback-ledger/v1.01")
        for version in versions:
            normalized, findings = self.validate_entry(ledger_data(schema=version))
            with self.subTest(version=version):
                self.assertIsNotNone(normalized)
                self.assertTrue([item for item in findings if item.level == ERROR])

    def test_old_version_cannot_use_theme(self):
        for version in ("feedback-ledger/v1", "feedback-ledger/v1.0"):
            _, findings = self.validate_entry(ledger_data(schema=version))
            with self.subTest(version=version):
                self.assertTrue(any(item.locus == "entry.toml::theme" for item in findings))

    def test_new_entry_rewrites_draft_version_to_current_minor(self):
        draft = self.write_draft(LEDGER_SPEC, ledger_data(schema="feedback-ledger/v1.2"))
        code, _ = self.run_cli("new-entry", "--from", draft)
        stored = tomllib.loads(self.stored("ledger", ENTRY_ID).read_text(encoding="utf-8"))
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(stored["schema"], LEDGER_CURRENT_SCHEMA)

    def test_new_entry_rejects_unsupported_major(self):
        draft = self.write_draft(LEDGER_SPEC, ledger_data(schema="feedback-ledger/v2"))
        code, _ = self.run_cli("new-entry", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)


class LegacyRenderTests(FeedbackLedgerTestCase):
    def test_render_accepts_legacy_entry_without_theme(self):
        data = ledger_data(schema="feedback-ledger/v1")
        data.pop("theme")
        self.place(LEDGER_SPEC, data)
        check_code, _ = self.run_cli("check", "--canonical")
        self.assertEqual(check_code, EXIT_OK)
        code, output = self.run_cli("render")
        self.assertEqual(code, EXIT_OK)
        self.assertIn(f"({ENTRY_ID}; テーマ: なし)", output)
        self.assertIn("- テーマ: なし; 判断軸: implementation", output)
