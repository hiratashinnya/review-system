"""Issue #297 managed Issue-start adapter/hook tests。"""

import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from issue_start.gate import (
    BINDING_MARKER,
    IssueStartError,
    IssueStartRequest,
    _validate_tool_input_shape,
    evaluate_issue_start,
    parse_dispatch_payload,
)
from issue_start.hook import run as run_hook


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parents[1] / "fixtures" / "blocker_gate"
OID = "a" * 40


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class Collector:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.waiver_calls = 0

    def collect_issue(self, repository, number):
        return self.snapshot

    def collect_waiver_materials(self, repository, refs):
        self.waiver_calls += 1
        raise AssertionError("#299前に waiver provider を呼んではならない")

    def issue_metadata(self, repository, number):
        return {
            "number": number,
            "title": f"blocker {number}",
            "html_url": f"https://github.com/{repository}/issues/{number}",
        }


def request(repository="example/repo", issue=10):
    return IssueStartRequest("issue-pipeline", repository, issue)


def claude_binding():
    return {
        "entrypoint": "issue-pipeline",
        "repository": "example/repo",
        "issue": 10,
        "branch_name": "issue-297",
        "base_ref": "main",
        "base_oid": OID,
        "base_pr": None,
    }


class FakeCompleted:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def git_runner(*, origin="https://github.com/example/repo.git", inside="true", top=ROOT):
    def run(argv, **kwargs):
        if argv == ["git", "rev-parse", "--is-inside-work-tree"]:
            return FakeCompleted(inside + "\n")
        if argv == ["git", "rev-parse", "--show-toplevel"]:
            return FakeCompleted(str(top) + "\n")
        if argv == ["git", "remote", "get-url", "origin"]:
            return FakeCompleted(origin + "\n")
        raise AssertionError(f"unexpected git argv: {argv}")
    return run


class DispatchPayloadMixin:
    """Codex/Claude の正規 dispatch payload を組み立てる共通ヘルパ（テストは持たない）。"""

    def codex_payload(self, *, task_name="issue_10", tool="collaborationspawn_agent", cwd=ROOT):
        return {
            "cwd": str(cwd),
            "tool_name": tool,
            "tool_input": {
                "agent_type": "issue-implementer",
                "fork_turns": "all",
                "task_name": task_name,
                # Codex 0.146.0 の実測では message は暗号化値。binding に使わない。
                "message": "ENC[AQICAH-encrypted-prompt]",
            },
        }

    def claude_payload(self, binding=None, *, tool="Task", isolation="worktree"):
        raw = claude_binding() if binding is None else binding
        tool_input = {
            "subagent_type": "issue-implementer",
            "prompt": BINDING_MARKER + json.dumps(raw, separators=(",", ":")),
            "description": "hook deny probe",
        }
        # Issue #350: 正規の dispatch は必ず `isolation: "worktree"` を伴う。
        if isolation is not None:
            tool_input["isolation"] = isolation
        return {"tool_name": tool, "tool_input": tool_input}


class DispatchPayloadTests(DispatchPayloadMixin, unittest.TestCase):
    def test_codex_encrypted_message_uses_task_name_and_worktree_origin(self):
        for tool_name in ("spawn_agent", "collaborationspawn_agent"):
            with self.subTest(tool_name=tool_name):
                actual = parse_dispatch_payload(
                    self.codex_payload(tool=tool_name), cwd=ROOT, runner=git_runner()
                )
                self.assertEqual(actual, request())

    def test_codex_accepts_strict_github_https_and_ssh_origins(self):
        for origin in (
            "https://github.com/example/repo.git",
            "git@github.com:example/repo.git",
            "ssh://git@github.com/example/repo.git",
        ):
            with self.subTest(origin=origin):
                actual = parse_dispatch_payload(
                    self.codex_payload(), cwd=ROOT, runner=git_runner(origin=origin)
                )
                self.assertEqual(actual.repository, "example/repo")

    def test_codex_bad_or_missing_task_name_is_fail_close(self):
        for task_name in (None, "", "issue_0", "issue_01", "issue-10", "issue_10_more", "xissue_10"):
            payload = self.codex_payload()
            if task_name is None:
                del payload["tool_input"]["task_name"]
            else:
                payload["tool_input"]["task_name"] = task_name
            with self.subTest(task_name=task_name), self.assertRaisesRegex(
                IssueStartError,
                "ISSUE_START_(TOOL_INPUT_SHAPE_INVALID|TASK_NAME_INVALID)",
            ):
                parse_dispatch_payload(payload, cwd=ROOT, runner=git_runner())

    def test_codex_bad_cwd_worktree_and_origin_are_fail_close(self):
        cases = [
            (self.codex_payload(cwd=ROOT.parent), git_runner(), "ISSUE_START_CWD_MISMATCH"),
            (self.codex_payload(), git_runner(inside="false"), "ISSUE_START_NOT_WORKTREE"),
            (self.codex_payload(), git_runner(top=ROOT.parent), "ISSUE_START_WORKTREE_ROOT_MISMATCH"),
            (self.codex_payload(), git_runner(origin="https://evil.example/example/repo.git"), "ISSUE_START_ORIGIN_INVALID"),
            (self.codex_payload(), git_runner(origin="http://github.com/example/repo.git"), "ISSUE_START_ORIGIN_INVALID"),
            (self.codex_payload(), git_runner(origin="https://user@github.com/example/repo.git"), "ISSUE_START_ORIGIN_INVALID"),
        ]
        for payload, runner, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(IssueStartError, reason):
                parse_dispatch_payload(payload, cwd=ROOT, runner=runner)

    def test_claude_task_and_runtime_agent_alias_use_marker_contract(self):
        for tool_name in ("Task", "Agent"):
            with self.subTest(tool_name=tool_name):
                self.assertEqual(
                    parse_dispatch_payload(self.claude_payload(tool=tool_name)), request()
                )
        bad = claude_binding()
        bad.pop("base_oid")
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_UNKNOWN_FIELD"):
            parse_dispatch_payload(self.claude_payload(bad))
        wrong_entrypoint = claude_binding()
        wrong_entrypoint["entrypoint"] = "other-pipeline"
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_ENTRYPOINT_UNKNOWN"):
            parse_dispatch_payload(self.claude_payload(wrong_entrypoint))

    def test_codex_agent_matcher_alias_is_not_a_codex_payload_alias(self):
        with self.assertRaisesRegex(
            IssueStartError, "ISSUE_START_TOOL_INPUT_SHAPE_INVALID"
        ):
            parse_dispatch_payload(
                self.codex_payload(tool="Agent"), cwd=ROOT, runner=git_runner()
            )

    def test_claude_shape_rejects_codex_field_mixing(self):
        for field, value in (
            ("agent_type", "issue-implementer"),
            ("message", "ENC[AQICAH-encrypted-prompt]"),
            ("task_name", "issue_10"),
        ):
            payload = self.claude_payload(tool="Agent")
            payload["tool_input"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_(TARGET_UNKNOWN|TOOL_INPUT_SHAPE_INVALID)"
            ):
                parse_dispatch_payload(payload)

    def test_unknown_or_similar_tool_names_are_not_payload_aliases(self):
        for tool_name in (
            "collaboration.spawn_agent",
            "evil.spawn_agent",
            "evilspawn_agent",
            "collaborationspawn_agent_extra",
            "collaborationspawn_agents",
        ):
            with self.subTest(tool_name=tool_name), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_ENTRYPOINT_UNKNOWN"
            ):
                parse_dispatch_payload(
                    self.codex_payload(tool=tool_name), cwd=ROOT, runner=git_runner()
                )
        for tool_name in ("agent", "Agents", "TaskAgent", "Agent_extra"):
            with self.subTest(tool_name=tool_name), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_ENTRYPOINT_UNKNOWN"
            ):
                parse_dispatch_payload(self.claude_payload(tool=tool_name))

    def test_non_issue_agent_is_explicitly_unmanaged(self):
        payload = self.codex_payload()
        payload["tool_input"]["agent_type"] = "explorer"
        self.assertIsNone(parse_dispatch_payload(payload, cwd=ROOT, runner=git_runner()))

    def test_missing_or_ambiguous_target_is_fail_close(self):
        missing = self.codex_payload()
        del missing["tool_input"]["agent_type"]
        ambiguous = self.codex_payload()
        ambiguous["tool_input"]["subagent_type"] = "issue-implementer"
        for payload in (missing, ambiguous):
            with self.assertRaisesRegex(IssueStartError, "ISSUE_START_TARGET_UNKNOWN"):
                parse_dispatch_payload(payload, cwd=ROOT, runner=git_runner())


class IsolationContractTests(DispatchPayloadMixin, unittest.TestCase):
    """Issue #350: Claude dispatch は `isolation: "worktree"` を欠くと deny される。

    分離は role 側では実現できない（gitgate に worktree verb が無く、agent-command-gate の
    層2 が `cd` を deny する）ので、dispatch 側の指定だけが「isolated worktree」契約を
    成立させる唯一の手段。欠落は fail-close で拒否する。
    """

    def test_claude_dispatch_with_worktree_isolation_is_bound(self):
        payload = self.claude_payload()
        self.assertEqual(payload["tool_input"]["isolation"], "worktree")
        for tool_name in ("Task", "Agent"):
            with self.subTest(tool_name=tool_name):
                self.assertEqual(
                    parse_dispatch_payload(self.claude_payload(tool=tool_name)), request()
                )

    def test_claude_dispatch_without_worktree_isolation_is_denied(self):
        # None＝field 自体が無い（isolation を渡し忘れた dispatch）。
        for isolation in (None, "remote", "", "Worktree", "worktree ", 1, True, ["worktree"]):
            with self.subTest(isolation=isolation), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_ISOLATION_NOT_WORKTREE"
            ):
                parse_dispatch_payload(self.claude_payload(isolation=isolation))

    def test_isolation_check_does_not_mask_more_fundamental_shape_errors(self):
        # required field 欠落は isolation より先に報告する（直す順序を誤らせない）。
        payload = self.claude_payload(isolation=None)
        del payload["tool_input"]["prompt"]
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_TOOL_INPUT_SHAPE_INVALID"):
            parse_dispatch_payload(payload)

    def test_codex_transport_carries_no_isolation_requirement(self):
        # Codex の spawn_agent に isolation パラメータは無い。claude 側の要求を持ち込まない。
        self.assertEqual(
            parse_dispatch_payload(self.codex_payload(), cwd=ROOT, runner=git_runner()),
            request(),
        )

    def test_unmanaged_agents_are_never_required_to_declare_isolation(self):
        # 非 issue-implementer の dispatch を巻き込むと全委譲が壊れる。素通し（None）を固定する。
        for agent in ("pr-reviewer", "issue-fixer", "general-purpose", "dsv2-lookup"):
            payload = self.claude_payload(isolation=None)
            payload["tool_input"]["subagent_type"] = agent
            with self.subTest(agent=agent):
                self.assertIsNone(parse_dispatch_payload(payload))

    def test_broken_manifest_isolation_value_fails_close(self):
        # manifest 破損（非文字列・空）を「要求なし」と誤読して素通ししない。
        for broken in ("", None, 1, True, ["worktree"]):
            transport = {
                "required_tool_input_fields": ["subagent_type", "prompt"],
                "forbidden_tool_input_fields": ["agent_type"],
                "required_isolation": broken,
            }
            with self.subTest(broken=broken), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_MANIFEST_CONTRACT_ERROR"
            ):
                _validate_tool_input_shape(
                    {"subagent_type": "issue-implementer", "prompt": "x", "isolation": "worktree"},
                    transport,
                )


class EvaluationTests(unittest.TestCase):
    def test_allow_contains_blocker_evidence_only(self):
        collector = Collector(load("closed_direct.json"))
        result = evaluate_issue_start(request(), collector_factory=lambda token: collector)
        self.assertEqual((result["result"], result["exit_code"]), ("ALLOW", 0))
        self.assertEqual(result["reason"], "ISSUE_START_ALLOWED")
        self.assertNotIn("branch_source_evidence", result)
        self.assertEqual(collector.waiver_calls, 0)

    def test_block_and_collection_error_preserve_verdict(self):
        for fixture, verdict in [("open_direct.json", "BLOCK"), ("cycle.json", "ERROR")]:
            result = evaluate_issue_start(
                request(), collector_factory=lambda token, f=fixture: Collector(load(f))
            )
            self.assertEqual(result["result"], verdict)
            self.assertNotIn("branch_source_evidence", result)

    def test_block_report_has_number_title_url_path_and_next_action(self):
        result = evaluate_issue_start(
            request(), collector_factory=lambda token: Collector(load("open_direct.json"))
        )
        item = result["blockers"][0]
        self.assertEqual(item["number"], 9)
        self.assertEqual(item["title"], "blocker 9")
        self.assertIn("/issues/9", item["url"])
        self.assertEqual(item["path"], ["example/repo#10", "example/repo#9"])
        self.assertIn("fresh invocation", item["next_action"])

    def test_repository_issue_binding_mismatch_is_error(self):
        bad = load("closed_direct.json")
        bad["subject"]["number"] = 11
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BLOCKER_BINDING_MISMATCH"):
            evaluate_issue_start(request(), collector_factory=lambda token: Collector(bad))


class HookTests(unittest.TestCase):
    def managed_payload(self, task_name="issue_10"):
        return {
            "cwd": str(ROOT),
            "tool_name": "collaborationspawn_agent",
            "tool_input": {
                "agent_type": "issue-implementer",
                "task_name": task_name,
                "message": "ENC[AQICAH-encrypted-prompt]",
            },
        }

    def test_malformed_managed_dispatch_emits_deny(self):
        stdout = io.StringIO()
        rc = run_hook(
            stdin=io.StringIO(json.dumps(self.managed_payload("issue-10"))),
            stdout=stdout,
            stderr=io.StringIO(),
            cwd=ROOT,
        )
        self.assertEqual(rc, 0)
        output = json.loads(stdout.getvalue())
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_codex_encrypted_message_allow_reaches_evaluation(self):
        evidence = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
        }
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch(
            "issue_start.hook.resolve_github_token", return_value="credential-from-gh"
        ), patch("issue_start.hook.evaluate_issue_start", return_value=evidence) as evaluate:
            run_hook(
                stdin=io.StringIO(json.dumps(self.managed_payload())),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
            )
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ISSUE_START_ALLOWED", stderr.getvalue())
        self.assertEqual(evaluate.call_args.args[0].issue, 10)
        self.assertEqual(evaluate.call_args.args[0].repository, "hiratashinnya/review-system")
        self.assertEqual(evaluate.call_args.kwargs["token"], "credential-from-gh")

    def test_issue_317_equivalent_allows_with_mocked_gh_credential(self):
        repository = "hiratashinnya/review-system"
        snapshot = {
            "schema": "blocker-gate-snapshot/v1",
            "policy_version": "1.0",
            "mode": "issue-start",
            "repository": repository,
            "subject": {"type": "issue", "number": 317},
            "roots": [f"{repository}#317"],
            "virtual_closed": [],
            "nodes": {
                f"{repository}#317": {
                    "node_id": "I317",
                    "state": "OPEN",
                    "blocked_by": [f"{repository}#316"],
                    "parent": None,
                    "children": [],
                },
                f"{repository}#316": {
                    "node_id": "I316",
                    "state": "CLOSED_COMPLETED",
                    "blocked_by": [],
                    "parent": None,
                    "children": [],
                },
            },
            "pages_complete": True,
            "errors": [],
            "fetched_at": "2026-08-09T00:00:00Z",
            "graphql_closing_set": [],
            "delivered_message_closing_set": [],
            "binding": {},
        }
        secret = "credential-from-mocked-gh"

        def evaluate(request, *, token):
            self.assertEqual(token, secret)
            return evaluate_issue_start(
                request,
                token=token,
                collector_factory=lambda actual: Collector(snapshot),
            )

        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=secret), patch(
            "issue_start.hook.evaluate_issue_start", side_effect=evaluate
        ):
            rc = run_hook(
                stdin=io.StringIO(json.dumps(self.managed_payload("issue_317"))),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
            )
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ISSUE_START_ALLOWED", stderr.getvalue())
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())

    def test_claude_runtime_agent_alias_allow_reaches_evaluation(self):
        evidence = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
        }
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER
                + json.dumps(claude_binding(), separators=(",", ":")),
                "description": "hook deny probe",
                "isolation": "worktree",
            },
        }
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start", return_value=evidence
        ) as evaluate:
            run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
            )
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ISSUE_START_ALLOWED", stderr.getvalue())
        self.assertEqual(evaluate.call_args.args[0], request())

    def test_missing_isolation_denies_before_any_github_evaluation(self):
        """Issue #350 AC4: `isolation` 欠落を hook が機械的に deny し、直し方を deny 文に載せる。"""
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER
                + json.dumps(claude_binding(), separators=(",", ":")),
                "description": "hook deny probe",
            },
        }
        stdout = io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start"
        ) as evaluate:
            rc = run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout,
                stderr=io.StringIO(),
                cwd=ROOT,
            )
        self.assertEqual(rc, 0)
        decision = json.loads(stdout.getvalue())["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        reason = decision["permissionDecisionReason"]
        self.assertIn("ISSUE_START_ISOLATION_NOT_WORKTREE", reason)
        # 「isolation を worktree にせよ」が deny 文だけで読み取れること（reason code だけにしない）。
        self.assertIn("isolation=worktree", reason)
        self.assertIn("actual=None", reason)
        # blocker 判定（GitHub API）まで進まずに落ちる＝dispatch 前に閉じる。
        evaluate.assert_not_called()

    def test_block_deny_reason_preserves_actionable_blocker_report(self):
        blocker = {
            "number": 9,
            "repository": "example/repo",
            "title": "required blocker",
            "url": "https://github.com/example/repo/issues/9",
            "path": ["example/repo#10", "example/repo#9"],
            "next_action": "blockerをcloseしてfresh invocationで再試行する",
        }
        evidence = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "BLOCK",
            "exit_code": 10,
            "reason": "OPEN_BLOCKER",
            "blockers": [blocker],
        }
        stdout = io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start", return_value=evidence
        ):
            run_hook(
                stdin=io.StringIO(json.dumps(self.managed_payload())),
                stdout=stdout,
                stderr=io.StringIO(),
                cwd=ROOT,
            )
        reason = json.loads(stdout.getvalue())["hookSpecificOutput"]["permissionDecisionReason"]
        report = json.loads(reason.split(" blockers=", 1)[1])
        self.assertEqual(report, [blocker])


if __name__ == "__main__":
    unittest.main()
