"""申し送り記録の再掲・レポート拒否・オフライン経路。"""

import json
from unittest import mock

from karte import exit_codes, model, paths
from karte.finding_handoff_exemption import is_stall_exempt
from tests.unit.karte_support import RootedCase, finding
from tests.unit.test_karte_finding_handoff_predicate import verified_item
from tests.unit.test_karte_reviewer_ingest import ReviewerIngestCase, _report


FIELDS = finding("a.py", "要約", harm="none", harm_detail="実害なし", severity="minor",
                 evidence="根拠", expected="期待", recheck="確認", disposition="deferred", deferred_to="#9")


class HandoffIngestTest(RootedCase):
    def test_repost_keeps_record_until_content_changes(self):
        self.assertEqual(0, self.ingest(1, ("new", FIELDS))[0])
        path = paths.karte_path(7, self.root)
        ledger = self.ledger()
        ledger.findings[0].handoff = verified_item().handoff
        path.write_text(model.dumps(ledger), encoding="utf-8")
        self.assertTrue(is_stall_exempt(self.ledger().findings[0]))
        self.assertEqual(0, self.ingest(2, ("F-7-01", {**FIELDS, "evidence": "新しい根拠"}))[0])
        self.assertTrue(is_stall_exempt(self.ledger().findings[0]))
        self.assertEqual(0, self.ingest(3, ("F-7-01", {**FIELDS, "summary": "新しい要約"}))[0])
        self.assertIsNotNone(self.ledger().findings[0].handoff)
        self.assertFalse(is_stall_exempt(self.ledger().findings[0]))

    def test_ingest_review_rejects_all(self):
        code, _, err = self.ingest(1, ("new", FIELDS), ("new", {**FIELDS, "handoff_unknown": "x"}))
        self.assertEqual(exit_codes.EXIT_ERROR, code)
        self.assertIn("handoff_", err)
        self.assertFalse(paths.karte_path(7, self.root).exists())

    def test_verbs_do_not_run_subprocess(self):
        path = paths.karte_path(7, self.root, create_dir=True)
        path.write_text(model.dumps(model.Karte(issue=7, findings=[verified_item()])), encoding="utf-8")
        with mock.patch("subprocess.run", side_effect=AssertionError("subprocess")), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("subprocess")):
            code, output, err = self.run_verb(["status", "--issue", "7", "--json"])
            self.assertEqual(0, code, err)
            self.assertEqual(["F-7-01"], json.loads(output)["handoff_exempt_findings"])
            code, output, err = self.run_verb(["render", "--issue", "7"])
            self.assertEqual(0, code, err)
            self.assertNotIn("★無進捗", output)
            code, _, err = self.run_verb(["check", "--issue", "7", "--round", "11"])
            self.assertEqual(exit_codes.EXIT_ERROR, code)
            self.assertIn("診断が要る未解消 finding", err)


class HandoffReviewerTest(ReviewerIngestCase):
    def test_ingest_reviewer_rejects_entire_report(self):
        self.assertEqual(0, self._activate()[0])
        text = _report() + "\n" + _report(handoff_state="verified")
        code, _, err = self._ingest(text)
        self.assertEqual(exit_codes.EXIT_ERROR, code)
        self.assertIn("handoff_", err)
        self.assertFalse(paths.karte_path(self.issue, self.root).exists())
