"""Issue #345: 到達不能環境の snapshot fallback（［A］）と reason 分離（［B］）。

［A］孤立ブランチ `blocker-snapshot` の repository 全体 snapshot を、
GitHub API へ到達できない invocation だけが読む。［B］到達不能を
`API_PERMISSION` から分離し、それを fallback の機械的な引き金にする。
"""

from datetime import datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from blocker_gate.cli import run as run_cli
from blocker_gate.github import GitHubCollector
from blocker_gate.model import ERROR_REASONS, INCOMPLETE_REASONS, POLICY_VERSION
from blocker_gate.resolver import evaluate_snapshot
from blocker_gate.snapshot import (
    REPOSITORY_SNAPSHOT_SCHEMA,
    RepositorySnapshotError,
    parse_repository_snapshot,
    project_issue_snapshot,
)
from issue_start.gate import (
    SNAPSHOT_BRANCH,
    SNAPSHOT_MAX_AGE_SECONDS,
    SNAPSHOT_PATH,
    IssueStartError,
    IssueStartRequest,
    evaluate_issue_start,
    read_repository_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "example/repo"
# 生成時刻と wall clock の比較は常に `now=` 注入で制御する（CLAUDE.md
# 「時刻依存 test data の規律」/ Issue #344）。素の datetime.now は使わない。
GENERATED_AT = "2026-08-12T00:00:00Z"
GENERATED_AT_DT = datetime(2026, 8, 12, tzinfo=timezone.utc)
EVALUATED_AT = GENERATED_AT_DT + timedelta(seconds=1)


class FrozenResolverClockMixin:
    """`evaluate_snapshot` の `completed_at` は wall clock 読み取りであり、
    snapshot 側の `fetched_at`（＝固定した `generated_at`）と
    `fetched_at <= completed_at` で比較される。固定しないと、実行時刻が
    `GENERATED_AT` より前になる時間帯だけ RESULT_CONTRACT_INVALID で赤くなる
    （CLAUDE.md「時刻依存 test data の規律」/ Issue #344）。
    """

    def setUp(self):
        super().setUp()
        # collector 側の `generated_at` も同じ固定時刻にする。実時刻のままだと
        # 実行時刻が EVALUATED_AT を追い越した後で collector 由来 snapshot の
        # fetched_at > completed_at になり、テストが黙って別経路
        # （contract error）へ滑る。
        for target in ("blocker_gate.resolver.datetime", "blocker_gate.github.datetime"):
            patcher = patch(target, wraps=datetime)
            clock = patcher.start()
            clock.now.return_value = EVALUATED_AT
            self.addCleanup(patcher.stop)


def graphql_node(
    number,
    *,
    state="OPEN",
    state_reason=None,
    blocked_by=(),
    children=(),
    parent=None,
    blocked_truncated=False,
    children_truncated=False,
    repository=REPOSITORY,
):
    def connection(numbers, truncated):
        return {
            "pageInfo": {"hasNextPage": truncated},
            "nodes": [
                {"number": item, "repository": {"nameWithOwner": repository}}
                for item in numbers
            ],
        }

    return {
        "id": f"I_{number}",
        "number": number,
        "state": state,
        "stateReason": state_reason,
        "title": f"issue {number}",
        "url": f"https://github.com/{REPOSITORY}/issues/{number}",
        "parent": (
            None
            if parent is None
            else {"number": parent, "repository": {"nameWithOwner": repository}}
        ),
        "blockedBy": connection(blocked_by, blocked_truncated),
        "subIssues": connection(children, children_truncated),
    }


def graphql_page(
    nodes, *, has_next=False, cursor=None, repository=REPOSITORY, rate_limit=None
):
    data = {
        "repository": {
            "nameWithOwner": repository,
            "issues": {
                "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                "nodes": list(nodes),
            },
        }
    }
    # `rateLimit` は telemetry（F-345-04）。省略した page も引き続き受理される
    # ことが「欠落で生成を落とさない」契約の裏付けになる。
    if rate_limit is not None:
        data["rateLimit"] = dict(rate_limit)
    return {"data": data}


class PagedGraphQLTransport:
    """`post` だけを返す fake。GET は使わない（GraphQL 一括のため）。"""

    def __init__(self, pages):
        self.pages = list(pages)
        self.post_calls = []

    def get(self, url, headers):  # pragma: no cover - 呼ばれたら設計違反
        raise AssertionError("repository snapshot は GraphQL だけで取得する")

    def post(self, url, headers, body):
        self.post_calls.append((url, dict(headers), body))
        page = self.pages.pop(0)
        if isinstance(page, tuple):
            return page
        return 200, {}, json.dumps(page).encode("utf-8")


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


def repository_snapshot(
    entries, *, generated_at=GENERATED_AT, pages_complete=True, errors=(),
    repository=REPOSITORY,
):
    return {
        "schema": REPOSITORY_SNAPSHOT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "repository": repository,
        "generated_at": generated_at,
        "pages_complete": pages_complete,
        "errors": list(errors),
        "issues": {f"{repository}#{number}": value for number, value in entries.items()},
    }


def unreachable_issue_snapshot(*, extra_errors=(), number=10):
    """API 経路が「GitHub まで届かなかった」ときに collector が返す形。"""
    return {
        "schema": "blocker-gate-snapshot/v1",
        "policy_version": POLICY_VERSION,
        "mode": "issue-start",
        "repository": REPOSITORY,
        "subject": {"type": "issue", "number": number},
        "roots": [f"{REPOSITORY}#{number}"],
        "virtual_closed": [],
        "nodes": {},
        "pages_complete": False,
        "errors": ["API_UNREACHABLE", *extra_errors],
        "fetched_at": "2026-08-12T00:00:00Z",
        "graphql_closing_set": [],
        "delivered_message_closing_set": [],
        "binding": {},
    }


class StubCollector:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def collect_issue(self, repository, number):
        return self.snapshot

    def issue_metadata(self, repository, number):  # pragma: no cover - 到達不能環境では未使用
        raise AssertionError("snapshot 経路で API metadata を引いてはならない")


def request(number=10):
    return IssueStartRequest("issue-pipeline", REPOSITORY, number)


class ReasonSeparationTests(FrozenResolverClockMixin, unittest.TestCase):
    """［B］到達不能が権限拒否と別の閉じた reason になっている。"""

    def test_reason_is_registered_as_error_and_incomplete(self):
        self.assertIn("API_UNREACHABLE", ERROR_REASONS)
        # required read の未完なので pages_complete=true と両立してはならない。
        self.assertIn("API_UNREACHABLE", INCOMPLETE_REASONS)

    def test_unreachable_snapshot_is_error_and_never_permits(self):
        result = evaluate_snapshot(unreachable_issue_snapshot())
        self.assertEqual((result["result"], result["exit_code"]), ("ERROR", 20))
        self.assertFalse(result["permit_issued"])
        self.assertFalse(result["pages_complete"])
        self.assertIn("API_UNREACHABLE", result["reasons"])


class RepositoryCollectorTests(FrozenResolverClockMixin, unittest.TestCase):
    def collect(self, pages):
        transport = PagedGraphQLTransport(pages)
        raw = GitHubCollector("token", transport).collect_repository(REPOSITORY)
        return raw, transport

    def test_all_issues_are_enumerated_across_cursors(self):
        raw, transport = self.collect(
            [
                graphql_page(
                    [graphql_node(10, blocked_by=(9,), children=(11,))],
                    has_next=True,
                    cursor="cursor-1",
                ),
                graphql_page(
                    [
                        graphql_node(9, state="CLOSED", state_reason="COMPLETED"),
                        graphql_node(11, state="CLOSED", state_reason="NOT_PLANNED", parent=10),
                    ]
                ),
            ]
        )
        self.assertTrue(raw["pages_complete"])
        self.assertEqual(raw["errors"], [])
        self.assertEqual(len(transport.post_calls), 2)
        self.assertEqual(sorted(raw["issues"]), [f"{REPOSITORY}#{n}" for n in (10, 11, 9)])
        self.assertEqual(raw["issues"][f"{REPOSITORY}#9"]["state"], "CLOSED_COMPLETED")
        self.assertEqual(raw["issues"][f"{REPOSITORY}#11"]["state"], "CLOSED_NOT_PLANNED")
        # closed Issue も列挙するからこそ parent/child の逆参照が埋まる。
        self.assertEqual(raw["issues"][f"{REPOSITORY}#11"]["parent"], f"{REPOSITORY}#10")
        parse_repository_snapshot(raw)

    def test_closed_without_known_reason_is_unknown_state(self):
        for state_reason in (None, "DUPLICATE", "REOPENED"):
            with self.subTest(state_reason=state_reason):
                raw, _ = self.collect(
                    [graphql_page([graphql_node(10, state="CLOSED", state_reason=state_reason)])]
                )
                self.assertEqual(raw["issues"][f"{REPOSITORY}#10"]["state"], "UNKNOWN")

    def test_truncated_relation_connection_fails_close(self):
        """Issue #345 落とし穴2: `first:` を超えた relation は補完せず fail-close する。"""
        for field in ("blocked_truncated", "children_truncated"):
            with self.subTest(field=field):
                raw, _ = self.collect(
                    [graphql_page([graphql_node(10, **{field: True})])]
                )
                self.assertFalse(raw["pages_complete"])
                self.assertIn("PAGINATION_INCOMPLETE", raw["errors"])
                projected, _ = project_issue_snapshot(
                    parse_repository_snapshot(raw), REPOSITORY, 10
                )
                result = evaluate_snapshot(projected)
                self.assertEqual(result["result"], "ERROR")
                self.assertFalse(result["permit_issued"])

    def test_cross_repository_relation_is_recorded_not_silently_dropped(self):
        node = graphql_node(10)
        node["blockedBy"]["nodes"] = [
            {"number": 5, "repository": {"nameWithOwner": "other/repo"}}
        ]
        raw, _ = self.collect([graphql_page([node])])
        self.assertFalse(raw["pages_complete"])
        self.assertIn("CROSS_REPOSITORY_UNSUPPORTED", raw["errors"])

    def test_transport_and_identity_failures_are_recorded(self):
        cases = (
            ([(403, {}, b"{}")], "API_UNREACHABLE"),
            ([(403, {"X-GitHub-Request-Id": "E1"}, b"{}")], "API_PERMISSION"),
            ([graphql_page([], repository="other/repo")], "IDENTITY_MISMATCH"),
            ([graphql_page([graphql_node(10)], has_next=True, cursor=None)], "PAGINATION_INCOMPLETE"),
        )
        for pages, reason in cases:
            with self.subTest(reason=reason):
                raw, _ = self.collect(pages)
                self.assertFalse(raw["pages_complete"])
                self.assertIn(reason, raw["errors"])

    def test_duplicate_issue_number_is_identity_mismatch(self):
        raw, _ = self.collect(
            [graphql_page([graphql_node(10), graphql_node(10)])]
        )
        self.assertIn("IDENTITY_MISMATCH", raw["errors"])
        self.assertFalse(raw["pages_complete"])


class ParseAndProjectionTests(FrozenResolverClockMixin, unittest.TestCase):
    def test_projection_keeps_only_the_reachable_closure(self):
        snapshot = parse_repository_snapshot(
            repository_snapshot(
                {
                    10: issue_entry(10, blocked_by=(9,), children=(11,)),
                    9: issue_entry(9, state="CLOSED_COMPLETED"),
                    11: issue_entry(11, state="CLOSED_COMPLETED", parent=10),
                    # 対象と無関係な Issue は射影に含めない。
                    99: issue_entry(99),
                }
            )
        )
        projected, metadata = project_issue_snapshot(snapshot, REPOSITORY, 10)
        self.assertEqual(
            sorted(projected["nodes"]), [f"{REPOSITORY}#{n}" for n in (10, 11, 9)]
        )
        self.assertNotIn(f"{REPOSITORY}#99", projected["nodes"])
        self.assertEqual(projected["fetched_at"], GENERATED_AT)
        self.assertEqual(projected["roots"], [f"{REPOSITORY}#10"])
        self.assertEqual(metadata[f"{REPOSITORY}#9"]["title"], "issue 9")
        result = evaluate_snapshot(projected)
        self.assertEqual((result["result"], result["primary_reason"]), ("ALLOW", "NO_VIOLATION"))

    def test_missing_target_is_unreadable_not_blocker_free(self):
        snapshot = parse_repository_snapshot(repository_snapshot({9: issue_entry(9)}))
        projected, _ = project_issue_snapshot(snapshot, REPOSITORY, 10)
        result = evaluate_snapshot(projected)
        self.assertEqual(result["result"], "ERROR")
        self.assertIn("RELATION_TARGET_UNREADABLE", result["reasons"])
        self.assertFalse(result["permit_issued"])

    def test_global_incompleteness_fails_close_unrelated_issues(self):
        """Issue #345 落とし穴1: repository 単位の pages_complete/errors は global。

        ある Issue の収集失敗が、blocker を持たない無関係な Issue まで
        fail-close させる。fail-close 側の過剰なので許容するが、
        「実装後に偶然発見される状態」にしないためここで固定する。
        """
        for pages_complete, errors in ((False, ()), (True, ("API_PARTIAL_RESPONSE",))):
            with self.subTest(pages_complete=pages_complete, errors=errors):
                snapshot = parse_repository_snapshot(
                    repository_snapshot(
                        {10: issue_entry(10)},
                        pages_complete=pages_complete,
                        errors=errors,
                    )
                )
                projected, _ = project_issue_snapshot(snapshot, REPOSITORY, 10)
                result = evaluate_snapshot(projected)
                self.assertEqual(result["result"], "ERROR")
                self.assertFalse(result["permit_issued"])

    def test_repository_mismatch_is_rejected(self):
        snapshot = parse_repository_snapshot(repository_snapshot({10: issue_entry(10)}))
        with self.assertRaises(RepositorySnapshotError) as caught:
            project_issue_snapshot(snapshot, "other/repo", 10)
        self.assertEqual(caught.exception.reason, "SNAPSHOT_REPOSITORY_MISMATCH")

    def test_malformed_snapshots_are_rejected(self):
        valid = repository_snapshot({10: issue_entry(10)})
        mutations = {
            "schema": {**valid, "schema": "something/else"},
            "policy_version": {**valid, "policy_version": "9.9"},
            "unknown key": {**valid, "extra": 1},
            "missing key": {k: v for k, v in valid.items() if k != "errors"},
            "repository": {**valid, "repository": "not-a-repo"},
            "generated_at": {**valid, "generated_at": "2026-08-12 00:00:00"},
            "pages_complete": {**valid, "pages_complete": "true"},
            "unknown error reason": {**valid, "errors": ["NOT_A_REASON"]},
            "issue ref": {**valid, "issues": {"other/repo#1": issue_entry(1)}},
            "issue keys": {
                **valid,
                "issues": {f"{REPOSITORY}#10": {"node_id": "I_10", "state": "OPEN"}},
            },
            "issue state": {
                **valid,
                "issues": {f"{REPOSITORY}#10": {**issue_entry(10), "state": "MAYBE"}},
            },
            "report fields": {
                **valid,
                "issues": {f"{REPOSITORY}#10": {**issue_entry(10), "title": ""}},
            },
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label), self.assertRaises(RepositorySnapshotError):
                parse_repository_snapshot(mutation)


class GateFallbackTests(FrozenResolverClockMixin, unittest.TestCase):
    def evaluate(self, *, api_snapshot, reader=None, now=GENERATED_AT_DT, number=10):
        return evaluate_issue_start(
            request(number),
            collector_factory=lambda token: StubCollector(api_snapshot),
            snapshot_reader=reader,
            now=now,
        )

    def reader(self, snapshot):
        calls = []

        def read(*, repository, cwd=None, runner=None):
            calls.append((repository, cwd, runner))
            return parse_repository_snapshot(snapshot)

        read.calls = calls
        return read

    def test_reachable_api_path_never_reads_the_snapshot(self):
        """ローカル環境の fresh read を退行させない（fallback は起動しない）。"""
        def forbidden(*, repository=None, cwd=None, runner=None):
            raise AssertionError("到達できている invocation は snapshot を読まない")

        allowed = {
            **unreachable_issue_snapshot(),
            "nodes": {
                f"{REPOSITORY}#10": {
                    "node_id": "I_10",
                    "state": "OPEN",
                    "blocked_by": [],
                    "parent": None,
                    "children": [],
                }
            },
            "pages_complete": True,
            "errors": [],
        }
        evidence = self.evaluate(api_snapshot=allowed, reader=forbidden)
        self.assertEqual(evidence["result"], "ALLOW")
        self.assertEqual(evidence["source"], "api")
        self.assertIsNone(evidence["snapshot_generated_at"])

    def test_permission_error_does_not_trigger_the_fallback(self):
        """真の権限エラーは従来どおり ERROR のまま。stale な材料へ逃げない。"""
        def forbidden(*, repository=None, cwd=None, runner=None):
            raise AssertionError("API_PERMISSION は fallback の引き金ではない")

        denied = {**unreachable_issue_snapshot(), "errors": ["API_PERMISSION"]}
        evidence = self.evaluate(api_snapshot=denied, reader=forbidden)
        self.assertEqual(evidence["result"], "ERROR")
        self.assertEqual(evidence["reason"], "API_PERMISSION")
        self.assertEqual(evidence["source"], "api")

    def test_unreachable_falls_back_and_reports_blockers_without_api(self):
        reader = self.reader(
            repository_snapshot(
                {
                    10: issue_entry(10, blocked_by=(9,)),
                    9: issue_entry(9),
                }
            )
        )
        evidence = self.evaluate(
            api_snapshot=unreachable_issue_snapshot(), reader=reader
        )
        self.assertEqual((evidence["result"], evidence["exit_code"]), ("BLOCK", 10))
        self.assertEqual(evidence["reason"], "OPEN_BLOCKER")
        self.assertEqual(evidence["source"], "snapshot")
        self.assertEqual(evidence["snapshot_generated_at"], GENERATED_AT)
        self.assertEqual(len(reader.calls), 1)
        blocker = evidence["blockers"][0]
        # title/URL は snapshot 同梱値から組み立てる（API は叩けない環境なので）。
        self.assertEqual(blocker["number"], 9)
        self.assertEqual(blocker["title"], "issue 9")
        self.assertIn("/issues/9", blocker["url"])

    def test_unreachable_falls_back_and_can_allow(self):
        reader = self.reader(
            repository_snapshot(
                {
                    10: issue_entry(10, blocked_by=(9,)),
                    9: issue_entry(9, state="CLOSED_COMPLETED"),
                }
            )
        )
        evidence = self.evaluate(
            api_snapshot=unreachable_issue_snapshot(), reader=reader
        )
        self.assertEqual((evidence["result"], evidence["exit_code"]), ("ALLOW", 0))
        self.assertEqual(evidence["source"], "snapshot")
        self.assertEqual(evidence["fetched_at"], GENERATED_AT)

    def test_trigger_uses_reason_membership_not_primary_reason(self):
        """canonical sort で primary が別 reason になっても fallback は起動する。

        F-345-01 の是正で「読めた node が 0 件」という条件が加わったが、
        `primary_reason` ではなく `reasons` の membership で見るという判断は
        そのまま有効である（実測形の primary は別 reason になる）。
        """
        api_snapshot = unreachable_issue_snapshot(extra_errors=("API_PARTIAL_RESPONSE",))
        self.assertEqual(
            evaluate_snapshot(api_snapshot)["primary_reason"], "API_PARTIAL_RESPONSE"
        )
        reader = self.reader(repository_snapshot({10: issue_entry(10)}))
        evidence = self.evaluate(api_snapshot=api_snapshot, reader=reader)
        self.assertEqual(evidence["source"], "snapshot")
        self.assertEqual(evidence["result"], "ALLOW")

    def test_real_unreachable_shape_still_falls_back(self):
        """F-345-01 recheck (a): 到達不能環境の実測形で fallback が生きている。

        実測形は `reasons=["API_UNREACHABLE", "RELATION_TARGET_UNREADABLE"]` /
        `nodes={}`。F-345-01 の是正（node 0 件条件の追加）がこの真の到達不能
        ケースまで殺していないことを固定する。
        """
        api_snapshot = unreachable_issue_snapshot(
            extra_errors=("RELATION_TARGET_UNREADABLE",)
        )
        self.assertEqual(api_snapshot["nodes"], {})
        self.assertEqual(
            sorted(evaluate_snapshot(api_snapshot)["reasons"]),
            ["API_UNREACHABLE", "RELATION_TARGET_UNREADABLE"],
        )
        reader = self.reader(repository_snapshot({10: issue_entry(10)}))
        evidence = self.evaluate(api_snapshot=api_snapshot, reader=reader)
        self.assertEqual(evidence["source"], "snapshot")
        self.assertEqual(evidence["result"], "ALLOW")
        # 読取側へは invocation の repository が束縛されて渡る（F-345-02）。
        self.assertEqual([call[0] for call in reader.calls], [REPOSITORY])

    def test_partially_read_invocation_does_not_fall_back(self):
        """F-345-01 recheck (b): 1 node でも読めていれば fallback しない。

        到達できている環境で 1 node が一過性 timeout / URLError を起こすと
        `API_UNREACHABLE` が reasons に入る。reasons membership だけを引き金に
        すると、この invocation が最大10分 stale な材料で ALLOW になりうる。
        GitHub provenance を観測している以上 fallback しないことを固定する。
        """
        def forbidden(*, repository=None, cwd=None, runner=None):
            raise AssertionError("node を読めた invocation は snapshot を読まない")

        partial = {
            **unreachable_issue_snapshot(),
            "nodes": {
                f"{REPOSITORY}#10": {
                    "node_id": "I_10",
                    "state": "OPEN",
                    "blocked_by": [],
                    "parent": None,
                    "children": [],
                }
            },
        }
        self.assertIn("API_UNREACHABLE", partial["errors"])
        evidence = self.evaluate(api_snapshot=partial, reader=forbidden)
        self.assertEqual((evidence["result"], evidence["exit_code"]), ("ERROR", 20))
        self.assertEqual(evidence["reason"], "API_UNREACHABLE")
        self.assertEqual(evidence["source"], "api")
        self.assertIsNone(evidence["snapshot_generated_at"])

    def test_staleness_bound_is_enforced_in_both_directions(self):
        reader = self.reader(repository_snapshot({10: issue_entry(10)}))
        edge = GENERATED_AT_DT + timedelta(seconds=SNAPSHOT_MAX_AGE_SECONDS)
        self.assertEqual(
            self.evaluate(
                api_snapshot=unreachable_issue_snapshot(), reader=reader, now=edge
            )["result"],
            "ALLOW",
        )
        cases = (
            ("ISSUE_START_SNAPSHOT_STALE", edge + timedelta(seconds=1)),
            ("ISSUE_START_SNAPSHOT_FUTURE", GENERATED_AT_DT - timedelta(seconds=1)),
        )
        for reason, now in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(
                IssueStartError, reason
            ):
                self.evaluate(
                    api_snapshot=unreachable_issue_snapshot(), reader=reader, now=now
                )

    def test_snapshot_repository_mismatch_fails_close(self):
        reader = self.reader(
            repository_snapshot({10: issue_entry(10)}, repository="other/repo")
        )
        with self.assertRaisesRegex(
            IssueStartError, "ISSUE_START_SNAPSHOT_BINDING_MISMATCH"
        ):
            self.evaluate(api_snapshot=unreachable_issue_snapshot(), reader=reader)

    def test_unavailable_snapshot_never_becomes_allow(self):
        def raising(reason):
            def read(*, repository=None, cwd=None, runner=None):
                raise IssueStartError(reason)

            return read

        for reason in (
            "ISSUE_START_SNAPSHOT_FETCH_FAILED",
            "ISSUE_START_SNAPSHOT_UNREADABLE",
            "ISSUE_START_SNAPSHOT_INVALID_JSON",
            "ISSUE_START_SNAPSHOT_INVALID",
        ):
            with self.subTest(reason=reason), self.assertRaisesRegex(
                IssueStartError, reason
            ):
                self.evaluate(
                    api_snapshot=unreachable_issue_snapshot(), reader=raising(reason)
                )


class SnapshotReaderTests(unittest.TestCase):
    """`git fetch` → `git show` の固定 argv 契約（shell を経由しない）。"""

    def runner(self, *, show, fetch_returncode=0, origin=f"https://github.com/{REPOSITORY}"):
        calls = []

        class Completed:
            def __init__(self, stdout="", returncode=0):
                self.stdout = stdout
                self.returncode = returncode

        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            if argv[:2] == ["git", "rev-parse"]:
                return Completed(str(ROOT) + "\n")
            if argv[1] == "remote":
                return Completed(origin + "\n")
            if argv[1] == "fetch":
                return Completed("", fetch_returncode)
            return Completed(show)

        run.calls = calls
        run.Completed = Completed
        return run

    def test_reads_the_orphan_branch_through_origin(self):
        payload = json.dumps(repository_snapshot({10: issue_entry(10)}))
        runner = self.runner(show=payload)
        snapshot = read_repository_snapshot(
            repository=REPOSITORY, cwd=ROOT, runner=runner
        )
        self.assertEqual(snapshot["repository"], REPOSITORY)
        argvs = [argv for argv, _ in runner.calls]
        self.assertIn(
            [
                "git",
                "fetch",
                "--no-tags",
                "--quiet",
                "origin",
                f"+refs/heads/{SNAPSHOT_BRANCH}:refs/remotes/origin/{SNAPSHOT_BRANCH}",
            ],
            argvs,
        )
        self.assertIn(
            ["git", "show", f"refs/remotes/origin/{SNAPSHOT_BRANCH}:{SNAPSHOT_PATH}"],
            argvs,
        )
        for _, kwargs in runner.calls:
            self.assertIs(kwargs["shell"], False)
            self.assertLessEqual(kwargs["timeout"], 30)

    def test_missing_branch_and_broken_payload_fail_close(self):
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_SNAPSHOT_FETCH_FAILED"):
            read_repository_snapshot(
                repository=REPOSITORY,
                cwd=ROOT,
                runner=self.runner(show="", fetch_returncode=1),
            )
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_SNAPSHOT_INVALID_JSON"):
            read_repository_snapshot(
                repository=REPOSITORY, cwd=ROOT, runner=self.runner(show="not-json")
            )
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_SNAPSHOT_INVALID"):
            read_repository_snapshot(
                repository=REPOSITORY, cwd=ROOT, runner=self.runner(show='{"schema":"x"}')
            )

    def test_origin_pointing_at_another_repository_fails_close(self):
        """F-345-02: identity 束縛を snapshot の自己申告だけに閉じない。

        origin を攻撃者の管理下へ向けた上で、対象 repository を名乗る snapshot を
        配れば ALLOW が作れてしまう（policy §3.3.1 の「偽造には対象 repository への
        push 権限が要る」という論拠がこの経路で崩れる）。origin が要求 repository と
        一致しない限り、**fetch すら行わない**ことを固定する。
        """
        # snapshot 自体は要求 repository を自己申告している（内容検査は通る形）。
        payload = json.dumps(repository_snapshot({10: issue_entry(10)}))
        runner = self.runner(show=payload, origin="https://github.com/attacker/repo")
        with self.assertRaisesRegex(
            IssueStartError, "ISSUE_START_SNAPSHOT_ORIGIN_MISMATCH"
        ):
            read_repository_snapshot(
                repository=REPOSITORY, cwd=ROOT, runner=runner
            )
        verbs = [argv[1] for argv, _ in runner.calls]
        self.assertNotIn("fetch", verbs)
        self.assertNotIn("show", verbs)

    def test_origin_is_normalized_like_the_codex_path(self):
        """ssh 形式・`.git` 付きでも同じ canonical repository に落ちる。"""
        payload = json.dumps(repository_snapshot({10: issue_entry(10)}))
        for origin in (
            f"https://github.com/{REPOSITORY}.git",
            f"git@github.com:{REPOSITORY}.git",
            f"ssh://git@github.com/{REPOSITORY}",
        ):
            with self.subTest(origin=origin):
                snapshot = read_repository_snapshot(
                    repository=REPOSITORY,
                    cwd=ROOT,
                    runner=self.runner(show=payload, origin=origin),
                )
                self.assertEqual(snapshot["repository"], REPOSITORY)

    def test_unparsable_origin_fails_close(self):
        payload = json.dumps(repository_snapshot({10: issue_entry(10)}))
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_ORIGIN_INVALID"):
            read_repository_snapshot(
                repository=REPOSITORY,
                cwd=ROOT,
                runner=self.runner(show=payload, origin="/tmp/local/clone"),
            )


class SnapshotCliTests(unittest.TestCase):
    def test_snapshot_subcommand_emits_one_json_and_exits_zero(self):
        transport = PagedGraphQLTransport([graphql_page([graphql_node(10)])])
        stdout, stderr = StringIO(), StringIO()
        code = run_cli(
            ["snapshot", "--repository", REPOSITORY],
            stdout=stdout,
            stderr=stderr,
            collector_factory=lambda token: GitHubCollector(token, transport),
        )
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue().count("\n"), 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["schema"], REPOSITORY_SNAPSHOT_SCHEMA)
        parse_repository_snapshot(payload)
        self.assertIn("pages_complete=True", stderr.getvalue())

    def test_incomplete_snapshot_is_still_published_but_exits_degraded(self):
        """F-345-03: 部分 publish は維持したまま、恒久故障を exit code で外へ出す。

        生成側は verdict を出さない（判定は読取側）。しかし exit 0 のままだと
        生成が恒久的に壊れても workflow が緑で終わり、機能が死んでいることに
        誰も気づけない。JSON は従来どおり stdout へ出しつつ exit 20 を返す。
        """
        transport = PagedGraphQLTransport([(403, {}, b"{}")])
        stdout, stderr = StringIO(), StringIO()
        code = run_cli(
            ["snapshot", "--repository", REPOSITORY],
            stdout=stdout,
            stderr=stderr,
            collector_factory=lambda token: GitHubCollector(token, transport),
        )
        self.assertEqual(code, 20)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["pages_complete"])
        self.assertEqual(payload["errors"], ["API_UNREACHABLE"])
        self.assertIn("DEGRADED", stderr.getvalue())

    def test_errors_alone_are_enough_to_report_degraded(self):
        """`pages_complete` が真でも `errors` が非空なら劣化として扱う。"""
        page = graphql_page(
            [graphql_node(10, parent=11, repository="other/repo")]
        )
        transport = PagedGraphQLTransport([page])
        stdout, stderr = StringIO(), StringIO()
        code = run_cli(
            ["snapshot", "--repository", REPOSITORY],
            stdout=stdout,
            stderr=stderr,
            collector_factory=lambda token: GitHubCollector(token, transport),
        )
        self.assertEqual(code, 20)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["errors"], ["CROSS_REPOSITORY_UNSUPPORTED"])

    def test_rate_limit_is_measured_and_summarized(self):
        """F-345-04: cron 5分が枠内に収まることを事後検証できるようにする。"""
        pages = [
            graphql_page([graphql_node(10)], has_next=True, cursor="c1", rate_limit={
                "cost": 2, "remaining": 4998, "resetAt": "2026-08-12T01:00:00Z",
            }),
            graphql_page([graphql_node(11)], rate_limit={
                "cost": 3, "remaining": 4995, "resetAt": "2026-08-12T01:00:00Z",
            }),
        ]
        transport = PagedGraphQLTransport(pages)
        stdout, stderr = StringIO(), StringIO()
        collector = GitHubCollector(None, transport)
        code = run_cli(
            ["snapshot", "--repository", REPOSITORY],
            stdout=stdout,
            stderr=stderr,
            collector_factory=lambda token: collector,
        )
        self.assertEqual(code, 0)
        # query は rateLimit を top-level（repository の兄弟）で引く。
        self.assertIn("rateLimit{cost remaining resetAt}", GitHubCollector._REPOSITORY_QUERY)
        # cost は page をまたいで合計、remaining/resetAt は最後の観測値。
        self.assertEqual(
            collector.last_rate_limit,
            {"cost": 5, "pages": 2, "remaining": 4995, "reset_at": "2026-08-12T01:00:00Z"},
        )
        self.assertIn("rate_limit=cost=5,remaining=4995", stderr.getvalue())
        # telemetry は閉じた snapshot schema へ混ざらない。
        parse_repository_snapshot(json.loads(stdout.getvalue()))

    def test_missing_rate_limit_never_fails_generation(self):
        """telemetry の欠落で snapshot 生成を落とさない（判定材料ではない）。"""
        transport = PagedGraphQLTransport([graphql_page([graphql_node(10)])])
        stdout, stderr = StringIO(), StringIO()
        collector = GitHubCollector(None, transport)
        code = run_cli(
            ["snapshot", "--repository", REPOSITORY],
            stdout=stdout,
            stderr=stderr,
            collector_factory=lambda token: collector,
        )
        self.assertEqual(code, 0)
        self.assertIsNone(collector.last_rate_limit)
        self.assertIn("rate_limit=-", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
