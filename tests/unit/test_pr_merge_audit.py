from datetime import datetime
import unittest

from pr_merge_gate.audit import REPORT_SCHEMA, build_owner_report


class OwnerReportEnvelopeTests(unittest.TestCase):
    def test_report_contains_evidence_and_never_grants_a_permit(self):
        evidence = {"result": "ALLOW", "primary_reason": "NO_VIOLATION", "findings": []}
        report = build_owner_report("example/repo", 42, "merge", evidence)
        self.assertEqual(report["schema"], REPORT_SCHEMA)
        self.assertEqual(report["verdict"], "ALLOW")
        self.assertEqual(report["blocker_evidence"], evidence)
        self.assertTrue(report["owner_action_required"])
        self.assertFalse(report["automatic_merge_authorized"])
        self.assertFalse(report["merge_api_called"])
        datetime.fromisoformat(report["generated_at"].replace("Z", "+00:00"))

    def test_block_and_error_reports_never_recommend_a_merge(self):
        for verdict in ("BLOCK", "ERROR"):
            with self.subTest(verdict=verdict):
                report = build_owner_report(
                    "example/repo", 42, "merge", {"result": verdict}
                )
                self.assertEqual(report["next_action"], "DO_NOT_MERGE")

    def test_unknown_verdict_is_rejected(self):
        with self.assertRaises(ValueError):
            build_owner_report("example/repo", 42, "merge", {"result": "PASS"})


if __name__ == "__main__":
    unittest.main()
