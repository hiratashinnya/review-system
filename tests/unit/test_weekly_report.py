"""Fixed-time tests for report semantics, read-only retrieval, and rendering."""

from datetime import timedelta
from pathlib import Path
import io
import json
from subprocess import CompletedProcess, run
import tempfile
import unittest
from unittest.mock import patch

from defect_metrics.collect import load_issues, load_pulls
from defect_metrics.metrics import compute_window_metrics
from defect_metrics.model import Window

from weekly_report import activity, analysis, backlog, cli, github, local, output, quality, read_github, records, snapshot
from weekly_report.git_source import verify_repository
from weekly_report.comparison import compare
from weekly_report.period import COLLECTION_START, parse_jst, resolve_period

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


def pull(number, created, merged=None, head_sha=None):
    return records.pull({
        "number": number, "state": "closed" if merged else "open", "title": f"PR {number}",
        "draft": False, "base": {"ref": "main"}, "head": {"sha": head_sha}, "created_at": created,
        "updated_at": merged or created, "closed_at": merged, "merged_at": merged,
    })


def page(payload, more=False):
    link = '\nLink: <https://api.github.com/next>; rel="next"' if more else ""
    return f"HTTP/2.0 200 OK{link}\n\n{json.dumps(payload)}"


def git(root, *args):
    return run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


def initialize(root, *options):
    root.mkdir()
    git(root, "init", *options)
    git(root, "remote", "add", "origin", "https://github.com/Example/Review-System.git")


def activity_sources(issues, pulls, reviews=None):
    return {"issues": github.evidence("issues", issues, retrieved_total=len(issues)),
            "pulls": github.evidence("pulls", pulls, retrieved_total=len(pulls)),
            "ci": github.evidence("actions", [], retrieved_total=0),
            "blocked_by": {}, "sub_issues": {}, "reviews": reviews or {}}


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
        metrics, events, _ = self.measure(rows, [pull(6, START, START), pull(7, START, END)])
        self.assertEqual(metrics["issues_created"]["value"], 3)
        self.assertEqual(metrics["issues_closed_completed"]["value"], 1)
        self.assertEqual(metrics["issues_closed_not_planned"]["value"], 1)
        self.assertEqual(metrics["issues_closed_duplicate"]["value"], 1)
        self.assertEqual(metrics["issue_lead_days"]["value"], 1)
        self.assertEqual(metrics["pulls_merged"]["value"], 1)
        self.assertEqual(metrics["pull_lead_days"]["value"], 0)
        self.assertEqual([row["number"] for row in events["closed"]], [1, 2, 3])

    def test_unknown_reason_does_not_count_as_completion(self):
        metrics, _, _ = self.measure([issue(1, START, START)], [])
        self.assertIsNone(metrics["issues_closed_completed"]["value"])
        self.assertEqual(metrics["issues_closed_completed"]["observed_count"], 0)
        self.assertEqual(metrics["issues_closed_unknown"]["value"], 1)
        self.assertIsNone(metrics["issue_lead_days"]["value"])

    def test_existing_defect_definition_uses_pre_window_merge_as_reference(self):
        issues = [issue(1, START, body="#2"), issue(9, START, body="#3")]
        pulls = [pull(2, "2026-11-20T00:00:00+09:00", "2026-11-22T23:59:59+09:00"),
                 pull(3, START, "2026-11-23T00:00:01+09:00")]
        metrics, _, captured = self.measure(issues, pulls)
        self.assertEqual(metrics["defects_per_merge"]["numerator"], 1)
        self.assertEqual(metrics["defects_per_merge"]["denominator"], 1)
        self.assertEqual(metrics["defects_per_merge"]["derived_issue_numbers"], [1])
        captured = json.loads(snapshot.dumps(captured))
        replay = compute_window_metrics(Window(parse_jst(START), parse_jst(END)),
                                        load_issues(captured["issues"]), load_pulls(captured["pulls"]), REPOSITORY)
        self.assertEqual(captured["issues"][0]["body"], "#2")
        self.assertEqual(captured["pulls"][0]["mergedAt"], "2026-11-22T23:59:59+09:00")
        self.assertEqual((replay.derived_issues, replay.merged_prs), (1, 1))

    def test_missing_inputs_and_zero_denominator(self):
        metrics, events, captured = self.measure(None, [])
        self.assertIsNone(metrics["issues_created"]["value"])
        self.assertIsNone(metrics["issue_lead_days"]["n"])
        self.assertIsNone(events["closed"])
        self.assertIsNone(captured)
        metrics, _, _ = self.measure([], [])
        self.assertEqual(metrics["issues_created"]["value"], 0)
        self.assertIsNone(metrics["defects_per_merge"]["value"])
        self.assertEqual(metrics["defects_per_merge"]["denominator"], 0)
        metrics, _, _ = self.measure([], [], START)
        self.assertIsNone(metrics["defects_per_merge"]["value"])

    def test_backlog_is_point_in_time_and_reports_incomplete_dependencies(self):
        period = resolve_period(START, END, AS_OF)
        boundary = (period.observed_at - timedelta(days=30)).isoformat()
        rows = [issue(1, boundary), issue(2, START), issue(3, START, START, "completed")]
        gh = {"issues": github.evidence("issues", rows), "pulls": github.evidence("pulls", []),
              "blocked_by": {1: github.evidence("dependencies", [{"state": "open"}]),
                             2: github.evidence("dependencies", reason="打ち切り")}, "sub_issues": {}}
        metrics, inventory = backlog.measure(period.observed_at, gh)
        self.assertEqual(metrics["open_issues"]["value"], 2)
        self.assertEqual(metrics["stale_issues"]["value"], 1)
        self.assertIsNone(metrics["blocked_issues"]["value"])
        self.assertEqual(metrics["blocked_issues"]["observed_issue_numbers"], [1])
        self.assertEqual([row["number"] for row in inventory["open_issues"]], [1, 2])

    def test_missing_close_timestamp_preserves_known_items_separately(self):
        rows = [issue(1, START) | {"state": "closed"}, issue(2, START, START, "completed")]
        metrics, events, _ = self.measure(rows, [])
        self.assertIsNone(metrics["issues_closed_completed"]["value"])
        self.assertEqual(metrics["issues_closed_completed"]["observed_count"], 1)
        self.assertIsNone(events["closed"])
        self.assertEqual([row["number"] for row in events["closed_known"]], [2])

    def test_pending_review_is_not_a_missing_submitted_timestamp(self):
        period = resolve_period(START, END, AS_OF)
        pending = records.review({"id": 11, "state": "PENDING"})
        approved = records.review({"id": 12, "state": "APPROVED"})
        for rows, expected in [([pending], 0), ([pending, approved], None)]:
            with self.subTest(expected=expected):
                data = activity_sources([], [pull(1, START)], {1: github.evidence("reviews", rows)})
                metric = quality.measure(period, data)["review_submissions"]
                self.assertEqual(metric["value"], expected)
                if expected is None:
                    self.assertIn("時刻に欠損", metric["reason"])

    def test_current_head_association_excludes_prior_unknown_and_unsubmitted_evidence(self):
        sha, prior_sha = "A" * 40, "b" * 40
        submitted = {"state": "APPROVED", "submitted_at": START}
        reviews = [records.review({"id": i, **submitted, "commit_id": commit})
                   for i, commit in enumerate((sha, prior_sha, None), start=11)]
        reviews.append(records.review({"id": 14, "state": "PENDING", "commit_id": sha}))
        data = activity_sources([], [pull(1, START, head_sha=sha), pull(2, START)],
                                {1: github.evidence("reviews", reviews), 2: github.evidence("reviews", [])})
        runs = [records.workflow_run({"id": i, "event": "pull_request", "status": "completed",
                                      "conclusion": "success", "created_at": START, "head_sha": commit})
                for i, commit in enumerate((sha, prior_sha, None), start=21)]
        data["ci"] = github.evidence("actions", runs)
        self.assertEqual(quality.matching_heads(data), {
            1: {"head_sha": sha.lower(), "matching_workflow_run_ids": [21], "matching_review_ids": [11]},
            2: {"head_sha": None, "matching_workflow_run_ids": None, "matching_review_ids": None},
        })
        self.assertIsNone(quality.matching_heads(data | {"ci": github.evidence("actions", reason="取得失敗")})
                          [1]["matching_workflow_run_ids"])


class GitHubTests(unittest.TestCase):
    def get(self, response, limit=30, collection=None):
        with patch("weekly_report.github.subprocess.run", return_value=response) as run:
            value = github.get(REPOSITORY, "issues?per_page=100", limit, convert=dict, collection=collection)
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--method") + 1], "GET")
        return value

    def test_multiple_http_pages_and_explicit_last_page(self):
        response = CompletedProcess([], 0, page([{"id": 1}], True) + page([{"id": 2}]), "")
        for limit in (2, 30):
            with self.subTest(limit=limit):
                result = self.get(response, limit)
                self.assertEqual(result["pages"], 2)
                self.assertEqual(result["rows"], [{"id": 1}, {"id": 2}])

    def test_truncation_schema_errors_rate_limit_and_duplicates(self):
        first = page([{"id": 1}], True)
        last = page([{"id": 2}])
        cases = [(first + page([{"id": 2}], True) + page([{"id": 3}]), 2),
                 (first + page([{"id": 2}], True), 2), (first, 30), (first + page([{"id": 1}]), 30),
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
                "observed_at": observed_at, "observation_source": COLLECTION_START, "period": period.as_dict(),
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

    def test_actual_observations_compare_even_when_event_windows_differ(self):
        current = self.snapshot(START, END, "2026-11-24", 7, basis="observation")
        previous = self.snapshot("2026-11-16", START, "2026-11-23", 3, basis="observation")
        compared = compare(current, previous)
        self.assertEqual(compared["status"], "incomparable")
        self.assertEqual(compared["observation"]["status"], "comparable")
        self.assertEqual(compared["observation"]["previous_observed_at"], START)
        self.assertEqual(compared["observation"]["observed_at"], "2026-11-24T00:00:00+09:00")
        self.assertEqual(compared["metrics"]["example"], {"previous": 3, "delta": 4, "reason": None})
        self.assertEqual(compare(current, previous | {"observed_at": "2026-11-24"})["observation"]["status"],
                         "incomparable")
        self.assertIsNone(compare(current, previous | {"observed_at": "2026-11-22"})["metrics"]["example"]["delta"])
        self.assertIsNone(compare(current, previous | {"observation_source": None})["metrics"]["example"]["delta"])
        previous["metrics"]["example"]["value"] = None
        self.assertIsNone(compare(current, previous)["metrics"]["example"]["delta"])


class BundleTests(unittest.TestCase):
    def test_end_to_end_cli_escapes_inputs_and_never_overwrites(self):
        unsafe = '<external quoted="yes">'
        data = {"issues": github.evidence("issues", [issue(1, START, title=unsafe)], retrieved_total=1),
                "pulls": github.evidence("pulls", [pull(2, START)], retrieved_total=1),
                "ci": github.evidence("actions", [], retrieved_total=0),
                "blocked_by": {1: github.evidence("dependencies", [])}, "sub_issues": {}, "reviews": {}}
        reference = {"base_ref": "origin/main", "base_sha": "a" * 40,
                     "checkout_sha": "b" * 40, "checkout_dirty": False}
        with tempfile.TemporaryDirectory() as directory, patch("sys.stdout", new_callable=io.StringIO), \
                patch("sys.stderr", new_callable=io.StringIO), patch("weekly_report.local.checkout", return_value=reference), \
                patch("weekly_report.read_github.collect", return_value=data):
            base = Path(directory)
            root = base / "repo"
            initialize(root)
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
                external = json.loads(original)
                external["comparison"]["metrics"]["issues_created"] = {"delta": unsafe, "previous": unsafe, "reason": None}
                external["inventory"]["open_issues"][0]["url"] = "https://example.invalid/external"
                external_path = base / "incoming.json"
                external_path.write_text(snapshot.dumps(external), encoding="utf-8")
                second = base / "second"
                self.assertEqual(cli.main(["render", "--snapshot", str(external_path), "--analysis",
                                           str(draft), "--out", str(second)]), 0)
            self.assertEqual((rendered / "snapshot.json").read_bytes(), original)
            html = (rendered / "report.html").read_text(encoding="utf-8")
            self.assertNotIn(unsafe, html)
            self.assertIn("&lt;external quoted=&quot;yes&quot;&gt;", html)
            self.assertIn('href="https://github.com/example/review-system/issues/1"', html)
            self.assertIn('href="https://github.com/example/review-system/pull/2"', html)
            self.assertIn("途中経過", html)
            self.assertIn("今週の要約", (rendered / "summary.txt").read_text(encoding="utf-8"))
            second_html = (second / "report.html").read_text(encoding="utf-8")
            self.assertNotIn(unsafe, second_html)
            self.assertNotIn('href="https://example.invalid/external"', second_html)
            self.assertIn('<td>&lt;external quoted=&quot;yes&quot;&gt;<br><small>前回 ', second_html)
            self.assertFalse((root / "content").exists())
            self.assertIsNone(snapshot.load(raw / "snapshot.json")["metrics"]["maintainability_violations"]["value"])

    def test_worktree_output_denied_through_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repo"
            initialize(root)
            alias = base / "alias"
            alias.symlink_to(root, target_is_directory=True)
            with patch("weekly_report.render.report", return_value="report"), \
                    patch("weekly_report.output.chat_summary", return_value="summary"):
                with self.assertRaises(ValueError):
                    output.write({}, None, alias / "content", root)
            self.assertFalse((root / "content").exists())

    def test_linked_worktrees_and_git_admin_are_denied_before_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root, linked = parent / "primary", parent / "linked"
            initialize(root)
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.org",
                "commit", "--allow-empty", "-m", "initial")
            git(root, "worktree", "add", "--detach", str(linked))
            with patch("weekly_report.render.report", return_value="report"), \
                    patch("weekly_report.output.chat_summary", return_value="summary"):
                for protected in (root, linked, root / ".git"):
                    with self.subTest(path=protected), self.assertRaisesRegex(ValueError, "Git 管理領域"):
                        output.write({}, None, protected / "report", linked)
                    self.assertFalse((protected / "report").exists())
                with patch.dict("os.environ", {"TMPDIR": str(root)}), \
                        patch("weekly_report.worktree_output.mkdtemp") as make_temp:
                    with self.assertRaises(ValueError):
                        output.write({}, None, None, linked)
                    make_temp.assert_not_called()
                with patch.dict("os.environ", {"TMPDIR": str(parent)}):
                    archive = output.write({}, None, None, linked)
                    self.assertEqual(archive.parent, parent)
                    self.assertTrue((archive / "report.html").is_file())

    def test_external_git_admin_and_unknown_primary_fail_safely(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root, admin, linked = (parent / name for name in ("primary", "store", "linked"))
            initialize(root, "--separate-git-dir", str(admin))
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.org",
                "commit", "--allow-empty", "-m", "initial")
            git(root, "worktree", "add", "--detach", str(linked))
            with patch("weekly_report.render.report", return_value="report"), \
                    patch("weekly_report.output.chat_summary", return_value="summary"):
                with self.assertRaisesRegex(ValueError, "Git 管理領域"):
                    output.write({}, None, admin / "report", root)
                outside = parent / "report"
                with self.assertRaisesRegex(ValueError, "所在を確認できません"):
                    output.write({}, None, outside, linked)
                self.assertFalse((admin / "report").exists())
                self.assertFalse(outside.exists())
                self.assertEqual(output.write({}, None, outside, root), outside)

    def test_origin_mismatch_and_unidentified_checkout_are_rejected_before_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            initialize(root)
            verify_repository(root, REPOSITORY)
            git(root, "remote", "set-url", "origin", "git@github.com:Example/Review-System.git")
            verify_repository(root, REPOSITORY)
            with patch("weekly_report.cli.resolve_root", return_value=root), \
                    patch("weekly_report.read_github.collect") as collect, \
                    patch("sys.stderr", new_callable=io.StringIO) as stderr:
                self.assertEqual(cli.main(["collect", "--repository", "another/repo", "--now", START]), 1)
                self.assertIn("一致しません", stderr.getvalue())
                git(root, "remote", "remove", "origin")
                self.assertEqual(cli.main(["collect", "--repository", REPOSITORY, "--now", START]), 1)
                self.assertIn("確認できません", stderr.getvalue())
                collect.assert_not_called()

    def test_missing_and_unobserved_events_are_not_rendered_as_zero(self):
        review = records.review({"id": 11, "state": "APPROVED"})
        data = activity_sources([issue(1, START) | {"state": "closed"}], [pull(2, START)],
                                {2: github.evidence("reviews", [review])})
        reference = {"base_ref": "origin/main", "base_sha": "a" * 40,
                     "checkout_sha": "b" * 40, "checkout_dirty": False}
        with tempfile.TemporaryDirectory() as directory, patch("sys.stdout", new_callable=io.StringIO), \
                patch("weekly_report.local.checkout", return_value=reference), \
                patch("weekly_report.read_github.collect", return_value=data):
            parent = Path(directory)
            root = parent / "repo"
            initialize(root)
            for cutoff, expected in [(START, "観測済みの時間帯がありません"),
                                     ("2026-11-23T01:00:00+09:00", "クローズ時刻の欠損")]:
                with self.subTest(cutoff=cutoff), patch("weekly_report.cli.resolve_root", return_value=root), \
                        patch("weekly_report.cli.datetime") as clock:
                    clock.now.return_value = parse_jst(AS_OF)
                    destination = parent / cutoff[11:13]
                    self.assertEqual(cli.main(["collect", "--repository", REPOSITORY, "--now", cutoff,
                                               "--out", str(destination)]), 0)
                    observed = snapshot.load(destination / "snapshot.json")
                    self.assertEqual(observed["observed_at"], AS_OF)
                    self.assertEqual(observed["period"]["observed_until"], cutoff)
                    self.assertIsNone(observed["events"]["closed"])
                    self.assertIsNone(observed["metrics"]["review_submissions"]["value"])
                    if cutoff == START:
                        self.assertIsNone(observed["metrics"]["issues_created"]["value"])
                    html = (destination / "report.html").read_text(encoding="utf-8")
                    closure = html.split("<summary>クローズ Issue</summary>", 1)[1].split("</details>", 1)[0]
                    self.assertNotIn("0 件", closure)
                    self.assertIn(expected, closure)

    def test_missing_local_baselines_and_ledgers_are_unmeasured(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            period = resolve_period(START, END, AS_OF)
            self.assertIsNone(local.maintainability(root)["value"])
            self.assertIsNone(local.owner_proposals(root)["value"])
            self.assertIsNone(local.advisory(root, period)["advisories_created"]["value"])
