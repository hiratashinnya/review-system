"""Fixed-time tests for report semantics, read-only retrieval, and rendering."""

from datetime import timedelta
from pathlib import Path
import io
import json
from subprocess import CompletedProcess
import tempfile
import unittest
from unittest.mock import patch

from weekly_report import activity, analysis, backlog, cli, github, local, output, read_github, records, snapshot
from weekly_report.comparison import compare
from weekly_report.period import parse_jst, resolve_period

REPOSITORY = "example/review-system"
START = "2026-11-23T00:00:00+09:00"
END = "2026-11-30T00:00:00+09:00"
AS_OF = "2026-11-30T02:00:00+09:00"


def issue(number, created, closed=None, reason=None, title=None, body=None, updated=None):
    return records.issue({
        "number": number, "state": "closed" if closed else "open",
        "title": title or f"Issue {number}", "labels": [], "body": body,
        "created_at": created, "updated_at": updated or closed or created,
        "closed_at": closed, "state_reason": reason,
    })


def pull(number, created, merged=None):
    return records.pull({
        "number": number, "state": "closed" if merged else "open", "title": f"PR {number}",
        "draft": False, "base": {"ref": "main"}, "created_at": created,
        "updated_at": merged or created, "closed_at": merged, "merged_at": merged,
    })


def page(payload, more=False):
    link = '\nLink: <https://api.github.com/next>; rel="next"' if more else ""
    return f"HTTP/2.0 200 OK{link}\n\n{json.dumps(payload)}"


class PeriodTests(unittest.TestCase):
    def test_monday_boundary_and_partial(self):
        period = resolve_period(None, None, "2026-11-22T15:00:00Z")
        self.assertEqual(period.start.isoformat(), START)
        self.assertEqual(period.end.isoformat(), END)
        self.assertTrue(period.as_dict()["partial"])
        self.assertFalse(period.contains(parse_jst(START)))
        period = resolve_period(None, None, "2026-11-22T14:59:59Z")
        self.assertEqual(period.end.isoformat(), START)

    def test_explicit_dates_and_invalid_ranges(self):
        period = resolve_period("2026-11-23", "2026-11-30", AS_OF)
        self.assertTrue(period.contains(parse_jst(START)))
        self.assertFalse(period.contains(parse_jst(END)))
        self.assertFalse(period.as_dict()["partial"])
        for start, end, now in [(START, None, AS_OF), (END, START, AS_OF), (START, END, "2026-11-22")]:
            with self.subTest(start=start, end=end, now=now), self.assertRaises(ValueError):
                resolve_period(start, end, now)


class ActivityTests(unittest.TestCase):
    def measure(self, issues, pulls, now=AS_OF):
        return activity.measure(
            resolve_period(START, END, now), REPOSITORY,
            github.evidence("issues", issues, reason="取得失敗" if issues is None else None),
            github.evidence("pulls", pulls, reason="打ち切り" if pulls is None else None),
        )

    def test_close_reason_half_open_and_lead_time(self):
        rows = [issue(1, "2026-11-22T00:00:00+09:00", START, "completed"),
                issue(2, START, START, "not_planned"),
                issue(3, START, "2026-11-24T00:00:00+09:00", "duplicate"),
                issue(4, END, END, "completed"), issue(5, START)]
        metrics, events = self.measure(rows, [pull(6, START, START), pull(7, START, END)])
        self.assertEqual(metrics["issues_created"]["value"], 3)
        self.assertEqual(metrics["issues_closed_completed"]["value"], 1)
        self.assertEqual(metrics["issues_closed_not_planned"]["value"], 1)
        self.assertEqual(metrics["issues_closed_duplicate"]["value"], 1)
        self.assertEqual(metrics["issue_lead_days"]["value"], 1)
        self.assertEqual(metrics["pulls_merged"]["value"], 1)
        self.assertEqual(metrics["pull_lead_days"]["value"], 0)
        self.assertEqual([row["number"] for row in events["closed"]], [1, 2, 3])

    def test_unknown_reason_does_not_count_as_completion(self):
        metrics, _ = self.measure([issue(1, START, START)], [])
        self.assertIsNone(metrics["issues_closed_completed"]["value"])
        self.assertEqual(metrics["issues_closed_completed"]["observed_count"], 0)
        self.assertEqual(metrics["issues_closed_unknown"]["value"], 1)
        self.assertIsNone(metrics["issue_lead_days"]["value"])

    def test_existing_defect_definition_uses_pre_window_merge_as_reference(self):
        issues = [issue(1, START, body="#2"), issue(9, START, body="#3")]
        pulls = [pull(2, "2026-11-20T00:00:00+09:00", "2026-11-22T23:59:59+09:00"),
                 pull(3, START, "2026-11-23T00:00:01+09:00")]
        metrics, _ = self.measure(issues, pulls)
        self.assertEqual(metrics["defects_per_merge"]["numerator"], 1)
        self.assertEqual(metrics["defects_per_merge"]["denominator"], 1)
        self.assertEqual(metrics["defects_per_merge"]["derived_issue_numbers"], [1])

    def test_missing_inputs_and_zero_denominator(self):
        metrics, events = self.measure(None, [])
        self.assertIsNone(metrics["issues_created"]["value"])
        self.assertIsNone(metrics["issue_lead_days"]["n"])
        self.assertIsNone(events["closed"])
        metrics, _ = self.measure([], [])
        self.assertEqual(metrics["issues_created"]["value"], 0)
        self.assertIsNone(metrics["defects_per_merge"]["value"])
        self.assertEqual(metrics["defects_per_merge"]["denominator"], 0)
        metrics, _ = self.measure([], [], START)
        self.assertIsNone(metrics["defects_per_merge"]["value"])

    def test_backlog_is_point_in_time_and_reports_incomplete_dependencies(self):
        period = resolve_period(START, END, AS_OF)
        boundary = (period.observed_at - timedelta(days=30)).isoformat()
        rows = [issue(1, boundary), issue(2, START), issue(3, START, START, "completed")]
        gh = {"issues": github.evidence("issues", rows), "pulls": github.evidence("pulls", []),
              "blocked_by": {1: github.evidence("dependencies", [{"state": "open"}]),
                             2: github.evidence("dependencies", reason="打ち切り")}, "sub_issues": {}}
        metrics, inventory = backlog.measure(period, gh)
        self.assertEqual(metrics["open_issues"]["value"], 2)
        self.assertEqual(metrics["stale_issues"]["value"], 1)
        self.assertIsNone(metrics["blocked_issues"]["value"])
        self.assertEqual(metrics["blocked_issues"]["observed_issue_numbers"], [1])
        self.assertEqual([row["number"] for row in inventory["open_issues"]], [1, 2])


class GitHubTests(unittest.TestCase):
    def get(self, response, limit=30, collection=None):
        with patch("weekly_report.github.subprocess.run", return_value=response) as run:
            value = github.get(REPOSITORY, "issues?per_page=100", limit, convert=dict, collection=collection)
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--method") + 1], "GET")
        return value

    def test_multiple_http_pages_and_explicit_last_page(self):
        result = self.get(CompletedProcess([], 0, page([{"id": 1}], True) + page([{"id": 2}]), ""))
        self.assertEqual(result["pages"], 2)
        self.assertEqual(result["rows"], [{"id": 1}, {"id": 2}])

    def test_truncation_schema_errors_rate_limit_and_duplicates(self):
        first = page([{"id": 1}], True)
        last = page([{"id": 2}])
        cases = [(first + last, 2), (first, 30), (first + page([{"id": 1}]), 30),
                 (first + "[{\"id\":2}]", 30), ("[]", 30), ("", 30)]
        for response, limit in cases:
            with self.subTest(response=response, limit=limit):
                result = self.get(CompletedProcess([], 0, response, ""), limit)
                self.assertIsNone(result["rows"])
                self.assertTrue(result["reason"])
        result = self.get(CompletedProcess([], 1, first + last, "gh: too many (HTTP 429)"))
        self.assertIsNone(result["rows"])
        self.assertIn("429", result["reason"])

    def test_github_actions_search_cap_and_count_mismatch(self):
        for count in (2, 1000):
            with self.subTest(count=count):
                body = page({"total_count": count, "workflow_runs": [{"id": 1}]})
                result = self.get(CompletedProcess([], 0, body, ""), collection="workflow_runs")
                self.assertIsNone(result["rows"])
                self.assertEqual(result["reported_total"], count)

    def test_actions_day_slices_exclude_shared_boundary(self):
        period = resolve_period("2026-11-23", "2026-11-25", AS_OF)
        second_day = parse_jst("2026-11-24")
        row = {"id": 1, "created_at": second_day}
        with patch("weekly_report.read_github.get", side_effect=[
            github.evidence("first", [row], retrieved_total=1),
            github.evidence("second", [row], retrieved_total=1),
        ]) as fetch:
            result = read_github.read_ci(REPOSITORY, period, 30)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(result["rows"], [row])
        self.assertEqual(len(result["shards"]), 2)


class ComparisonTests(unittest.TestCase):
    def snapshot(self, start, end, observed_at, value, **metric):
        period = resolve_period(start, end, observed_at)
        return {"schema_version": 1, "repository": REPOSITORY,
                "observed_at": observed_at, "period": period.as_dict(),
                "metrics": {"example": {"definition": "test", "value": value, "basis": "period", "unit": "items"} | metric}}

    def test_matching_adjacent_full_or_partial_and_nonperiod_values(self):
        for current_at, earlier_at in [(AS_OF, AS_OF), ("2026-11-24", "2026-11-17")]:
            with self.subTest(current_at=current_at):
                current = self.snapshot(START, END, current_at, 7)
                previous = self.snapshot("2026-11-16", START, earlier_at, 3)
                self.assertEqual(compare(current, previous)["metrics"]["example"]["delta"], 4)
                current["metrics"]["example"]["basis"] = "observation"
                self.assertIsNone(compare(current, previous)["metrics"]["example"]["delta"])

    def test_initial_incompatible_spans_definitions_and_missing_values(self):
        current = self.snapshot(START, END, "2026-11-24", 5)
        self.assertEqual(compare(current, None)["status"], "initial")
        previous = self.snapshot("2026-11-16", START, AS_OF, 3)
        self.assertEqual(compare(current, previous)["status"], "incomparable")
        self.assertEqual(compare(current, {})["status"], "incomparable")
        previous = self.snapshot("2026-11-16", START, "2026-11-17", 3, definition="old")
        self.assertIsNone(compare(current, previous)["metrics"]["example"]["delta"])
        previous = self.snapshot("2026-11-16", START, "2026-11-17", None)
        self.assertIsNone(compare(current, previous)["metrics"]["example"]["delta"])


class BundleTests(unittest.TestCase):
    def test_end_to_end_cli_escapes_inputs_and_never_overwrites(self):
        unsafe = '<external quoted="yes">'
        data = {"issues": github.evidence("issues", [issue(1, START, title=unsafe)], retrieved_total=1),
                "pulls": github.evidence("pulls", [], retrieved_total=0),
                "ci": github.evidence("actions", [], retrieved_total=0),
                "blocked_by": {1: github.evidence("dependencies", [])}, "sub_issues": {}, "reviews": {}}
        reference = {"base_ref": "origin/main", "base_sha": "a" * 40,
                     "checkout_sha": "b" * 40, "checkout_dirty": False}
        with tempfile.TemporaryDirectory() as directory, patch("sys.stdout", new_callable=io.StringIO), \
                patch("sys.stderr", new_callable=io.StringIO), patch("weekly_report.local.checkout", return_value=reference), \
                patch("weekly_report.read_github.collect", return_value=data):
            base = Path(directory)
            root = base / "repo"
            root.mkdir()
            raw, rendered = base / "raw", base / "rendered"
            with patch("weekly_report.cli.resolve_root", return_value=root):
                command = ["collect", "--repository", REPOSITORY, "--now", START, "--out", str(raw)]
                self.assertEqual(cli.main(command), 0)
                original = (raw / "snapshot.json").read_bytes()
                self.assertEqual(cli.main(command), 1)
                self.assertEqual((raw / "snapshot.json").read_bytes(), original)
                self.assertEqual(cli.main(command[:-1] + [str(root / "content")]), 1)
                body = {"sections": {key: [{"kind": "fact", "text": unsafe, "sources": [unsafe]}]
                                     for key in analysis.SECTIONS}, "summary": "今週の要約"}
                draft = base / "analysis.json"
                draft.write_text(snapshot.dumps(body), encoding="utf-8")
                command = ["render", "--snapshot", str(raw / "snapshot.json"), "--analysis",
                           str(draft), "--out", str(rendered)]
                self.assertEqual(cli.main(command), 0)
            self.assertEqual((rendered / "snapshot.json").read_bytes(), original)
            html = (rendered / "report.html").read_text(encoding="utf-8")
            self.assertNotIn(unsafe, html)
            self.assertIn("&lt;external quoted=&quot;yes&quot;&gt;", html)
            self.assertIn("途中経過", html)
            self.assertIn("今週の要約", (rendered / "summary.txt").read_text(encoding="utf-8"))
            self.assertFalse((root / "content").exists())
            self.assertIsNone(snapshot.load(raw / "snapshot.json")["metrics"]["maintainability_violations"]["value"])

    def test_worktree_output_denied_through_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repo"
            root.mkdir()
            alias = base / "alias"
            alias.symlink_to(root, target_is_directory=True)
            with patch("weekly_report.render.report", return_value="report"), \
                    patch("weekly_report.output.chat_summary", return_value="summary"):
                with self.assertRaises(ValueError):
                    output.write({}, None, alias / "content", root)
            self.assertEqual(list(root.iterdir()), [])

    def test_missing_local_baselines_and_ledgers_are_unmeasured(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            period = resolve_period(START, END, AS_OF)
            self.assertIsNone(local.maintainability(root)["value"])
            self.assertIsNone(local.owner_proposals(root)["value"])
            self.assertIsNone(local.advisory(root, period)["advisories_created"]["value"])
