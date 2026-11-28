"""Exercise GitHub drift and cross-repository dependency identity."""

import json
import unittest

from tests.unit.test_weekly_report import AS_OF, START, activity_sources, issue, pull
from tests.unit.test_weekly_report_display import _data
from weekly_report import backlog, capture_stock, github, render, snapshot
from weekly_report.gh_consistency import compare_reads
from weekly_report.period import parse_jst
from weekly_report.report_initiatives import initiatives_section


class StateCoverageTests(unittest.TestCase):
    def test_changed_state_does_not_publish_mixed_certainties(self):
        initial = issue(1, START, body="## Acceptance Criteria\n- [x] First")
        initial["sub_issues_summary"] = {"total": 1}
        inputs = activity_sources([initial], [pull(3, START)])
        inputs["blocked_by"][1] = github.evidence("blocked/1", [{"state": "open"}])
        inputs["sub_issues"][1] = github.evidence("children/1", [{"id": 20, "state": "open"}])
        changed = issue(1, START, closed=AS_OF)
        changed["sub_issues_summary"] = {"total": 0}
        drift = compare_reads(inputs["issues"], github.evidence("second issues", [changed]))
        inputs["consistency"] = {"issues": drift}
        metrics, inventory = backlog.measure(parse_jst(AS_OF), inputs)
        self.assertEqual(metrics["open_pulls"]["value"], 1)
        for key in ("open_issues", "stale_issues", "blocked_issues"):
            self.assertIsNone(metrics[key]["value"])
            self.assertEqual(metrics[key]["status"], "not_measured")
        for key in ("open_issues", "blocked_by", "sub_issues", "initiative_progress", "issue_acceptance"):
            self.assertIsNone(inventory[key])
        data = _data()
        data["metrics"].update({key: {**value, "basis": "observation"} for key, value in metrics.items()})
        data.update(inventory=inventory, evidence={"consistency": inputs["consistency"]})
        saved = json.loads(snapshot.dumps(data))
        text = render.report(saved, None)
        self.assertIn("state", text)
        self.assertIn("sub_issues_summary", text)
        self.assertIn("親子関係 未計測", text)
        self.assertIn("Issue 一覧の前後照合で変化を検出しました", text)
        self.assertEqual(inputs["sub_issues"][1]["rows"][0]["id"], 20)

    def test_incomplete_second_read_also_qualifies_saved_observations(self):
        inputs = activity_sources([], [pull(3, START)])
        metrics, inventory = backlog.measure(parse_jst(AS_OF), inputs)
        drift = compare_reads(inputs["pulls"], github.evidence("second pulls", reason="HTTP 403"))
        archive = {"metrics": metrics, "inventory": inventory, "evidence": {"consistency": {"pulls": drift}}}
        later_metrics, later_inventory = capture_stock.from_archive(archive)
        self.assertEqual(later_metrics["open_pulls"]["status"], "not_retrieved")
        self.assertIn("HTTP 403", later_metrics["open_pulls"]["reason"])
        self.assertEqual(later_metrics["open_issues"]["value"], 0)
        self.assertIsNone(later_inventory["open_pulls"])
        self.assertEqual(metrics["open_pulls"]["value"], 1)

    def test_external_child_does_not_inherit_same_number_local_dependencies(self):
        def related(repo, number, title):
            return {"number": number, "title": title, "state": "open",
                    "repository_url": f"https://api.github.com/repos/{repo}"}

        repo = "example/review-system"
        parent = {"number": 1, "title": "親", "total": 2, "completed": 0, "children": [
            related("external/related", 7, "外部の子"), related(repo, 7, "対象の子"),
        ]}
        blocked = {7: github.evidence("local/7", [related(repo, 9, "対象の前提")])}
        data = {"repository": repo, "comparison": {},
                "inventory": {"initiative_progress": {1: parent}, "blocked_by": blocked}}
        text = initiatives_section(data)
        self.assertIn('href="https://github.com/external/related/issues/7"', text)
        self.assertIn("外部の子</a> <small class=\"missing\">対象外", text)
        self.assertIn("対象の子</a> <small>→ 前提</small>", text)
        self.assertEqual(text.count('href="https://github.com/example/review-system/issues/9"'), 1)
