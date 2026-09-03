"""project_status_sync の遷移表・禁止事項・fail-close を固定する（Issue #460）。

時刻依存 test data の規律（CLAUDE.md / `.claude/rules/04-test-data.md`）: 本 test は
絶対時刻の `generated_at` を使うが、比較相手の「現在時刻」は wall clock ではなく
`now=` 引数で注入する（`planner.check_snapshot` / `cli.run` はどちらも `now` を
受け取る）。したがって時間経過でこの test が反転することはない。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from blocker_gate.model import POLICY_VERSION  # noqa: E402
from blocker_gate.snapshot import REPOSITORY_SNAPSHOT_SCHEMA  # noqa: E402
from project_status_sync import github as gh  # noqa: E402
from project_status_sync.cli import run  # noqa: E402
from project_status_sync.model import (  # noqa: E402
    MAX_SNAPSHOT_AGE_SECONDS,
    OWNER_ONLY_FIELDS,
    Plan,
    ProjectItem,
    ProjectView,
    WRITABLE_TARGETS,
)
from project_status_sync.planner import build_plan, check_snapshot  # noqa: E402
from project_status_sync.report import is_red, render_summary  # noqa: E402

REPO = "owner/repo"
NOW = datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)
PROJECT_ID = "PVT_test"

# 実 Project（review-system Development）と同じ語彙・同じ option id 形を使う。
OPTION_IDS = {
    "Inbox": "f75ad846",
    "Ready": "db901e48",
    "In progress": "47fc9ee4",
    "In review": "59456311",
    "Blocked": "c7fb86f8",
    "Done": "98236657",
}
STATUS_FIELD_ID = "PVTSSF_test"

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "project-status-sync.yml"
BLOCKER_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "blocker-snapshot.yml"


def ref(number: int) -> str:
    return f"{REPO}#{number}"


def issue(
    number: int,
    *,
    state: str = "OPEN",
    blocked_by: tuple[int, ...] = (),
    parent: int | None = None,
    children: tuple[int, ...] = (),
) -> dict:
    return {
        "node_id": f"I_{number}",
        "state": state,
        "blocked_by": [ref(item) for item in blocked_by],
        "parent": None if parent is None else ref(parent),
        "children": [ref(item) for item in children],
        "title": f"issue {number}",
        "url": f"https://github.com/{REPO}/issues/{number}",
    }


def snapshot_raw(
    issues: dict[int, dict],
    *,
    generated_at: str = "2026-09-03T11:55:00Z",
    pages_complete: bool = True,
    errors: tuple[str, ...] = (),
) -> dict:
    return {
        "schema": REPOSITORY_SNAPSHOT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "repository": REPO,
        "generated_at": generated_at,
        "pages_complete": pages_complete,
        "errors": list(errors),
        "issues": {ref(number): value for number, value in issues.items()},
    }


def item(number: int | None, status: str | None, *, item_id: str = "") -> ProjectItem:
    return ProjectItem(
        item_id=item_id or f"PVTI_{number}",
        issue_ref=None if number is None else ref(number),
        status=status,
        content_type="Issue" if number is not None else "PullRequest",
    )


def plan_for(
    raw: dict,
    items: tuple[ProjectItem, ...],
    *,
    now: datetime = NOW,
    max_age_seconds: int = MAX_SNAPSHOT_AGE_SECONDS,
) -> Plan:
    parsed, abort = check_snapshot(raw, now=now, max_age_seconds=max_age_seconds)
    if abort is not None:
        return Plan(abort=abort)
    assert parsed is not None
    return build_plan(parsed, items, REPO)


class FakeClient:
    """Project への書き込み回数と引数を数えるだけの client。"""

    def __init__(self, items: tuple[ProjectItem, ...], *, fail_at: int | None = None) -> None:
        self.view = ProjectView(
            project_id=PROJECT_ID,
            number=1,
            title="review-system Development",
            status_field_id=STATUS_FIELD_ID,
            status_option_ids=dict(OPTION_IDS),
            items=items,
        )
        self.fetch_calls = 0
        self.writes: list[tuple[str, str, str, str]] = []
        self._fail_at = fail_at

    def fetch_project(self, project_id, repository, expected_number=None):
        self.fetch_calls += 1
        return self.view

    def set_status(self, project_id, item_id, field_id, option_id):
        if self._fail_at is not None and len(self.writes) == self._fail_at:
            raise gh.ProjectSyncApiError("API_UNAVAILABLE")
        self.writes.append((project_id, item_id, field_id, option_id))


class TransitionTableTest(unittest.TestCase):
    def test_ready_with_open_blocker_becomes_blocked(self):
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)})
        plan = plan_for(raw, (item(1, "Ready"),))
        self.assertIsNone(plan.abort)
        self.assertEqual(
            [(c.issue_ref, c.from_status, c.to_status, c.reason) for c in plan.changes],
            [(ref(1), "Ready", "Blocked", "OPEN_BLOCKER")],
        )

    def test_inbox_with_open_blocker_becomes_blocked(self):
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)})
        plan = plan_for(raw, (item(1, "Inbox"),))
        self.assertEqual([c.to_status for c in plan.changes], ["Blocked"])

    def test_blocked_without_blocker_returns_to_ready(self):
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2, state="CLOSED_COMPLETED")})
        plan = plan_for(raw, (item(1, "Blocked"),))
        self.assertEqual(
            [(c.from_status, c.to_status, c.reason) for c in plan.changes],
            [("Blocked", "Ready", "BLOCKER_CLEARED")],
        )

    def test_transitive_open_blocker_blocks(self):
        raw = snapshot_raw(
            {1: issue(1, blocked_by=(2,)), 2: issue(2, blocked_by=(3,)), 3: issue(3)}
        )
        plan = plan_for(raw, (item(1, "Ready"),))
        self.assertEqual([c.to_status for c in plan.changes], ["Blocked"])

    def test_closed_blocker_stops_the_transitive_walk(self):
        """A -> B(closed) -> C(open) のとき A はブロックしない（evaluator 準拠）。"""
        raw = snapshot_raw(
            {
                1: issue(1, blocked_by=(2,)),
                2: issue(2, state="CLOSED_COMPLETED", blocked_by=(3,)),
                3: issue(3),
            }
        )
        self.assertEqual(plan_for(raw, (item(1, "Ready"),)).changes, ())
        # 同じグラフで Blocked に居るなら Ready へ戻る（ブロックされていないため）。
        self.assertEqual(
            [c.to_status for c in plan_for(raw, (item(1, "Blocked"),)).changes], ["Ready"]
        )

    def test_open_parent_with_open_child_is_not_blocked(self):
        raw = snapshot_raw({1: issue(1, children=(2,)), 2: issue(2, parent=1)})
        plan = plan_for(raw, (item(1, "Ready"), item(2, "Ready")))
        self.assertEqual(plan.changes, ())
        self.assertEqual(plan.warnings, ())

    def test_no_diff_produces_no_change(self):
        raw = snapshot_raw({1: issue(1), 2: issue(2, blocked_by=(3,)), 3: issue(3)})
        plan = plan_for(raw, (item(1, "Ready"), item(2, "Blocked")))
        self.assertEqual(plan.changes, ())
        self.assertEqual(plan.warnings, ())

    def test_done_and_closed_issues_are_out_of_scope(self):
        raw = snapshot_raw(
            {
                1: issue(1, blocked_by=(3,)),
                2: issue(2, state="CLOSED_COMPLETED", blocked_by=(3,)),
                3: issue(3),
            }
        )
        plan = plan_for(raw, (item(1, "Done"), item(2, "Ready")))
        self.assertEqual(plan.changes, ())
        self.assertEqual(plan.skipped, ())
        self.assertEqual(plan.out_of_scope, 2)

    def test_never_targets_done(self):
        self.assertEqual(WRITABLE_TARGETS, frozenset({"Ready", "Blocked"}))
        self.assertNotIn("Done", WRITABLE_TARGETS)


class ActiveItemTest(unittest.TestCase):
    def test_in_progress_with_blocker_warns_without_writing(self):
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)})
        for status in ("In progress", "In review"):
            with self.subTest(status=status):
                plan = plan_for(raw, (item(1, status),))
                self.assertEqual(plan.changes, ())
                self.assertEqual([w.code for w in plan.warnings], ["ACTIVE_ITEM_BLOCKED"])

    def test_in_progress_without_blocker_is_silent(self):
        raw = snapshot_raw({1: issue(1)})
        plan = plan_for(raw, (item(1, "In progress"),))
        self.assertEqual(plan.changes, ())
        self.assertEqual(plan.warnings, ())


class ClosureInvariantTest(unittest.TestCase):
    def test_closed_parent_with_open_child_warns_and_blocks_the_write(self):
        raw = snapshot_raw(
            {
                1: issue(1, state="CLOSED_COMPLETED", children=(2,)),
                2: issue(2, parent=1, blocked_by=(3,)),
                3: issue(3),
            }
        )
        plan = plan_for(raw, (item(2, "Ready"),))
        self.assertIsNone(plan.abort)
        # ブロッカーがあるので通常なら Blocked を書くが、グラフ不整合なので書かない。
        self.assertEqual(plan.changes, ())
        self.assertEqual([w.code for w in plan.warnings], ["CLOSURE_OPEN_DESCENDANT"])


class FailCloseTest(unittest.TestCase):
    def test_degraded_snapshot_aborts_without_planning(self):
        for kwargs in ({"pages_complete": False}, {"errors": ("API_UNAVAILABLE",)}):
            with self.subTest(kwargs=kwargs):
                raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)}, **kwargs)
                plan = plan_for(raw, (item(1, "Ready"),))
                self.assertIsNotNone(plan.abort)
                self.assertEqual(plan.abort.code, "SNAPSHOT_DEGRADED")
                self.assertEqual(plan.changes, ())

    def test_stale_snapshot_aborts(self):
        stale = (NOW - timedelta(seconds=MAX_SNAPSHOT_AGE_SECONDS + 1)).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)}, generated_at=stale)
        plan = plan_for(raw, (item(1, "Ready"),))
        self.assertEqual(plan.abort.code, "SNAPSHOT_STALE")
        self.assertEqual(plan.changes, ())

    def test_exactly_at_the_age_limit_is_still_fresh(self):
        edge = (NOW - timedelta(seconds=MAX_SNAPSHOT_AGE_SECONDS)).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)}, generated_at=edge)
        plan = plan_for(raw, (item(1, "Ready"),))
        self.assertIsNone(plan.abort)
        self.assertEqual([c.to_status for c in plan.changes], ["Blocked"])

    def test_unknown_issue_state_aborts_everything(self):
        raw = snapshot_raw(
            {
                1: issue(1, blocked_by=(2,)),
                2: issue(2, state="UNKNOWN"),
                4: issue(4, blocked_by=(5,)),
                5: issue(5),
            }
        )
        plan = plan_for(raw, (item(1, "Ready"), item(4, "Ready")))
        self.assertEqual(plan.abort.code, "ISSUE_STATE_UNKNOWN")
        self.assertEqual(plan.changes, ())

    def test_broken_snapshot_schema_aborts(self):
        plan = plan_for({"schema": "nope"}, (item(1, "Ready"),))
        self.assertEqual(plan.abort.code, "SNAPSHOT_INVALID")

    def test_inconsistent_graph_aborts(self):
        # 子が親を指すのに親が子を持たない＝RELATION_INCONSISTENT。
        raw = snapshot_raw({1: issue(1), 2: issue(2, parent=1)})
        plan = plan_for(raw, (item(2, "Ready"),))
        self.assertEqual(plan.abort.code, "GRAPH_UNREADABLE")
        self.assertEqual(plan.changes, ())


class SkippedTest(unittest.TestCase):
    def test_item_missing_from_snapshot_is_skipped(self):
        raw = snapshot_raw({1: issue(1)})
        plan = plan_for(raw, (item(9, "Ready"),))
        self.assertIsNone(plan.abort)
        self.assertEqual([(s.code, s.issue_ref) for s in plan.skipped], [("NOT_IN_SNAPSHOT", ref(9))])
        self.assertEqual(plan.changes, ())

    def test_unset_status_is_skipped(self):
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)})
        plan = plan_for(raw, (item(1, None),))
        self.assertEqual([s.code for s in plan.skipped], ["STATUS_UNSET"])
        self.assertEqual(plan.changes, ())

    def test_unknown_status_is_skipped(self):
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)})
        plan = plan_for(raw, (item(1, "Icebox"),))
        self.assertEqual([s.code for s in plan.skipped], ["STATUS_UNKNOWN"])
        self.assertEqual(plan.changes, ())

    def test_non_issue_content_is_out_of_scope(self):
        raw = snapshot_raw({1: issue(1)})
        plan = plan_for(raw, (item(None, "Ready", item_id="PVTI_pr"),))
        self.assertEqual(plan.skipped, ())
        self.assertEqual(plan.out_of_scope, 1)

    def test_skipped_alone_is_not_red(self):
        report = {
            "abort": None,
            "warnings": [],
            "skipped": [{"code": "NOT_IN_SNAPSHOT", "issue_ref": ref(9), "detail": ""}],
        }
        self.assertFalse(is_red(report))


class CliTest(unittest.TestCase):
    def _run(self, raw, items, *, apply_mode=False, client=None, now=NOW, extra=()):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = Path(tmp) / "snapshot.json"
            report_path = Path(tmp) / "out" / "report.json"
            snapshot_path.write_text(json.dumps(raw), encoding="utf-8")
            fake = client if client is not None else FakeClient(items)
            argv = [
                "sync",
                "--repository", REPO,
                "--project-id", PROJECT_ID,
                "--project-number", "1",
                "--snapshot", str(snapshot_path),
                "--report", str(report_path),
                *extra,
            ]
            if apply_mode:
                argv.append("--apply")
            stdout, stderr = io.StringIO(), io.StringIO()
            code = run(
                argv,
                stdout=stdout,
                stderr=stderr,
                client_factory=lambda: fake,
                now=now,
            )
            report = (
                json.loads(report_path.read_text(encoding="utf-8"))
                if report_path.exists()
                else None
            )
            return code, report, stdout.getvalue(), fake

    def test_dry_run_never_writes(self):
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)})
        code, report, summary, fake = self._run(raw, (item(1, "Ready"),))
        self.assertEqual(code, 0)
        self.assertEqual(report["mode"], "dry-run")
        self.assertEqual(len(report["planned"]), 1)
        self.assertEqual(report["applied"], [])
        self.assertEqual(fake.writes, [])
        self.assertIn("dry-run", summary)

    def test_apply_writes_only_the_status_field(self):
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)})
        code, report, _, fake = self._run(raw, (item(1, "Ready"),), apply_mode=True)
        self.assertEqual(code, 0)
        self.assertEqual(report["mode"], "apply")
        self.assertEqual(
            fake.writes, [(PROJECT_ID, "PVTI_1", STATUS_FIELD_ID, OPTION_IDS["Blocked"])]
        )
        self.assertEqual([row["to"] for row in report["applied"]], ["Blocked"])

    def test_apply_never_sends_the_done_option(self):
        raw = snapshot_raw(
            {
                1: issue(1, blocked_by=(4,)),
                2: issue(2),
                3: issue(3, state="CLOSED_COMPLETED"),
                4: issue(4),
            }
        )
        items = (item(1, "Ready"), item(2, "Blocked"), item(3, "Ready"))
        _, _, _, fake = self._run(raw, items, apply_mode=True)
        sent = {row[3] for row in fake.writes}
        self.assertNotIn(OPTION_IDS["Done"], sent)
        self.assertTrue(sent <= {OPTION_IDS["Ready"], OPTION_IDS["Blocked"]})

    def test_no_write_api_call_when_there_is_no_diff(self):
        raw = snapshot_raw({1: issue(1)})
        code, report, _, fake = self._run(raw, (item(1, "Ready"),), apply_mode=True)
        self.assertEqual(code, 0)
        self.assertEqual(fake.writes, [])
        self.assertEqual(report["planned"], [])

    def test_degraded_snapshot_does_not_even_read_the_project(self):
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)}, pages_complete=False)
        code, report, _, fake = self._run(raw, (item(1, "Ready"),), apply_mode=True)
        self.assertEqual(code, 20)
        self.assertEqual(fake.fetch_calls, 0)
        self.assertEqual(fake.writes, [])
        self.assertEqual(report["abort"]["code"], "SNAPSHOT_DEGRADED")

    def test_stale_snapshot_is_red_and_writes_nothing(self):
        stale = (NOW - timedelta(hours=3)).isoformat(timespec="seconds").replace("+00:00", "Z")
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)}, generated_at=stale)
        code, report, _, fake = self._run(raw, (item(1, "Ready"),), apply_mode=True)
        self.assertEqual(code, 20)
        self.assertEqual(fake.writes, [])
        self.assertEqual(report["abort"]["code"], "SNAPSHOT_STALE")

    def test_warning_is_red_but_the_report_is_still_written(self):
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)})
        code, report, summary, _ = self._run(raw, (item(1, "In progress"),), apply_mode=True)
        self.assertEqual(code, 20)
        self.assertIsNotNone(report)
        self.assertEqual([row["code"] for row in report["warnings"]], ["ACTIVE_ITEM_BLOCKED"])
        self.assertIn("ACTIVE_ITEM_BLOCKED", summary)

    def test_skipped_items_are_reported_but_not_red(self):
        raw = snapshot_raw({1: issue(1)})
        code, report, summary, _ = self._run(
            raw, (item(9, "Ready"), item(1, None)), apply_mode=True
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            sorted(row["code"] for row in report["skipped"]),
            ["NOT_IN_SNAPSHOT", "STATUS_UNSET"],
        )
        self.assertIn("skipped（2件", summary)
        self.assertIn("NOT_IN_SNAPSHOT", summary)

    def test_missing_token_aborts_as_project_unreadable(self):
        raw = snapshot_raw({1: issue(1)})

        def factory():
            raise gh.ProjectSyncApiError("TOKEN_MISSING")

        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = Path(tmp) / "snapshot.json"
            report_path = Path(tmp) / "report.json"
            snapshot_path.write_text(json.dumps(raw), encoding="utf-8")
            code = run(
                [
                    "sync",
                    "--repository", REPO,
                    "--project-id", PROJECT_ID,
                    "--snapshot", str(snapshot_path),
                    "--report", str(report_path),
                    "--apply",
                ],
                stdout=io.StringIO(),
                stderr=io.StringIO(),
                client_factory=factory,
                now=NOW,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(code, 20)
        self.assertEqual(report["abort"], {"code": "PROJECT_UNREADABLE", "detail": "TOKEN_MISSING"})

    def test_apply_failure_keeps_the_successful_writes_in_the_report(self):
        raw = snapshot_raw(
            {
                1: issue(1, blocked_by=(3,)),
                2: issue(2, blocked_by=(3,)),
                3: issue(3),
            }
        )
        items = (item(1, "Ready"), item(2, "Ready"))
        fake = FakeClient(items, fail_at=1)
        code, report, _, _ = self._run(raw, items, apply_mode=True, client=fake)
        self.assertEqual(code, 20)
        self.assertEqual(report["abort"]["code"], "APPLY_FAILED")
        self.assertEqual(len(report["applied"]), 1)
        self.assertEqual(len(fake.writes), 1)

    def test_summary_shows_the_planned_diff(self):
        raw = snapshot_raw({1: issue(1, blocked_by=(2,)), 2: issue(2)})
        _, report, summary, _ = self._run(raw, (item(1, "Ready"),))
        self.assertIn("Ready", summary)
        self.assertIn("Blocked", summary)
        self.assertIn(ref(1), summary)
        self.assertEqual(render_summary(report), summary)


class OwnerOnlyFieldTest(unittest.TestCase):
    def test_queries_touch_only_the_status_field(self):
        for query in (gh._PROJECT_QUERY, gh._UPDATE_MUTATION):
            for name in OWNER_ONLY_FIELDS:
                self.assertNotIn(name, query)
        self.assertEqual(gh._PROJECT_QUERY.count('name:"Status"'), 2)
        self.assertNotIn('name:"', gh._UPDATE_MUTATION)


class WorkflowTest(unittest.TestCase):
    def test_workflow_publishes_before_failing(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        publish = text.index("Publish the report to the orphan branch")
        fail = text.index("Fail the job when the sync reported a problem")
        self.assertLess(publish, fail)

    def test_workflow_writes_the_step_summary_and_uses_apply(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('>> "$GITHUB_STEP_SUMMARY"', text)
        self.assertIn("--apply", text)
        self.assertIn("PROJECT_SYNC_TOKEN", text)

    def test_workflow_does_not_use_pull_request_target(self):
        """secret を露出させる trigger を持たない（コメント中の言及は対象外）。"""
        text = WORKFLOW.read_text(encoding="utf-8")
        triggers = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertNotIn("pull_request_target", triggers)
        self.assertNotIn("pull_request", triggers)

    def test_blocker_snapshot_workflow_stays_independent(self):
        text = BLOCKER_WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("project_status_sync", text)
        self.assertNotIn("PROJECT_SYNC_TOKEN", text)


class IssuePipelineSkillTest(unittest.TestCase):
    def test_dispatch_step_sets_in_progress_and_restores_ready_on_stop(self):
        text = (REPO_ROOT / ".ai" / "skills" / "issue-pipeline" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        section = text.split("### ②-a 実装", 1)[1].split("### ②-b", 1)[0]
        self.assertIn("In progress", section)
        self.assertIn("ALLOW", section)
        self.assertIn("STOP", section)
        self.assertIn("Ready", section)


if __name__ == "__main__":
    unittest.main()
