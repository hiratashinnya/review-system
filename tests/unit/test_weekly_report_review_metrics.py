"""Keep failed inputs, missing measurements and zero denominators distinct."""

import unittest

from tests.unit.test_weekly_report import AS_OF, END, REPOSITORY, START, issue, pull
from tests.unit.test_weekly_report_display import _data
from weekly_report import activity, github, render
from weekly_report.period import resolve_period


class MetricCoverageTests(unittest.TestCase):
    def statuses(self, issue_data, pull_data):
        period = resolve_period(START, END, AS_OF)
        metrics, _, _ = activity.measure(period, REPOSITORY, issue_data, pull_data)
        return metrics

    def test_refused_issue_and_pull_reads_are_not_retrieved(self):
        refused = github.evidence("REST", reason="HTTP 403")
        empty = github.evidence("REST", [])
        for issues, pulls, lead in ((refused, empty, "issue_lead_days"),
                                    (empty, refused, "pull_lead_days")):
            with self.subTest(lead=lead):
                metrics = self.statuses(issues, pulls)
                for key in (lead, "defects_per_merge"):
                    self.assertEqual(metrics[key]["status"], "not_retrieved")
                    self.assertIn("HTTP 403", metrics[key]["reason"])
                data = _data()
                data["metrics"].update({key: {**metric, "basis": "period"} for key, metric in metrics.items()})
                self.assertIn("<td>未取得<br>", render.report(data, None))

    def test_missing_times_and_empty_sets_have_different_metric_status(self):
        broken_issue = {**issue(1, START), "state": "closed", "state_reason": "completed"}
        broken_pull = {**pull(2, START, merged=START), "created_at": None}
        data = self.statuses(github.evidence("issues", [broken_issue]), github.evidence("pulls", [broken_pull]))
        self.assertEqual(data["issue_lead_days"]["status"], "not_measured")
        self.assertEqual(data["pull_lead_days"]["status"], "not_measured")
        for key in ("issue_lead_days", "pull_lead_days"):
            self.assertIsNone(data[key]["value"])
        empty = github.evidence("REST", [])
        metrics = self.statuses(empty, empty)
        for key in ("issue_lead_days", "pull_lead_days", "defects_per_merge"):
            self.assertEqual(metrics[key]["status"], "not_calculable")
        self.assertEqual(metrics["issues_created"]["value"], 0)
        self.assertEqual(metrics["issues_created"]["status"], "measured")
