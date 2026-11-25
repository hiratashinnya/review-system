"""Fixed calendar, observation-reuse and offline replay regressions."""

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.unit.test_weekly_report import activity_sources, git, initialize, issue, pull
from weekly_report import cli, github, records, replay, snapshot
from weekly_report.batch_periods import resolve_slots
from weekly_report.capture_initiatives import compare_initiatives
from weekly_report.period import COLLECTION_START, WEEKDAYS, parse_jst
from weekly_report.quantities import count, measured

REPOSITORY = "example/review-system"
OBSERVED = "2024-03-07T15:00:00+09:00"


def options(*args):
    return cli.parser().parse_args(["collect", "--repository", REPOSITORY, *args])


class CalendarTests(unittest.TestCase):
    def test_every_week_start_and_default(self):
        instant = parse_jst(OBSERVED)
        for day, name in enumerate(WEEKDAYS):
            with self.subTest(day=name):
                spans, _ = resolve_slots(options("--week-start", name), instant)
                self.assertEqual(spans[0][0].weekday(), day)
                self.assertEqual((spans[0][1] - spans[0][0]).days, 7)
        spans, _ = resolve_slots(options(), instant)
        self.assertEqual(spans[0][0].isoformat(), "2024-03-04T00:00:00+09:00")

    def test_leap_month_and_partial_first_and_last_calendar_weeks(self):
        spans, _ = resolve_slots(options("--month", "2024-02", "--week-start", "wednesday"), parse_jst(OBSERVED))
        self.assertEqual(spans[0][0].isoformat(), "2024-02-01T00:00:00+09:00")
        self.assertEqual(spans[-1][1].isoformat(), "2024-03-01T00:00:00+09:00")
        self.assertEqual([(end - start).days for start, end in spans], [6, 7, 7, 7, 2])

    def test_anchor_used_for_future_or_historic_weeks_and_wall_clock_caps_now(self):
        observed = parse_jst(OBSERVED)
        args = options("--week", "2024-03-03", "--week-start", "sunday", "--weeks", "3", "--now", "2024-03-29")
        spans, cutoff = resolve_slots(args, observed)
        self.assertEqual(cutoff, observed)
        self.assertEqual([start.day for start, _ in spans], [3, 10, 17])
        spans, _ = resolve_slots(options("--weeks", "3", "--week-start", "sunday"), observed)
        self.assertEqual([start.day for start, _ in spans], [18, 25, 3])
        with self.assertRaisesRegex(ValueError, "併用"):
            resolve_slots(options("--week", "2024-03-03", "--month", "2024-03"), observed)


class BatchReplayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)
        self.root = self.parent / "repo"
        initialize(self.root)
        git(self.root, "-c", "user.name=Test", "-c", "user.email=test@example.org",
            "commit", "--allow-empty", "-m", "initial")
        self.addCleanup(patch.stopall)
        patch("weekly_report.cli.resolve_root", return_value=self.root).start()
        self.clock = patch("weekly_report.cli.datetime").start()
        self.clock.now.return_value = parse_jst(OBSERVED)
        patch("sys.stdout", new_callable=io.StringIO).start()
        self.stderr = patch("sys.stderr", new_callable=io.StringIO).start()

    def evidence(self):
        opened = "2024-03-02T00:00:00+09:00"
        submitted = "2024-03-05T05:00:00+09:00"
        head = "b" * 40
        observed_pull = pull(3, opened, head_sha=head) | {"id": 103, "base_repo_id": 5, "base_repository": REPOSITORY}
        identity = {key: observed_pull[key] for key in ("id", "number", "base_repo_id", "head_sha")}
        workflow = {"id": 11, "event": "pull_request", "status": "completed", "conclusion": "success",
                    "created_at": parse_jst(submitted), "head_sha": head, "pull_requests": [identity]}
        inputs = activity_sources([issue(1, "2024-03-02T00:00:00+09:00"),
                                   issue(2, "2024-03-05T00:00:00+09:00")], [observed_pull],
                                  {3: github.evidence("reviews", [records.review({
                                      "id": 31, "state": "APPROVED", "submitted_at": submitted, "commit_id": head,
                                  })])})
        inputs["blocked_by"] = {1: github.evidence("dependencies", []), 2: github.evidence("dependencies", [])}
        inputs["head_ci"] = {head: github.evidence("head/actions", [workflow])}
        inputs["ci"] = github.evidence("actions", [workflow], retrieved_total=1)
        inputs["consistency"] = {kind: {"status": "unchanged", "source": [kind], "reason": None, "changed": []}
                                 for kind in ("issues", "pulls")}
        inputs["transitions"] = github.evidence("events", [], history_start=parse_jst("2024-03-01"))
        inputs["pull_files"] = {3: github.evidence("pulls/files", [{"filename": "x.py", "status": "modified"}])}
        return inputs

    def collect(self, name, *arguments):
        target = self.parent / name
        result = cli.main(["collect", "--repository", REPOSITORY, "--out", str(target), *arguments])
        self.assertEqual(result, 0, self.stderr.getvalue())
        return target

    def test_one_capture_for_split_month_future_rows_and_exact_offline_replay(self):
        with patch("weekly_report.read_github.collect", return_value=self.evidence()) as fetch:
            target = self.collect("month", "--month", "2024-03", "--week-start", "sunday")
        fetch.assert_called_once()
        index = snapshot.load(target / "index.json")
        self.assertEqual([week["status"] for week in index["weeks"]],
                         ["generated", "generated", "not_arrived", "not_arrived", "not_arrived", "not_arrived"])
        self.assertIsNone(index["weeks"][-1]["period"]["observed_until"])
        self.assertIn("week-2024-03-03/report.html", (target / "index.html").read_text())
        first = snapshot.load(target / "week-2024-03-01" / "snapshot.json")
        second_path = target / "week-2024-03-03" / "snapshot.json"
        second = snapshot.load(second_path)
        self.assertEqual(first["metrics"]["issues_created"]["value"], 1)
        self.assertEqual(second["metrics"]["issues_created"]["value"], 1)
        self.assertEqual(second["comparison"]["status"], "incomparable")
        self.assertEqual(first["observation"]["kind"], "retrospective")
        self.assertEqual(first["observation"]["period_end_status"], "not_measured")
        self.assertEqual(first["metrics"]["workflow_runs"]["value"], 0)
        self.assertEqual(second["metrics"]["workflow_runs"]["value"], 1)
        self.assertEqual(second["metrics"]["review_submissions"]["value"], 1)
        self.assertEqual(second["evidence"]["pull_heads"]["3"]["matching_workflow_run_ids"], [11])
        self.assertEqual(second["evidence"]["pull_heads"]["3"]["matching_review_ids"], [31])
        self.assertEqual(second["metrics"]["issues_open_before_cutoff"]["value"], 2)

        destination = self.parent / "replayed"
        with patch("weekly_report.read_github.collect", side_effect=AssertionError("network")), \
                patch("weekly_report.ledger.capture", side_effect=AssertionError("ledger")), \
                patch("weekly_report.local.checkout", side_effect=AssertionError("Git state")):
            arguments = ["replay", "--snapshot", str(second_path), "--out", str(destination)]
            self.assertEqual(cli.main(arguments), 0, self.stderr.getvalue())
            self.assertEqual((destination / "snapshot.json").read_bytes(), second_path.read_bytes())
            self.assertEqual(cli.main(arguments), 1)
        second["metrics"]["issues_created"]["value"] = 125
        self.assertEqual(replay.recalculate(second)["metrics"]["issues_created"]["value"], 1)

    def test_old_saved_observation_keeps_its_time_and_never_reuses_future_state(self):
        self.clock.now.return_value = parse_jst("2024-03-03T00:00:00+09:00")
        dates = ("--start", "2024-03-01", "--end", "2024-03-03")
        with patch("weekly_report.read_github.collect", return_value=self.evidence()):
            saved = self.collect("saved", *dates) / "snapshot.json"
        value = snapshot.load(saved)
        value.pop("replay_inputs")
        saved.write_text(snapshot.dumps(value), encoding="utf-8")
        self.clock.now.return_value = parse_jst(OBSERVED)
        with patch("weekly_report.read_github.collect", return_value=activity_sources([], [])):
            target = self.collect("recreated", *dates, "--observations", str(saved))
            missed = self.collect("uncaptured", *dates)
        recreated = snapshot.load(target / "snapshot.json")
        self.assertEqual(recreated["observation"]["kind"], "saved")
        self.assertEqual(recreated["observation"]["current_collection_at"], OBSERVED)
        self.assertEqual(recreated["observed_at"], "2024-03-03T00:00:00+09:00")
        self.assertEqual(recreated["observation"]["period_end_status"], "measured")
        self.assertEqual(recreated["metrics"]["open_issues"]["value"], 2)
        self.assertEqual(recreated["metrics"]["issues_created"]["value"], 0)
        self.assertEqual(snapshot.load(missed / "snapshot.json")["observation"]["kind"], "retrospective")
        with self.assertRaisesRegex(ValueError, "再集計用の取得証跡"):
            replay.recalculate(value)

    def test_all_future_stays_index_only_without_capture(self):
        with patch("weekly_report.read_github.collect", side_effect=AssertionError("network")):
            target = self.collect("future", "--week", "2024-03-23")
        row = snapshot.load(target / "index.json")["weeks"][0]
        self.assertEqual(row["status"], "not_arrived")
        self.assertIsNone(row["report"])
        self.assertFalse(any(path.is_dir() for path in target.iterdir()))

    def test_reused_observation_replays_its_original_capture(self):
        self.clock.now.return_value = parse_jst("2024-03-03T00:00:00+09:00")
        dates = ("--start", "2024-03-01", "--end", "2024-03-03")
        with patch("weekly_report.read_github.collect", return_value=self.evidence()):
            saved = self.collect("saved", *dates) / "snapshot.json"
        previous = snapshot.load(saved)
        previous["metrics"]["open_issues"]["value"] = 999
        saved.write_text(snapshot.dumps(previous), encoding="utf-8")
        self.clock.now.return_value = parse_jst(OBSERVED)
        with patch("weekly_report.read_github.collect", return_value=activity_sources([], [])):
            target = self.collect("reused", *dates, "--observations", str(saved)) / "snapshot.json"
        value = snapshot.load(target)
        self.assertEqual(value["metrics"]["open_issues"]["value"], 2)
        self.assertEqual(len(value["replay_inputs"]["archive"]["capture"]["github"]["issues"]["rows"]), 2)
        self.assertEqual(snapshot.dumps(replay.recalculate(value)).encode(), target.read_bytes())


class EvidenceStatusTests(unittest.TestCase):
    def test_missing_insufficient_and_undefined_are_distinct_from_zero(self):
        self.assertEqual(count([], "ready", github.evidence("source", []))["status"], "measured")
        self.assertEqual(count(None, "ready", github.evidence("source", reason="failed"))["status"],
                         "not_retrieved")
        self.assertEqual(measured(None, "rate", "source", denominator=0)["status"], "not_calculable")
        self.assertEqual(measured(None, "unclear", "source")["status"], "not_measured")

    def test_initiative_changes_require_both_real_complete_observations(self):
        def report(children, reason=None):
            return {"observation_source": COLLECTION_START, "inventory": {"initiative_progress": {
                1: {"children": None if children is None else [{"id": number + 100, "number": number} for number in children],
                    "total": None if children is None else len(children), "reason": reason},
            }}}
        previous, current = report([2, 3]), report([2, 4, 5])
        delta = compare_initiatives(current, previous, None)["1"]
        self.assertEqual(delta["added"], [{"id": 104, "number": 4}, {"id": 105, "number": 5}])
        self.assertEqual(delta["removed"], [{"id": 103, "number": 3}])
        self.assertEqual(delta["delta"], 1)
        self.assertEqual(compare_initiatives(current, report([2, 3], "完了理由が未知"), None)["1"]["delta"], 1)
        self.assertIsNone(compare_initiatives(current, previous, "後日")["1"]["delta"])
        self.assertIsNone(compare_initiatives(current, report(None, "欠損"), None)["1"]["delta"])
