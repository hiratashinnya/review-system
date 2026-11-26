"""Check transfer boundaries and retained cohort evidence for historical stock."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.unit.test_weekly_report import activity_sources
from tests.unit.test_weekly_report_github_evidence import END, OBSERVED, REPOSITORY, START, event, issue
from weekly_report import activity, github, history, ledger, render, replay, snapshot
from weekly_report.gh_consistency import compare_reads
from weekly_report.gh_issue_transitions import transition_evidence
from weekly_report.period import parse_jst, resolve_period


class TransferCoverageTests(unittest.TestCase):
    def test_earlier_transfer_is_reconstructable_only_in_retrievable_cohort(self):
        period = resolve_period(START, END, OBSERVED)
        issues = github.evidence("issues", [issue(1, updated="2026-01-12")])
        details = {1: github.evidence("events/1", [event(11, "transferred", "2026-01-12")])}
        history = transition_evidence(REPOSITORY, issues, details, period, compare_reads(issues, issues))
        metrics, events, _ = activity.measure(
            period, REPOSITORY, issues, github.evidence("pulls", []), transitions=history,
        )
        stock = metrics["issues_open_before_cutoff"]
        self.assertEqual(stock["value"], 1)
        self.assertIn("現在の一覧にない Issue は復元できません", stock["scope"])
        transfer, = events["issue_transfers"]
        self.assertEqual(transfer["created_at"], parse_jst("2026-01-12"))
        self.assertEqual((transfer["number"], transfer["repository"], transfer["id"]), (1, REPOSITORY, 11))

    def test_later_transfer_cannot_be_counted_at_earlier_cutoff(self):
        period = resolve_period(START, END, OBSERVED)
        issues = github.evidence("issues", [issue(1, updated=END), issue(2)])
        details = {1: github.evidence("events/1", [event(11, "transferred", END)]),
                   2: github.evidence("events/2", [])}
        history = transition_evidence(REPOSITORY, issues, details, period, compare_reads(issues, issues))
        pulls = github.evidence("pulls", [])
        metrics, events, _ = activity.measure(period, REPOSITORY, issues, pulls, transitions=history)
        stock = metrics["issues_open_before_cutoff"]
        self.assertIsNone(stock["value"])
        self.assertEqual(stock["status"], "not_measured")
        self.assertEqual(stock["uncertain_issue_numbers"], [1])
        self.assertEqual(stock["observed_count"], 1)
        self.assertEqual(events["issues_open_before_cutoff_known"], [{"number": 2, "title": "Issue 2"}])
        self.assertEqual(events["issue_transfers"], [])
        restored = replay.restore_github(json.loads(snapshot.dumps(history)))
        self.assertEqual(activity.measure(period, REPOSITORY, issues, pulls, transitions=restored)[:2],
                         (metrics, events))
        restored.pop("transfer_events")
        legacy, _, _ = activity.measure(period, REPOSITORY, issues, pulls, transitions=restored)
        self.assertIn("移管を確認できる履歴が保存されていません", legacy["issues_open_before_cutoff"]["reason"])

    def test_snapshot_and_offline_replay_distinguish_complete_and_partial_transfers(self):
        period = resolve_period(START, END, OBSERVED)
        reference = {"base_ref": "origin/main", "base_sha": None, "checkout_sha": "a" * 40, "checkout_dirty": False}
        with TemporaryDirectory() as directory:
            root = Path(directory)
            capture = {"reference": reference, "collection_period": period.as_dict(),
                       "ledger": ledger.capture(root), "main_history": history.capture(root, None)}
        for failed, found in ((False, False), (True, False), (True, True)):
            with self.subTest(failed=failed, found=found):
                inputs = activity_sources([issue(1), issue(2)], [])
                rows = [event(11, "transferred", START), event(12, "transferred", END)] if found else []
                details = {1: github.evidence("events/1", rows), 2: github.evidence("events/2", [])}
                if failed:
                    details[2] = github.evidence("events/2", reason="HTTP 403")
                issues = inputs["issues"]
                inputs["transitions"] = transition_evidence(
                    REPOSITORY, issues, details, period, compare_reads(issues, issues),
                )
                data = snapshot.assemble(REPOSITORY, period, capture | {"github": inputs},
                                         parse_jst(OBSERVED), None, None)
                encoded = snapshot.dumps(data)
                saved = json.loads(encoded)
                saved_events = saved["events"]
                self.assertEqual(saved_events["issue_transfers"], None if failed else [])
                report = render.report(saved, None)
                section = report.split("<summary>期間内の移管イベント証跡</summary>", 1)[1].split("</details>", 1)[0]
                self.assertEqual("0 件" in section, not failed)
                self.assertEqual('class="missing">未取得' in section, failed)
                self.assertEqual("HTTP 403" in section, failed)
                self.assertEqual("#1 Issue 1" in section, found)
                self.assertEqual([row["id"] for row in saved_events.get("issue_transfers_known", [])],
                                 [11] if found else [])
                if failed:
                    self.assertIn("HTTP 403", saved_events["issue_transfers_reason"])
                recalculated = replay.recalculate(saved)
                self.assertEqual(snapshot.dumps(recalculated), encoded)
                self.assertEqual(render.report(json.loads(snapshot.dumps(recalculated)), None), report)
