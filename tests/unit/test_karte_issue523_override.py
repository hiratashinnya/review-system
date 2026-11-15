"""Issue #523: waived・scope 覆しの owner override_ref と出所検証。"""
import unittest

from feedback_ledger.schema import LEDGER_SPEC
from feedback_ledger.store import write_document
from karte import cli, model, owner_cli, paths, verb_show
from tests.unit.test_feedback_ledger import ENTRY_ID, ledger_data
from tests.unit.test_karte_reviewer_ingest import ReviewerIngestCase, _report


class OverrideReferenceTest(ReviewerIngestCase):
    def _save_ref(self):
        write_document(self.root, LEDGER_SPEC, ledger_data())
        return ENTRY_ID

    def _status(self):
        return self._run(verb_show.cmd_status, issue=str(self.issue), json=True)

    def test_waived_cannot_be_clean_without_registered_reference(self):
        self.assertEqual(0, self._activate()[0])
        self.assertEqual(0, self._ingest(_report())[0])
        self.assertEqual(0, self._decide(disposition="waived", waived_by="owner",
                                        waived_reason="許可済み")[0])
        code, out, err = self._status()
        self.assertEqual(0, code, err)
        self.assertIn('"verdict": "harmful-open"', out)
        self.assertIn('"override_pending"', out)
        ref = self._save_ref()
        self.assertEqual(0, self._decide(override_ref=ref)[0])
        self.assertEqual(ref, self._finding(f"F-{self.issue}-01").override_ref)
        self.assertIn('"verdict": "clean"', self._status()[1])

    def test_owner_scope_override_requires_reference_from_round_one(self):
        self._activate()
        self.assertEqual(0, self._ingest(_report(scope="in"))[0])
        self.assertEqual(0, self._decide(disposition="deferred", deferred_to="#900",
                                        scope="out")[0])
        self.assertIn('"verdict": "harmful-open"', self._status()[1])
        self.assertEqual(0, self._decide(override_ref=self._save_ref())[0])
        self.assertIn('"verdict": "clean"', self._status()[1])
        self.assertEqual(0, self._ingest(_report(f"F-{self.issue}-01", scope="in"))[0])
        self.assertIn('"verdict": "clean"', self._status()[1])

    def test_invalid_owner_ref_rejected_without_write(self):
        self._activate()
        self._ingest(_report())
        before = paths.karte_path(self.issue, self.root).read_bytes()
        code, _, err = self._decide(override_ref="FBK-20261115-missing")
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("override_ref", err)
        self.assertEqual(before, paths.karte_path(self.issue, self.root).read_bytes())

    def test_invalid_ingest_ref_is_fail_close(self):
        self.assertEqual(0, self._run(owner_cli.cmd_activate, issue=str(self.issue))[0])
        report = self.root / "report.md"
        report.write_text(_report(override_ref="FBK-20261115-nonexistent"), encoding="utf-8")
        code, _, err = self._run(cli.cmd_ingest_review, issue=str(self.issue),
                                 round="1", source=str(report))
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("override_ref", err)
        self.assertFalse(paths.karte_path(self.issue, self.root).exists())

    def test_implementer_out_of_scope_without_reviewer_original_is_not_override(self):
        self.assertEqual(0, self._run(owner_cli.cmd_activate, issue=str(self.issue))[0])
        report = self.root / "report.md"
        report.write_text(_report(scope="out", disposition="deferred", deferred_to="#9"),
                          encoding="utf-8")
        code, _, err = self._run(cli.cmd_ingest_review, issue=str(self.issue),
                                 round="1", source=str(report))
        self.assertEqual(0, code, err)
        self.assertIn('"verdict": "clean"', self._status()[1])

    def test_existing_karte_without_ref_remains_readable(self):
        self._activate()
        self._ingest(_report())
        finding = self._finding(f"F-{self.issue}-01")
        self.assertEqual("", finding.override_ref)
        self.assertEqual("", model.parse(model.dumps(self._karte())).findings[0].override_ref)


if __name__ == "__main__":
    unittest.main()
