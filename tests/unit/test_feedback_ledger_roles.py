"""Versioned pipeline-role recording and schema parity contracts (Issue 371)."""

import json
import re
import unittest
from pathlib import Path

from feedback_ledger.model import check_document_identity
from feedback_ledger.schema import LEDGER_SPEC
from feedback_ledger.schema_utils import valid_overridden_role
from feedback_ledger.schema_values import (
    LEGACY_OVERRIDDEN_ROLES, OVERRIDDEN_ROLES, PIPELINE_OVERRIDDEN_ROLES,
)
from feedback_ledger.schema_version import LEDGER_CURRENT_SCHEMA
from feedback_ledger.store import load_store
from tests.unit.test_feedback_ledger import FeedbackLedgerTestCase, ledger_data


class LedgerRoleContractTests(FeedbackLedgerTestCase):
    def test_every_pipeline_role_can_be_recorded_via_new_entry(self):
        for role in PIPELINE_OVERRIDDEN_ROLES:
            with self.subTest(role=role):
                data = ledger_data(topic=role, id=f"FBK-20260901-{role}", overridden_role=role)
                draft = self.write_draft(LEDGER_SPEC, data)
                self.assertEqual(self.run_cli("new-entry", "--from", draft)[0], 0)
        recorded = load_store(self.root).of(LEDGER_SPEC.kind)
        self.assertEqual({doc.data["overridden_role"] for doc in recorded},
                         set(PIPELINE_OVERRIDDEN_ROLES))
        self.assertEqual(self.run_cli("check", "--canonical")[0], 0)

    def test_python_and_json_agree_for_every_supported_version(self):
        path = Path(__file__).resolve().parents[2] / ".ai/schema/feedback-ledger-v1.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        role_pattern = schema["properties"]["overridden_role"]["pattern"]
        condition = schema["allOf"][1]
        old_versions = condition["if"]["properties"]["schema"]["enum"]
        old_pattern = condition["then"]["properties"]["overridden_role"]["pattern"]
        roles = OVERRIDDEN_ROLES + ("skill:issue-pipeline", "unknown-role", "skill:")
        for version in (*old_versions, LEDGER_CURRENT_SCHEMA):
            for role in roles:
                expected = role in LEGACY_OVERRIDDEN_ROLES or role == "skill:issue-pipeline"
                expected |= version == LEDGER_CURRENT_SCHEMA and role in PIPELINE_OVERRIDDEN_ROLES
                with self.subTest(version=version, role=role):
                    self.assertEqual(valid_overridden_role(role, version), expected)
                    accepted = bool(re.fullmatch(role_pattern, role))
                    if version in old_versions:
                        accepted &= bool(re.fullmatch(old_pattern, role))
                    self.assertEqual(accepted, expected)
                    data = ledger_data(schema=version, overridden_role=role)
                    if version in ("feedback-ledger/v1", "feedback-ledger/v1.0"):
                        data.pop("theme")
                    findings = check_document_identity(LEDGER_SPEC, data, "entry.toml")
                    self.assertEqual(not any(f.locus.endswith("::overridden_role")
                                             for f in findings), expected)

    def test_unknown_role_is_rejected_before_persistence(self):
        draft = self.write_draft(LEDGER_SPEC, ledger_data(overridden_role="unknown-role"))
        self.assertEqual(self.run_cli("new-entry", "--from", draft)[0], 4)
        self.assertEqual(load_store(self.root).of(LEDGER_SPEC.kind), [])


if __name__ == "__main__":
    unittest.main()
