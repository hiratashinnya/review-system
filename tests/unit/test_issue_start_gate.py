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


class DispatchPayloadTests(unittest.TestCase):
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

    def claude_payload(self, binding=None, *, tool="Task"):
        raw = claude_binding() if binding is None else binding
        return {
            "tool_name": tool,
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER + json.dumps(raw, separators=(",", ":")),
                "description": "hook deny probe",
            },
        }

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
        with patch("issue_start.hook.evaluate_issue_start", return_value=evidence) as evaluate:
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
            },
        }
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.hook.evaluate_issue_start", return_value=evidence) as evaluate:
            run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
            )
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ISSUE_START_ALLOWED", stderr.getvalue())
        self.assertEqual(evaluate.call_args.args[0], request())

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
        with patch("issue_start.hook.evaluate_issue_start", return_value=evidence):
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
