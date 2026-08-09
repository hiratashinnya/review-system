"""Issue #297 managed Issue-start adapter/hook tests。"""

import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from branch_source import BranchSourceResult
from issue_start.gate import (
    BINDING_MARKER,
    IssueStartError,
    IssueStartRequest,
    evaluate_issue_start,
    parse_dispatch_payload,
)
from issue_start.hook import run as run_hook


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


def request():
    return IssueStartRequest(
        "issue-pipeline", "example/repo", 10, "issue-297", "main", OID, None
    )


def source():
    return BranchSourceResult("example/repo", "main", OID, "default-branch", None)


class DispatchPayloadTests(unittest.TestCase):
    def payload(self, binding=None, agent="issue-implementer", tool="spawn_agent"):
        marker = "" if binding is None else BINDING_MARKER + json.dumps(binding, separators=(",", ":"))
        return {"tool_name": tool, "tool_input": {"agent_type": agent, "message": marker}}

    def test_codex_and_claude_payloads_share_binding_contract(self):
        raw = request().__dict__
        self.assertEqual(parse_dispatch_payload(self.payload(raw)), request())
        observed_codex = self.payload(raw, tool="collaborationspawn_agent")
        self.assertEqual(parse_dispatch_payload(observed_codex), request())
        claude = {"tool_name": "Task", "tool_input": {
            "subagent_type": "issue-implementer",
            "prompt": BINDING_MARKER + json.dumps(raw, separators=(",", ":")),
        }}
        self.assertEqual(parse_dispatch_payload(claude), request())

    def test_unknown_missing_duplicate_and_extra_fields_deny(self):
        cases = [
            self.payload(),
            self.payload(request().__dict__, tool="unknown"),
            {"tool_name": "spawn_agent", "tool_input": {
                "agent_type": "issue-implementer",
                "message": "\n".join([BINDING_MARKER + "{}", BINDING_MARKER + "{}"]),
            }},
            self.payload({**request().__dict__, "unexpected": True}),
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(IssueStartError):
                    parse_dispatch_payload(payload)

    def test_alias_dotted_and_similar_tool_names_are_not_payload_aliases(self):
        for tool_name in (
            "Agent",
            "collaboration.spawn_agent",
            "evil.spawn_agent",
            "evilspawn_agent",
            "collaborationspawn_agent_extra",
            "collaborationspawn_agents",
        ):
            with self.subTest(tool_name=tool_name), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_ENTRYPOINT_UNKNOWN"
            ):
                parse_dispatch_payload(self.payload(request().__dict__, tool=tool_name))

    def test_non_issue_agent_is_explicitly_unmanaged(self):
        self.assertIsNone(parse_dispatch_payload(self.payload(agent="explorer")))

    def test_missing_target_is_fail_close(self):
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_TARGET_UNKNOWN"):
            parse_dispatch_payload({"tool_name": "spawn_agent", "tool_input": {"message": "x"}})


class EvaluationTests(unittest.TestCase):
    def test_allow_combines_blocker_and_branch_evidence(self):
        collector = Collector(load("closed_direct.json"))
        result = evaluate_issue_start(
            request(), collector_factory=lambda token: collector,
            branch_api_factory=lambda token: object(),
            branch_verifier=lambda *args, **kwargs: source(),
        )
        self.assertEqual((result["result"], result["exit_code"]), ("ALLOW", 0))
        self.assertEqual(result["reason"], "ISSUE_START_ALLOWED")
        self.assertEqual(result["branch_source_evidence"]["source_oid"], OID)
        self.assertEqual(collector.waiver_calls, 0)

    def test_block_and_collection_error_never_reach_branch_policy(self):
        for fixture, verdict in [("open_direct.json", "BLOCK"), ("cycle.json", "ERROR")]:
            calls = []
            result = evaluate_issue_start(
                request(), collector_factory=lambda token, f=fixture: Collector(load(f)),
                branch_verifier=lambda *args, **kwargs: calls.append(True),
            )
            self.assertEqual(result["result"], verdict)
            self.assertEqual(calls, [])

    def test_block_report_has_number_title_url_path_and_next_action(self):
        result = evaluate_issue_start(
            request(), collector_factory=lambda token: Collector(load("open_direct.json")),
            branch_verifier=lambda *args, **kwargs: self.fail("branch policy must not run"),
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
            evaluate_issue_start(
                request(), collector_factory=lambda token: Collector(bad),
                branch_verifier=lambda *args, **kwargs: source(),
            )


class HookTests(unittest.TestCase):
    def managed_payload(self):
        return {"tool_name": "spawn_agent", "tool_input": {
            "agent_type": "issue-implementer",
            "message": BINDING_MARKER + json.dumps(request().__dict__, separators=(",", ":")),
        }}

    def test_malformed_managed_dispatch_emits_deny(self):
        stdout = io.StringIO()
        rc = run_hook(
            stdin=io.StringIO(json.dumps({
                "tool_name": "spawn_agent",
                "tool_input": {"agent_type": "issue-implementer", "message": "missing"},
            })), stdout=stdout, stderr=io.StringIO()
        )
        self.assertEqual(rc, 0)
        output = json.loads(stdout.getvalue())
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_allow_keeps_stdout_empty_and_logs_evidence(self):
        evidence = {
            "schema_version": "issue-start-evidence/1", "policy_version": "issue-start/1.0",
            "result": "ALLOW", "exit_code": 0, "reason": "ISSUE_START_ALLOWED",
        }
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.hook.evaluate_issue_start", return_value=evidence):
            run_hook(
                stdin=io.StringIO(json.dumps(self.managed_payload())),
                stdout=stdout,
                stderr=stderr,
            )
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ISSUE_START_ALLOWED", stderr.getvalue())

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
            )
        reason = json.loads(stdout.getvalue())["hookSpecificOutput"]["permissionDecisionReason"]
        report = json.loads(reason.split(" blockers=", 1)[1])
        self.assertEqual(report, [blocker])


if __name__ == "__main__":
    unittest.main()
