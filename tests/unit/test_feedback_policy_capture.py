"""Policy vocabulary compatibility and capture CLI contract (#537)."""

import json
from pathlib import Path

from feedback_ledger.cli import EXIT_OK
from feedback_ledger.model import ERROR, check_document_identity, normalize_document
from feedback_ledger.schema import DECISION_POINTS, DIVERGENCES, LEDGER_SPEC
from feedback_ledger.schema_version import LEDGER_CURRENT_SCHEMA
from tests.unit.test_feedback_ledger import ENTRY_ID, FeedbackLedgerTestCase, ledger_data


class PolicyCaptureTests(FeedbackLedgerTestCase):
    def findings(self, **changes):
        data, findings = normalize_document(LEDGER_SPEC, ledger_data(**changes), "entry")
        if data is not None:
            findings.extend(check_document_identity(LEDGER_SPEC, data, "entry"))
        return [finding for finding in findings if finding.level == ERROR]

    def test_policy_and_approval_require_v1_3(self):
        for schema in ("feedback-ledger/v1", "feedback-ledger/v1.0",
                       "feedback-ledger/v1.1", "feedback-ledger/v1.2"):
            for field, value in (("decision_point", "policy"), ("divergence", "approval")):
                changes = {"schema": schema, field: value}
                if schema in ("feedback-ledger/v1", "feedback-ledger/v1.0"):
                    changes["theme"] = None
                raw = ledger_data(**changes)
                if raw["theme"] is None:
                    raw.pop("theme")
                normalized, findings = normalize_document(LEDGER_SPEC, raw, "entry")
                findings += check_document_identity(LEDGER_SPEC, normalized, "entry")
                with self.subTest(schema=schema, field=field):
                    self.assertTrue(any(item.locus == f"entry::{field}" for item in findings))
        self.assertEqual(LEDGER_CURRENT_SCHEMA, "feedback-ledger/v1.3")
        self.assertFalse(self.findings(decision_point="policy", divergence="approval"))

    def test_unknown_values_still_fail(self):
        for changes in ({"decision_point": "policy-unknown"}, {"divergence": "accepted"}):
            with self.subTest(changes=changes):
                self.assertTrue(self.findings(**changes))

    def test_policy_draft_new_entry_check_status_render(self):
        draft = self.write_draft(LEDGER_SPEC, ledger_data(
            decision_point="policy", divergence="approval",
        ))
        for command in (("new-entry", "--from", draft), ("check", "--canonical"),
                        ("status", "--now", "2026-09-19"), ("render",)):
            code, output = self.run_cli(*command)
            with self.subTest(command=command[0]):
                self.assertEqual(code, EXIT_OK, output)
        self.assertIn(ENTRY_ID, output)
        self.assertIn("判断軸: policy", output)
        self.assertIn("divergence: approval", output)

    def test_json_schema_has_matching_vocabulary_and_old_version_gate(self):
        root = Path(__file__).resolve().parents[2]
        schema = json.loads((root / ".ai/schema/feedback-ledger-v1.json").read_text())
        self.assertEqual(schema["properties"]["decision_point"]["enum"], list(DECISION_POINTS))
        self.assertEqual(schema["properties"]["divergence"]["enum"], list(DIVERGENCES))
        gate = schema["allOf"][-1]
        self.assertEqual(gate["if"]["properties"]["schema"]["enum"], [
            "feedback-ledger/v1", "feedback-ledger/v1.0", "feedback-ledger/v1.1",
            "feedback-ledger/v1.2",
        ])
        self.assertEqual(gate["then"]["properties"], {
            "decision_point": {"not": {"const": "policy"}},
            "divergence": {"not": {"const": "approval"}},
        })
