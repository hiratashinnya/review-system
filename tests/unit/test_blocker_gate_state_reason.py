"""Issue #466: closed Issue の state reason 写像と、未知 reason の検知。

`stateReason: DUPLICATE` / `null` / 将来 GitHub が追加する未知値のいずれでも、
blocker gate と Project Status 同期が `ISSUE_STATE_UNKNOWN` で止まらないことを固定する。
併せて、写像の一次情報源が REST 経路と GraphQL 経路で分岐していないこと（AC4）と、
未知 reason の出現が判定を止めずに運用者へ届くこと（AC5）を固定する。

依存仕様: `docs/methods/blocker-gate-pre-use-policy.md` §2.2（policy 2.0）。
"""

from datetime import datetime, timezone
from io import StringIO
import json
import unittest
from unittest.mock import patch

from blocker_gate.cli import format_unrecognized_state_reasons
from blocker_gate.cli import run as run_cli
from blocker_gate.github import GitHubCollector
from blocker_gate.model import (
    KNOWN_STATE_REASONS,
    POLICY_VERSION,
    IssueClass,
    classify_issue_state,
)
from blocker_gate.resolver import evaluate_snapshot
from blocker_gate.snapshot import (
    REPOSITORY_SNAPSHOT_SCHEMA,
    parse_repository_snapshot,
    project_issue_snapshot,
)
from project_status_sync.model import BLOCKED, READY, ProjectItem
from project_status_sync.planner import build_plan

REPOSITORY = "example/repo"
# 生成時刻と wall clock の比較は `now=` 相当の凍結で制御する（CLAUDE.md
# 「時刻依存 test data の規律」/ Issue #344）。素の datetime.now は使わない。
GENERATED_AT = "2026-08-12T00:00:00Z"
EVALUATED_AT = datetime(2026, 8, 12, 0, 0, 1, tzinfo=timezone.utc)


class FrozenClockMixin:
    """`evaluate_snapshot` の `completed_at` は wall clock 読み取りであり、
    固定した `generated_at` と `fetched_at <= completed_at` で比較される。
    凍結しないと実行時刻次第で別経路（contract error）へ滑る（Issue #344）。
    """

    def setUp(self):
        super().setUp()
        for target in ("blocker_gate.resolver.datetime", "blocker_gate.github.datetime"):
            patcher = patch(target, wraps=datetime)
            clock = patcher.start()
            clock.now.return_value = EVALUATED_AT
            self.addCleanup(patcher.stop)


def issue_entry(number, *, state="OPEN", blocked_by=(), children=(), parent=None):
    return {
        "node_id": f"I_{number}",
        "state": state,
        "blocked_by": [f"{REPOSITORY}#{item}" for item in blocked_by],
        "parent": None if parent is None else f"{REPOSITORY}#{parent}",
        "children": [f"{REPOSITORY}#{item}" for item in children],
        "title": f"issue {number}",
        "url": f"https://github.com/{REPOSITORY}/issues/{number}",
    }


def repository_snapshot(entries):
    return {
        "schema": REPOSITORY_SNAPSHOT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "repository": REPOSITORY,
        "generated_at": GENERATED_AT,
        "pages_complete": True,
        "errors": [],
        "issues": {f"{REPOSITORY}#{number}": entry for number, entry in entries.items()},
    }


def graphql_node(number, *, state="OPEN", state_reason=None, blocked_by=()):
    return {
        "id": f"I_{number}",
        "number": number,
        "state": state,
        "stateReason": state_reason,
        "title": f"issue {number}",
        "url": f"https://github.com/{REPOSITORY}/issues/{number}",
        "parent": None,
        "blockedBy": {
            "pageInfo": {"hasNextPage": False},
            "nodes": [
                {"number": item, "repository": {"nameWithOwner": REPOSITORY}}
                for item in blocked_by
            ],
        },
        "subIssues": {"pageInfo": {"hasNextPage": False}, "nodes": []},
    }


class GraphQLTransport:
    """GraphQL 1 page だけ返す fake（REST は使わない）。"""

    def __init__(self, nodes):
        self.nodes = list(nodes)

    def get(self, url, headers):  # pragma: no cover - 呼ばれたら設計違反
        raise AssertionError("repository snapshot は GraphQL だけで取得する")

    def post(self, url, headers, body):
        payload = {
            "data": {
                "repository": {
                    "nameWithOwner": REPOSITORY,
                    "issues": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": self.nodes,
                    },
                }
            }
        }
        return 200, {}, json.dumps(payload).encode("utf-8")


class RestTransport:
    """`collect_issue` が使う REST endpoint だけを返す fake。

    GraphQL 経路と同じ Issue を **REST の小文字語彙**で返し、両経路が同じ
    `IssueClass` に落ちることを確かめるために使う（Issue #466 AC4）。
    """

    def __init__(self, issues, blocked_by=None):
        self.issues = dict(issues)
        self.blocked_by = dict(blocked_by or {})

    def get(self, url, headers):
        path = url.split("api.github.com", 1)[1].split("?", 1)[0]
        parts = path.strip("/").split("/")
        number = int(parts[4])
        if parts[5:] == ["dependencies", "blocked_by"]:
            targets = [{"number": item} for item in self.blocked_by.get(number, ())]
            return 200, {}, json.dumps(targets).encode("utf-8")
        if len(parts) > 5:
            return 200, {}, b"[]"
        state, reason = self.issues[number]
        body = {
            "number": number,
            "node_id": f"I_{number}",
            "state": state,
            "state_reason": reason,
            "parent_issue_url": None,
        }
        return 200, {}, json.dumps(body).encode("utf-8")

    def post(self, url, headers, body):  # pragma: no cover - 呼ばれたら設計違反
        raise AssertionError("collect_issue は REST だけを使う")


class ClassifierTests(unittest.TestCase):
    """写像の正本（`blocker_gate.model.classify_issue_state`）そのもの。"""

    def test_open_and_recognized_closed_reasons_are_unchanged(self):
        cases = (
            (("OPEN", None), IssueClass.OPEN),
            (("OPEN", "REOPENED"), IssueClass.OPEN),
            (("CLOSED", "COMPLETED"), IssueClass.CLOSED_COMPLETED),
            (("CLOSED", "NOT_PLANNED"), IssueClass.CLOSED_NOT_PLANNED),
        )
        for (state, reason), expected in cases:
            with self.subTest(state=state, reason=reason):
                self.assertEqual(classify_issue_state(state, reason), (expected, None))

    def test_closed_with_any_other_reason_is_closed_other(self):
        """DUPLICATE / null / 未知の新 reason はすべて解決済み側へ倒す。"""
        for reason in (None, "DUPLICATE", "REOPENED", "SOME_FUTURE_REASON"):
            with self.subTest(reason=reason):
                issue_class, _ = classify_issue_state("CLOSED", reason)
                self.assertIs(issue_class, IssueClass.CLOSED_OTHER)

    def test_unrecognized_reason_is_reported_but_recognized_ones_are_not(self):
        """未知値を分類はしないが、増えたことは検知する（AC5）。"""
        self.assertEqual(
            classify_issue_state("CLOSED", "SOME_FUTURE_REASON"),
            (IssueClass.CLOSED_OTHER, "SOME_FUTURE_REASON"),
        )
        # その state と両立する既知語彙（DUPLICATE を含む）と reason 欠落は
        # 検知対象ではない。そうしないと duplicate クローズ1件で警告が
        # 常時鳴りっぱなしになる。
        for state, reason in (
            ("CLOSED", None),
            ("CLOSED", "COMPLETED"),
            ("CLOSED", "NOT_PLANNED"),
            ("CLOSED", "DUPLICATE"),
            ("OPEN", None),
            ("OPEN", "REOPENED"),
        ):
            with self.subTest(state=state, reason=reason):
                self.assertIsNone(classify_issue_state(state, reason)[1])

    def test_contradictory_state_and_reason_stays_detectable(self):
        """F-466-02: `CLOSED`+`REOPENED` を無警告で吸収しない。

        policy 1.2 ではこの矛盾応答が `UNKNOWN` → `ERROR` として必ず表に出ていた。
        2.0 は判定を `CLOSED_OTHER`（解決済み）に倒すが、**観測手段までは消さない**。
        """
        issue_class, telemetry = classify_issue_state("CLOSED", "REOPENED")
        self.assertIs(issue_class, IssueClass.CLOSED_OTHER)
        self.assertEqual(telemetry, "CLOSED+REOPENED")
        # 既知語彙であること自体は変えていない（語彙の増加ではなく矛盾として拾う）。
        self.assertIn("REOPENED", KNOWN_STATE_REASONS)
        # REST の小文字語彙でも同じ token になる（AC4）。
        self.assertEqual(classify_issue_state("closed", "reopened")[1], "CLOSED+REOPENED")
        # 一方 DUPLICATE は引き続き鳴らない（鳴りっぱなしの警告を作らない）。
        self.assertIsNone(classify_issue_state("CLOSED", "DUPLICATE")[1])

    def test_unreadable_state_or_reason_stays_unknown(self):
        """fail-close は弱めない。読めないものは `UNKNOWN` のまま。"""
        for state, reason in (
            (None, "COMPLETED"),
            ("", None),
            ("ARCHIVED", None),
            (True, None),
            (10, None),
            ("CLOSED", 7),
            ("CLOSED", ["COMPLETED"]),
        ):
            with self.subTest(state=state, reason=reason):
                self.assertEqual(
                    classify_issue_state(state, reason), (IssueClass.UNKNOWN, None)
                )

    def test_reason_type_check_precedes_the_state_branch(self):
        """F-466-01: policy §2.2 の表は上から順に適用する（行2 が行3 に優先）。

        `state` が読めていても `state reason` が文字列でも null でもなければ
        応答が矛盾しているので `UNKNOWN`。`OPEN` 行へは到達しない。
        """
        for state in ("OPEN", "open", "CLOSED", "closed"):
            for reason in (7, ["COMPLETED"], {"value": "COMPLETED"}, object()):
                with self.subTest(state=state, reason=reason):
                    self.assertEqual(
                        classify_issue_state(state, reason),
                        (IssueClass.UNKNOWN, None),
                    )

    def test_rest_and_graphql_casing_land_on_the_same_class(self):
        """判定の一次情報源を経路ごとに分岐させない（AC4・大小文字だけ吸収する）。"""
        pairs = (
            (("open", None), ("OPEN", None)),
            (("closed", "completed"), ("CLOSED", "COMPLETED")),
            (("closed", "not_planned"), ("CLOSED", "NOT_PLANNED")),
            (("closed", "duplicate"), ("CLOSED", "DUPLICATE")),
            (("closed", None), ("CLOSED", None)),
        )
        for rest, graphql in pairs:
            with self.subTest(rest=rest):
                self.assertEqual(classify_issue_state(*rest), classify_issue_state(*graphql))


class CollectorPathTests(FrozenClockMixin, unittest.TestCase):
    """REST collector と GraphQL collector が同じ答えを返すこと（AC4）。"""

    def test_duplicate_closed_issue_is_closed_other_on_both_paths(self):
        graphql = GitHubCollector(
            "token", GraphQLTransport([graphql_node(9, state="CLOSED", state_reason="DUPLICATE")])
        ).collect_repository(REPOSITORY)
        rest = GitHubCollector(
            "token", RestTransport({9: ("closed", "duplicate")})
        ).collect_issue(REPOSITORY, 9)
        self.assertEqual(
            graphql["issues"][f"{REPOSITORY}#9"]["state"],
            rest["nodes"][f"{REPOSITORY}#9"]["state"],
        )
        self.assertEqual(graphql["issues"][f"{REPOSITORY}#9"]["state"], "CLOSED_OTHER")

    def test_rest_issue_start_does_not_fail_close_on_a_duplicate_blocker(self):
        """AC1: duplicate クローズした blocker で issue-start gate が止まらない。"""
        collector = GitHubCollector(
            "token",
            RestTransport(
                {10: ("open", None), 9: ("closed", "duplicate")}, blocked_by={10: (9,)}
            ),
        )
        snapshot = collector.collect_issue(REPOSITORY, 10)
        self.assertEqual(
            snapshot["nodes"][f"{REPOSITORY}#10"]["blocked_by"], [f"{REPOSITORY}#9"]
        )
        result = evaluate_snapshot(snapshot)
        self.assertEqual(
            (result["result"], result["primary_reason"]), ("ALLOW", "NO_VIOLATION")
        )

    def test_unrecognized_reason_is_collected_as_telemetry_only(self):
        collector = GitHubCollector(
            "token",
            GraphQLTransport(
                [
                    graphql_node(9, state="CLOSED", state_reason="SOME_FUTURE_REASON"),
                    graphql_node(8, state="CLOSED", state_reason="DUPLICATE"),
                ]
            ),
        )
        raw = collector.collect_repository(REPOSITORY)
        self.assertEqual(
            collector.unrecognized_state_reasons,
            {"SOME_FUTURE_REASON": {f"{REPOSITORY}#9"}},
        )
        # telemetry は閉じた snapshot schema へ混ざらない（判定材料ではない）。
        parse_repository_snapshot(raw)
        self.assertEqual(raw["errors"], [])
        self.assertTrue(raw["pages_complete"])


class SnapshotCliDetectionTests(FrozenClockMixin, unittest.TestCase):
    """AC5: 未知 reason は run を止めず、運用者へ届く（検知であって分類ではない）。"""

    def run_snapshot(self, nodes, env=None):
        collector = GitHubCollector("token", GraphQLTransport(nodes))
        stdout, stderr = StringIO(), StringIO()
        with patch.dict("os.environ", env or {}, clear=False):
            code = run_cli(
                ["snapshot", "--repository", REPOSITORY],
                stdout=stdout,
                stderr=stderr,
                collector_factory=lambda token: collector,
            )
        return code, stdout.getvalue(), stderr.getvalue()

    def test_unrecognized_reason_is_reported_without_failing_the_run(self):
        code, stdout, stderr = self.run_snapshot(
            [graphql_node(9, state="CLOSED", state_reason="SOME_FUTURE_REASON")]
        )
        self.assertEqual(code, 0)
        self.assertIn("UNRECOGNIZED_STATE_REASON", stderr)
        self.assertIn(f"SOME_FUTURE_REASON={REPOSITORY}#9", stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["issues"][f"{REPOSITORY}#9"]["state"], "CLOSED_OTHER")

    def test_actions_annotation_is_a_warning_not_a_failure(self):
        code, _, stderr = self.run_snapshot(
            [graphql_node(9, state="CLOSED", state_reason="SOME_FUTURE_REASON")],
            env={"GITHUB_ACTIONS": "true"},
        )
        self.assertEqual(code, 0)
        self.assertIn("::warning title=blocker-gate:", stderr)
        self.assertNotIn("::error", stderr)

    def test_recognized_reasons_stay_silent(self):
        code, _, stderr = self.run_snapshot(
            [
                graphql_node(9, state="CLOSED", state_reason="DUPLICATE"),
                graphql_node(8, state="CLOSED", state_reason=None),
                graphql_node(7, state="OPEN"),
                graphql_node(6, state="OPEN", state_reason="REOPENED"),
            ],
            env={"GITHUB_ACTIONS": "true"},
        )
        self.assertEqual(code, 0)
        self.assertNotIn("UNRECOGNIZED_STATE_REASON", stderr)
        self.assertNotIn("::warning", stderr)

    def test_contradictory_state_and_reason_reaches_the_operator(self):
        """F-466-02: `CLOSED`+`REOPENED` は判定を止めずに運用者へ届く。"""
        code, stdout, stderr = self.run_snapshot(
            [
                graphql_node(9, state="CLOSED", state_reason="REOPENED"),
                graphql_node(8, state="CLOSED", state_reason="DUPLICATE"),
            ],
            env={"GITHUB_ACTIONS": "true"},
        )
        self.assertEqual(code, 0)
        self.assertIn("UNRECOGNIZED_STATE_REASON", stderr)
        self.assertIn(f"CLOSED+REOPENED={REPOSITORY}#9", stderr)
        self.assertIn("::warning title=blocker-gate:", stderr)
        self.assertNotIn("::error", stderr)
        # 鳴らすのは矛盾した1件だけ。DUPLICATE は巻き込まない。
        self.assertNotIn("DUPLICATE", stderr)
        # 判定は解決済み側のまま（検知は verdict を動かさない）。
        payload = json.loads(stdout)
        self.assertEqual(payload["issues"][f"{REPOSITORY}#9"]["state"], "CLOSED_OTHER")


class TelemetryFormattingTests(unittest.TestCase):
    """F-466-03: telemetry の整形は判定材料の供給を止めない（例外を投げない）。"""

    def test_non_string_keys_are_dropped_before_sorting(self):
        """キー型が混在しても `sorted` の手前で落とすので `TypeError` にならない。"""
        self.assertEqual(format_unrecognized_state_reasons({1: set(), "A": set()}), "A")

    def test_malformed_telemetry_never_raises(self):
        cases = (
            (None, ""),
            ({}, ""),
            ([("A", set())], ""),
            ({1: {"x"}, None: {"y"}}, ""),
            ({"A": {1, "b"}}, "A=b"),
            ({"A": 7}, "A"),
            ({"B": {"r2"}, "A": {"r1"}}, "A=r1; B=r2"),
            ({"CLOSED+REOPENED": {f"{REPOSITORY}#9"}}, f"CLOSED+REOPENED={REPOSITORY}#9"),
        )
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(format_unrecognized_state_reasons(raw), expected)


class ProjectStatusSyncAgreementTests(FrozenClockMixin, unittest.TestCase):
    """AC2/AC4: gate とボードが duplicate クローズで同じ答えを出す。"""

    def plan(self, entries, status):
        snapshot = parse_repository_snapshot(repository_snapshot(entries))
        items = (ProjectItem("PVTI_1", f"{REPOSITORY}#10", status),)
        return snapshot, build_plan(snapshot, items, REPOSITORY)

    def test_duplicate_closed_blocker_clears_the_board_instead_of_aborting(self):
        entries = {
            10: issue_entry(10, blocked_by=(9,)),
            9: issue_entry(9, state="CLOSED_OTHER"),
        }
        snapshot, plan = self.plan(entries, BLOCKED)
        self.assertIsNone(plan.abort)
        self.assertEqual(
            [(change.to_status, change.reason) for change in plan.changes],
            [(READY, "BLOCKER_CLEARED")],
        )
        # gate 側も同じ材料で ALLOW。判定の一次情報源は1つしかない。
        projected, _ = project_issue_snapshot(snapshot, REPOSITORY, 10)
        self.assertEqual(evaluate_snapshot(projected)["result"], "ALLOW")

    def test_unknown_state_still_aborts_the_whole_run(self):
        """fail-close の非緩和: 本当に読めない state では従来どおり止まる。"""
        entries = {
            10: issue_entry(10, blocked_by=(9,)),
            9: issue_entry(9, state="UNKNOWN"),
        }
        _, plan = self.plan(entries, BLOCKED)
        self.assertIsNotNone(plan.abort)
        self.assertEqual(plan.abort.code, "ISSUE_STATE_UNKNOWN")
        self.assertEqual(plan.changes, ())
