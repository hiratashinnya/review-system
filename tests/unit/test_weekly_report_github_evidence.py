"""Fixed-time coverage for report GitHub transitions, identities and progress."""

import json
import unittest

from weekly_report import activity, backlog, github, quality, records, replay, snapshot
from weekly_report.gh_acceptance import acceptance_evidence
from weekly_report.gh_consistency import compare_reads
from weekly_report.gh_issue_transitions import transition, transition_evidence
from weekly_report.gh_pull_files import verify_file_sets
from weekly_report.period import parse_jst, resolve_period
from weekly_report.report_evidence import _item_suffix

REPOSITORY = "example/review-system"
START, END = "2026-01-07", "2026-01-14"
OBSERVED = "2026-01-16"
SHA, BASE, MOVED = "a" * 40, "b" * 40, "c" * 40


def issue(number, state="open", updated=START, closed=None, reason=None, **extra):
    return records.issue({
        "number": number, "created_at": "2026-01-01T00:00:00+09:00",
        "updated_at": parse_jst(updated).isoformat(), "closed_at": parse_jst(closed).isoformat() if closed else None,
        "state": state, "state_reason": reason, "title": f"Issue {number}", "labels": [], "body": None, **extra,
    })


def pull(number, base="main", head=SHA, merged=START, target=REPOSITORY, base_sha=BASE):
    merged_at = parse_jst(merged).isoformat() if merged else None
    end = merged_at or "2026-01-03T00:00:00+09:00"
    return records.pull({
        "id": 100 + number, "number": number, "created_at": "2026-01-03T00:00:00+09:00",
        "state": "closed" if merged else "open", "draft": False, "title": f"PR {number}",
        "updated_at": end, "closed_at": merged_at, "merged_at": merged_at, "head": {"sha": head},
        "base": {"ref": base, "sha": base_sha, "repo": {"full_name": target, "id": 1}},
    })


def event(number, state, date, reason=None):
    return transition({
        "id": number, "event": state, "created_at": parse_jst(date).isoformat(), "state_reason": reason,
    })


class IssueActivityTests(unittest.TestCase):
    def setUp(self):
        self.period = resolve_period(START, END, OBSERVED)

    def test_merge_targets_are_disjoint_and_incomplete_identity_is_unknown(self):
        pushes = [pull(1), pull(2, "stack-base"), pull(3, target=None), pull(4, merged=END), pull(5, None)]
        metrics, events, _ = activity.measure(
            self.period, REPOSITORY, github.evidence("issues", []), github.evidence("pulls", pushes),
        )
        self.assertEqual(metrics["pulls_merged"]["value"], 4)
        self.assertEqual([metrics[f"pulls_merged_{kind}"]["value"] for kind in ("main", "other", "unknown")],
                         [1, 1, 2])
        self.assertEqual([row["number"] for row in events["merged"]], [1, 2, 3, 5])

    def test_close_then_reopen_and_historical_state_reconstruction(self):
        issues = github.evidence("issues", [
            issue(1, "closed", updated="2026-01-15", closed="2026-01-15", reason="completed"),
            issue(2, updated="2026-01-15"),
            issue(3, "closed", updated="2026-01-10", closed="2026-01-10", reason="not_planned"),
        ])
        details = {
            1: github.evidence("events/1", [event(11, "closed", START), event(12, "reopened", "2026-01-08"),
                                            event(13, "closed", "2026-01-15")]),
            2: github.evidence("events/2", [event(21, "closed", "2026-01-09", "completed"),
                                            event(22, "reopened", "2026-01-15")]),
            3: github.evidence("events/3", [event(31, "closed", "2026-01-10")]),
        }
        transitions = transition_evidence(REPOSITORY, issues, details, self.period, compare_reads(issues, issues))
        metrics, events, _ = activity.measure(
            self.period, REPOSITORY, issues, github.evidence("pulls", []), transitions=transitions,
        )
        self.assertEqual([row["id"] for row in events["issue_transitions"]], [11, 12, 21, 31])
        self.assertEqual([row["state_reason"] for row in events["issue_transitions"]],
                         [None, None, "completed", "not_planned"])
        self.assertEqual([row["reason_source"] for row in events["issue_transitions"]],
                         [None, None, "issue_event", "latest_issue_at_same_close"])
        self.assertEqual(metrics["issues_close_events"]["value"], 3)
        self.assertEqual(metrics["issues_reopen_events"]["value"], 1)
        self.assertEqual(metrics["issue_backlog_event_delta"]["value"], -2)
        self.assertIsNone(metrics["issues_close_events_completed"]["value"])
        self.assertEqual(metrics["issues_close_events_completed"]["observed_count"], 1)
        self.assertEqual(metrics["issues_open_before_cutoff"]["value"], 1)
        self.assertEqual(metrics["issues_open_before_cutoff"]["observation_kind"], "reconstructed")
        self.assertEqual(events["issues_open_before_cutoff"], [{"number": 1, "title": "Issue 1"}])

    def test_a_missing_or_mismatched_history_cannot_produce_a_precise_zero(self):
        issues = github.evidence("issues", [issue(1, "closed", closed=START), issue(2)])
        transitions = transition_evidence(
            REPOSITORY, issues, {1: github.evidence("events/1", []), 2: github.evidence("events/2", reason="HTTP 403")},
            self.period, compare_reads(issues, issues),
        )
        self.assertEqual(set(transitions["unavailable_issues"]), {1, 2})
        metrics, events, _ = activity.measure(
            self.period, REPOSITORY, issues, github.evidence("pulls", []), transitions=transitions,
        )
        self.assertIsNone(metrics["issues_reopen_events"]["value"])
        self.assertIsNone(metrics["issues_open_before_cutoff"]["value"])
        self.assertIsNone(events["issue_transitions"])

    def test_effective_close_time_takes_precedence_at_half_open_boundary(self):
        before = "2026-01-13T23:59:59+09:00"
        delayed = "2026-01-14T00:00:01+09:00"
        issues = github.evidence("issues", [
            issue(1, "closed", updated=before, closed=before, reason="completed"),
            issue(2, "closed", updated=END, closed=END, reason="duplicate"),
        ])
        details = {
            1: github.evidence("events/1", [event(11, "closed", delayed)]),
            2: github.evidence("events/2", [event(21, "closed", delayed)]),
        }
        transitions = transition_evidence(REPOSITORY, issues, details, self.period, compare_reads(issues, issues))
        metrics, events, _ = activity.measure(
            self.period, REPOSITORY, issues, github.evidence("pulls", []), transitions=transitions,
        )
        self.assertEqual(metrics["issues_close_events"]["value"], 1)
        self.assertEqual(metrics["issues_close_events_completed"]["value"], 1)
        self.assertEqual(metrics["issues_open_before_cutoff"]["value"], 1)
        self.assertEqual(events["issues_open_before_cutoff"], [{"number": 2, "title": "Issue 2"}])
        captured, = events["issue_transitions"]
        self.assertEqual(captured["effective_at"], parse_jst(before))
        self.assertEqual(captured["effective_source"], "issue.closed_at")
        self.assertEqual(captured["created_at"], parse_jst(delayed))
        self.assertIn(f"クローズ {before}, イベント記録 {delayed}", _item_suffix(captured))
        restored = replay.restore_github(json.loads(snapshot.dumps(transitions)))
        repeated, repeated_events, _ = activity.measure(
            self.period, REPOSITORY, issues, github.evidence("pulls", []), transitions=restored,
        )
        self.assertEqual((repeated, repeated_events), (metrics, events))

    def test_far_delays_and_ambiguous_matching_closes_remain_unmeasured(self):
        now = "2026-01-12T00:00:00+09:00"
        before = "2026-01-12T00:00:01+09:00"
        limit = "2026-01-12T00:00:02+09:00"
        delayed = "2026-01-12T00:00:03+09:00"
        issues = github.evidence("issues", [issue(1, "closed", updated=now, closed=now),
                                            issue(2, "closed", updated=now, closed=now)])
        details = {
            1: github.evidence("events/1", [event(11, "closed", delayed)]),
            2: github.evidence("events/2", [event(21, "closed", now), event(22, "reopened", before),
                                            event(23, "closed", limit)]),
        }
        transitions = transition_evidence(REPOSITORY, issues, details, self.period, compare_reads(issues, issues))
        self.assertIsNone(transitions["rows"])
        self.assertEqual(set(transitions["unavailable_issues"]), {1, 2})


class SuccessiveReadTests(unittest.TestCase):
    def test_same_sha_for_different_pull_is_not_ci_evidence(self):
        target = pull(2, merged=None)
        pull_source = github.evidence("pulls", [target])
        relation = {"id": target["id"], "number": target["number"], "head": {"sha": SHA},
                    "base": {"repo": {"id": 1}}}

        def run(number, association):
            return records.workflow_run({
                "id": number, "name": "tests", "event": "pull_request", "status": "completed", "conclusion": "success",
                "created_at": parse_jst(START).isoformat(), "head_sha": SHA, "pull_requests": [association],
            })

        captured = {
            "pulls": pull_source, "reviews": {2: github.evidence("reviews", [])},
            "head_ci": {SHA: github.evidence("actions", [
                run(10, relation | {"id": 103, "number": 3}), run(11, relation),
                run(12, relation | {"base": {"repo": {"id": 2}}}),
            ])},
            "consistency": {"pulls": compare_reads(pull_source, pull_source)},
        }
        self.assertEqual(quality.matching_heads(captured)[2]["matching_workflow_run_ids"], [11])
        updated = github.evidence("pulls", [pull(2, head=MOVED, merged=None)])
        captured["consistency"]["pulls"] = compare_reads(pull_source, updated)
        self.assertEqual(captured["consistency"]["pulls"]["changed"][0]["after_head_sha"], MOVED)
        self.assertIsNone(quality.matching_heads(captured)[2]["matching_workflow_run_ids"])

    def test_file_sets_require_same_base_and_head(self):
        target = pull(2, merged=None)
        first = github.evidence("pulls", [target])
        files = {2: github.evidence("files/2", [{"filename": "test.py", "status": "modified"}], pages=1)}
        stable = verify_file_sets(files, [target], compare_reads(first, first))[2]
        self.assertEqual((stable["head_sha"], stable["base_sha"]), (SHA, BASE))
        self.assertIsNotNone(stable["rows"])
        updated = github.evidence("pulls", [pull(2, merged=None, base_sha=MOVED)])
        changed = verify_file_sets(files, [target], compare_reads(first, updated))[2]
        self.assertIsNone(changed["rows"])
        self.assertIn("変化", changed["reason"])

    def test_ci_for_covering_period_is_filtered_to_individual_week(self):
        period = resolve_period(START, END, OBSERVED)
        workflows = [{"created_at": parse_jst(when), "conclusion": "success"}
                     for when in ("2026-01-06", START, END)]
        metrics = quality.measure(period, {
            "pulls": github.evidence("pulls", []), "reviews": {},
            "ci": github.evidence("runs", workflows),
        })
        self.assertEqual(metrics["workflow_runs"]["value"], 1)
        self.assertEqual(metrics["workflow_runs"]["by_result"], {"success": 1})


class InitiativeEvidenceTests(unittest.TestCase):
    def test_ac_uses_marked_source_lines_outside_fences(self):
        body = "\n".join((
            "## Context", "- [x] Background", "## Acceptance Criteria", "- [x] Initial item",
            "```md", "- [x] Example in a fence", "```", "1. [ ] Pending", "## End", "- [x] End item",
        ))
        value = acceptance_evidence({"number": 2, "title": "Parent", "body": body})
        self.assertEqual((value["checked"], value["total"]), (1, 2))
        self.assertEqual([row["line"] for row in value["items"]], [4, 8])
        self.assertEqual(len(value["source_body_sha256"]), 64)

    def test_parent_counts_do_not_treat_not_planned_as_completed(self):
        parents = [issue(2, sub_issues_summary={"total": 2}), issue(5, sub_issues_summary={"total": 0})]
        child_source = github.evidence("subissues/2", [
            {"id": 30, "state": "closed", "reason": "completed"}, {"id": 40, "state": "closed", "reason": "not_planned"},
        ])
        sources = {"issues": github.evidence("issues", parents), "pulls": github.evidence("pulls", []),
                   "blocked_by": {}, "sub_issues": {2: child_source}}
        _, inventory = backlog.measure(parse_jst(OBSERVED), sources)
        initiatives = inventory["initiative_progress"]
        self.assertEqual((initiatives[2]["total"], initiatives[2]["completed"], initiatives[2]["other_closed"]),
                         (2, 1, 1))
        self.assertEqual((initiatives[5]["total"], initiatives[5]["children"]), (0, []))
        child_source["rows"].pop()
        _, inventory = backlog.measure(parse_jst(OBSERVED), sources)
        self.assertIsNone(inventory["initiative_progress"][2]["total"])
