"""Check local ledger measurement and deterministic replay."""

from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from feedback_ledger.schema import PROPOSAL
from feedback_ledger.store import Document, Store
from karte.model import Finding, Karte, dumps

from weekly_report import ledger_advisory, ledger_feedback, ledger_karte, local
from weekly_report.period import resolve_period


class LedgerEvidenceTests(unittest.TestCase):
    def test_current_lint_is_recomputed_separately_from_registered_baseline(self):
        baseline = {"schema_version": 2, "source": "fixture", "module_lines": {"mod.py": {}},
                    "comment_blocks": {"mod.py|hash": 2}, "mixed_class_files": {}}
        evidence = {"source": local.LINT_SOURCE, "baseline": baseline, "reason": None,
                    "findings": [{"status": "accepted-debt", "rule": "module-over-100-lines"},
                                 {"status": "violation", "rule": "module-over-100-lines"}]}
        measured = local.measure_maintainability(json.loads(json.dumps(evidence)))
        self.assertEqual(measured["value"], 1)
        self.assertEqual(measured["baseline"]["total"], 3)

    def test_karte_is_observation_of_local_records(self):
        with TemporaryDirectory() as location:
            root = Path(location)
            folder = root / "tmp/_karte"
            folder.mkdir(parents=True)
            finding = Finding("F-21-01", harm_detail="観測結果を失う", rounds=[1, 2], locus=["sample.py:10"],
                              summary="結果の欠損", evidence="固定データ", expected="結果が残る", recheck="再集計")
            (folder / "issue-21.md").write_text(dumps(Karte(issue=21, findings=[finding])), encoding="utf-8")
            (folder / "issue-22.md").write_text("破損", encoding="utf-8")
            evidence = json.loads(json.dumps(ledger_karte.capture(root)))
            result = ledger_karte.measure(evidence)
            self.assertEqual(result["karte_observed_real_findings"]["value"], 1)
            self.assertEqual(result["karte_observed_rereview_rounds"]["value"], 1)
            self.assertEqual(result["karte_observed_pending_disposition"]["value"], 1)
            self.assertEqual(result["karte_observed_real_findings"]["unavailable_karte_count"], 1)
            self.assertIn("日時は不明", result["karte_observed_real_findings"]["scope"])

    def test_feedback_age_has_jst_date_precision_and_zero_denominator(self):
        with TemporaryDirectory() as location:
            root = Path(location)
            path = root / ".ai/feedback/queue/proposal.toml"
            path.parent.mkdir(parents=True)
            doc = Document(PROPOSAL, "proposal", str(path.relative_to(root)), path,
                           {"status": "pending", "proposed_at": date(2025, 1, 2)}, "")
            with patch("weekly_report.ledger_feedback.load_store", return_value=Store(root, {PROPOSAL: [doc]}, [])):
                evidence = json.loads(json.dumps(ledger_feedback.capture(root)))
            result = ledger_feedback.measure(evidence, "2025-01-04T17:00:00Z")
            self.assertEqual(result["owner_pending_proposals"]["value"], 1)
            self.assertEqual(result["owner_pending_proposal_age_days"]["value"], 3)
            self.assertEqual(result["owner_pending_proposal_age_days"]["n"], 1)
            evidence["rows"] = []
            empty = ledger_feedback.measure(evidence, "2025-01-05")
            self.assertEqual(empty["owner_pending_proposals"]["value"], 0)
            self.assertIsNone(empty["owner_pending_proposal_age_days"]["value"])
            self.assertEqual(empty["owner_pending_proposal_age_days"]["n"], 0)

    def test_advisory_replay_counts_history_in_half_open_window(self):
        period = resolve_period("2025-01-04", "2025-01-11", "2025-01-12")
        history_events = [
            {"at": "2025-01-03T15:00:00Z", "action": "create", "from_status": "", "to_status": "open"},
            {"at": "2025-01-10T15:00:00Z", "action": "transition", "from_status": "open", "to_status": "closed"},
        ]
        saved = {"source": ledger_advisory.SOURCE, "reason": None, "records": 1,
                 "events": [{"id": "ADV-fixture", "topic": "観測", "event": event} for event in history_events]}
        result = ledger_advisory.measure(period, json.loads(json.dumps(saved)))
        self.assertEqual(result["advisories_created"]["value"], 1)
        self.assertEqual(result["advisories_closed"]["value"], 0)
        saved["events"] = None
        saved["reason"] = "保存入力を取得できません"
        missing = ledger_advisory.measure(period, saved)
        self.assertIsNone(missing["advisories_closed"]["value"])

    def test_feedback_decision_on_partial_jst_day_has_unknown_membership(self):
        saved = {"source": ledger_feedback.SOURCE, "reason": None, "rows": [
            {"id": "first", "status": "approved", "proposed_at": "2025-01-01", "decided_at": "2025-01-03"},
            {"id": "last", "status": "applied", "proposed_at": "2025-01-01", "decided_at": "2025-01-04"},
        ]}
        period = resolve_period("2025-01-01", "2025-01-06", "2025-01-04T12:00")
        partial = ledger_feedback.measure_decisions(period, saved)
        self.assertIsNone(partial["value"])
        self.assertIsNone(partial["n"])
        self.assertEqual(partial["observed_age_days_by_proposal"], {"first": 2})
        self.assertEqual(partial["ambiguous_proposal_ids"], ["last"])
        period = resolve_period("2025-01-01", "2025-01-06", "2025-01-05")
        complete = ledger_feedback.measure_decisions(period, saved)
        self.assertEqual(complete["value"], 2.5)
        self.assertEqual(complete["n"], 2)
