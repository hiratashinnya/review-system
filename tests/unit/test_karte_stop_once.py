"""One-shot STOP: scope, replay, owner-question exemption and regression cases."""
import fcntl
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karte_stop_once import decision, hook, state, store

SESSION = "abcd-1234-session"


def status(issue=513, verdict="harmful-open", undecided=None, stalled=None, saturated=None):
    return {"issue": issue, "verdict": verdict,
            "undecided_disposition": undecided or [], "blocking_findings": undecided or [],
            "stalled_findings": stalled or [], "saturated_groups": saturated or [],
            "escalate": bool(stalled or saturated)}


def done(command, output, session=SESSION):
    return {"session_id": session, "tool_name": "Bash",
            "tool_input": {"command": command}, "tool_response": {"stdout": output}}


def tool(name, session=SESSION):
    return {"session_id": session, "tool_name": name}


class OneShotStopTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.command = "python3 -m karte ingest-review --issue 513 --round 1"
        self.output = "=== ingest-review: issue-513 round 1 ==="

    def post(self, value, session=SESSION, command=None, output=None):
        return hook.run("post", done(command or self.command, output or self.output, session),
                        root=self.root, status_reader=lambda root, issue: value)

    def pre(self, name, session=SESSION):
        return hook.run("pre", tool(name, session), root=self.root)

    def test_one_denial_then_continue(self):
        self.assertIsNotNone(self.post(status(undecided=["F-513-01"])))
        rejection = self.pre("Bash")
        self.assertEqual(rejection["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("オーナー", rejection["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertIsNone(self.pre("Bash"))
        self.assertIsNone(self.post(status(undecided=["F-513-01"])))
        self.assertIsNone(self.pre("Edit"))

    def test_correct_question_does_not_get_blocked(self):
        self.post(status(undecided=["F-513-01"]))
        self.assertIsNone(self.pre("AskUserQuestion"))
        self.assertIsNone(self.pre("Bash"))

    def test_todo_tools_pass_and_keep_the_denial(self):
        for name in ("TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet"):
            session = f"todo-pass-{name}"
            with self.subTest(tool=name):
                self.assertIsNotNone(self.post(status(undecided=["F-513-01"]), session=session))
                self.assertIsNone(self.pre(name, session))
                self.assertIsNotNone(self.pre("Bash", session))
                self.assertIsNone(self.pre("Bash", session))

    def test_status_is_read_while_the_state_lock_is_held(self):
        held = []

        def reader(root, issue):
            path = store.state_file(root, SESSION)
            fd = os.open(str(path) + ".lock", os.O_RDWR)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held.append(False)
            except BlockingIOError:
                held.append(True)
            finally:
                os.close(fd)
            return status(undecided=["F-513-01"])

        hook.run("post", done(self.command, self.output), root=self.root, status_reader=reader)
        self.assertEqual(held, [True])

    def test_invalid_state_shape_is_logged_not_raised(self):
        self.post(status(undecided=["F-513-01"]))
        path = store.state_file(self.root, SESSION)
        for text in ('{"events": []}', '{"events": {"513": []}}', '[]',
                     '{"events": {"513": {"digest": "x", "denied": "0", "followup_tools": []}}}'):
            with self.subTest(text=text):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    state.attempt(self.root, SESSION, "Bash")
        path.write_text('{"events": []}', encoding="utf-8")
        stdin = io.StringIO(json.dumps(tool("Bash")))
        stderr = io.StringIO()
        with patch("sys.stdin", stdin), patch("sys.stderr", stderr), \
                patch.object(hook, "_root", return_value=self.root):
            self.assertEqual(hook.main(["pre"]), 0)
        self.assertIn("karte_stop_once:", stderr.getvalue())

    def test_new_stop_reason_gets_another_denial(self):
        self.post(status(undecided=["F-513-01"]))
        self.pre("Bash")
        self.post(status(undecided=["F-513-01", "F-513-02"]))
        self.assertIsNotNone(self.pre("Edit"))

    def test_no_harm_only_and_escalate_are_independent(self):
        for status_value in (status(verdict="no-harm-only"), status(stalled=["F-513-01"])):
            self.assertIsNotNone(decision.evaluate(status_value))
        self.assertIsNone(decision.evaluate(status()))

    def test_other_session_never_blocked(self):
        self.post(status(undecided=["F-513-01"]))
        self.assertIsNone(self.pre("Bash", session="other-session-456"))
        self.assertIsNotNone(self.pre("Bash"))

    def test_mismatched_or_ambiguous_issue_does_not_arm(self):
        self.assertIsNone(self.post(status(undecided=["F-513-01"]), output="=== ingest-review: issue-514 round 1 ==="))
        self.assertIsNone(self.pre("Bash"))
        self.assertIsNone(self.post(status(undecided=["F-513-01"]), output="No issue marker"))

    def test_append_arms_without_explicit_issue(self):
        command = "python3 -m karte append --finding-ids F-513-01"
        output = "=== append: issue-513 Attempt 1（round 1）==="
        self.assertIsNotNone(self.post(status(undecided=["F-513-01"]), command=command, output=output))

    def test_cleared_status_resets_for_future_same_reason(self):
        self.post(status(undecided=["F-513-01"]))
        self.pre("Bash")
        self.post(status())
        self.assertIsNone(self.pre("Bash"))
        self.assertIsNotNone(self.post(status(undecided=["F-513-01"])))
        self.assertIsNotNone(self.pre("Edit"))

    def test_json_status_arms_and_denies(self):
        command = "python3 -m karte status --issue 513 --json"
        value = status(undecided=["F-513-01"])
        self.assertIsNotNone(self.post(value, command=command, output=json.dumps(value)))
        self.assertIsNotNone(self.pre("Edit"))

    def test_json_status_rejects_wrong_issue_or_invalid_result(self):
        command = "python3 -m karte status --issue 514 --json"
        value = status(issue=513, undecided=["F-513-01"])
        self.assertIsNone(self.post(value, command=command, output=json.dumps(value)))
        self.assertIsNone(self.pre("Edit"))
        self.assertIsNone(self.post(value, command=command, output='{"issue": 514}'))
        self.assertIsNone(self.pre("Bash"))

    def test_other_issue_clean_preserves_stop_history(self):
        finding = status(undecided=["F-513-01"])
        self.post(finding)
        self.assertIsNotNone(self.pre("Bash"))
        other_command = "python3 -m karte status --issue 514"
        other_output = "=== status: issue-514 ==="
        self.assertIsNone(self.post(status(issue=514), command=other_command,
                                    output=other_output))
        self.assertIsNone(self.post(finding))  # Identical STOP does not rearm.
        self.assertIsNone(self.pre("Edit"))

    def test_other_issue_stop_preserves_original_history(self):
        finding = status(undecided=["F-513-01"])
        self.post(finding)
        self.assertIsNotNone(self.pre("Bash"))
        other_command = "python3 -m karte status --issue 514"
        other_output = "=== status: issue-514 ==="
        self.assertIsNotNone(self.post(status(issue=514, stalled=["F-514-01"]),
                                       command=other_command, output=other_output))
        self.assertIsNotNone(self.pre("Edit"))
        self.assertIsNone(self.post(finding))
        self.assertIsNone(self.pre("Bash"))

    def observe(self, tool_name, tool_input, response, session=SESSION):
        payload = {"session_id": session, "tool_name": tool_name,
                   "tool_input": tool_input, "tool_response": response}
        return hook.run("post", payload, root=self.root,
                        status_reader=lambda root, issue:
                        status(issue=issue, undecided=[f"F-{issue}-01"]))

    def test_mcp_text_results_across_registered_execution_tools(self):
        cases = [
            ("mcp__plugin_context-mode_context-mode__ctx_execute",
             {"code": self.command}, {"content": [{"type": "text", "text": self.output}]}),
            ("mcp__plugin_context-mode_context-mode__ctx_batch_execute",
             {"commands": [{"command": self.command}]},
             {"content": [{"text": self.output}]}),
            ("Bash", {"command": self.command}, {"content": self.output}),
            ("Bash", {"command": self.command}, self.output),
        ]
        for index, (name, arguments, result) in enumerate(cases):
            session = f"mcp-output-case-{index}"
            with self.subTest(tool=name, form=index):
                self.assertIsNotNone(self.observe(name, arguments, result, session))
                self.assertIsNotNone(self.pre("Edit", session))
                self.assertIsNone(self.pre("Edit", session))

    def test_mcp_json_status_and_ingest_reviewer(self):
        command = "python3 -m karte status --issue 513 --json"
        result = {"content": [{"type": "text",
                              "text": json.dumps(status(undecided=["F-513-01"]))}]}
        self.assertIsNotNone(self.observe("Bash", {"command": command}, result))
        self.assertIsNotNone(self.pre("Edit"))
        reviewer = "python3 -m karte ingest-reviewer --issue 513 --round 2"
        self.assertIsNotNone(self.observe(
            "Bash", {"command": reviewer},
            {"stdout": "=== ingest-review: issue-513 round 2 ==="},
            "mcp-reviewer-session"))

    def test_decide_result_binds_by_finding_id(self):
        command = "python3 -m karte decide --finding F-513-01 --disposition fix-here"
        response = {"content": [{"type": "text",
                                "text": "=== decide: F-513-01 ==="}]}
        self.assertIsNotNone(self.observe("Bash", {"command": command}, response))
        self.assertIsNotNone(self.pre("Bash"))

    def test_decide_accepts_quoted_finding_forms(self):
        # The CLI strips shell quoting; PostToolUse must recognize the original command.
        variants = (
            "--finding F-513-01", "--finding=F-513-01",
            "--finding 'F-513-01'", '--finding "F-513-01"',
            "--finding='F-513-01'", '--finding="F-513-01"',
        )
        for index, argument in enumerate(variants):
            session = f"decide-quoting-{index}"
            command = f"python3 -m karte decide --issue 513 {argument} --disposition fix-here"
            with self.subTest(argument=argument):
                self.assertIsNotNone(self.post(
                    status(undecided=["F-513-02"]), session=session, command=command,
                    output="=== decide: F-513-01 ==="))
                self.assertIsNotNone(self.pre("Edit", session))
                self.assertIsNone(self.pre("Edit", session))

    def test_decide_rejects_malformed_or_mismatched_quotes(self):
        variants = (
            "--finding 'F-513-01",
            "--finding 'F-513-01'-extra",
            '--finding "F-513-02"',
        )
        for index, argument in enumerate(variants):
            session = f"decide-bad-quoting-{index}"
            command = f"python3 -m karte decide --issue 513 {argument} --disposition fix-here"
            with self.subTest(argument=argument):
                self.assertIsNone(self.post(
                    status(undecided=["F-513-02"]), session=session, command=command,
                    output="=== decide: F-513-01 ==="))
                self.assertIsNone(self.pre("Edit", session))

    def test_decide_rejects_mismatched_finding_or_explicit_issue(self):
        output = {"stdout": "=== decide: F-513-01 ==="}
        for index, command in enumerate((
            "python3 -m karte decide --finding F-513-02 --disposition fix-here",
            "python3 -m karte decide --issue 514 --finding F-513-01 --disposition fix-here",
            "python3 -m karte decide --disposition fix-here",
        )):
            session = f"decide-mismatch-{index}"
            self.assertIsNone(self.observe("Bash", {"command": command}, output, session))
            self.assertIsNone(self.pre("Edit", session))

    def test_mcp_result_error_or_nontext_does_not_arm(self):
        invalid = [
            {"content": [{"type": "text", "text": self.output}], "isError": True},
            {"content": [{"type": "text", "text": self.output}], "exit_code": 4},
            {"stdout": self.output, "returncode": 1},
            {"stdout": self.output, "interrupted": True},
            {"content": [{"type": "image", "text": self.output}]},
            {"content": [{"type": "text", "text": "unrelated"}]},
        ]
        for index, response in enumerate(invalid):
            session = f"result-failure-{index}"
            with self.subTest(result=index):
                self.assertIsNone(self.observe(
                    "mcp__plugin_context-mode_context-mode__ctx_execute",
                    {"code": self.command}, response, session))
                self.assertIsNone(self.pre("Edit", session))

    def test_mcp_conflicting_issues_do_not_bind(self):
        response = {"content": [
            {"type": "text", "text": "=== ingest-review: issue-513 round 1 ==="},
            {"type": "text", "text": "=== ingest-review: issue-514 round 1 ==="},
        ]}
        self.assertIsNone(self.observe("Bash", {"command": self.command}, response))
        self.assertIsNone(self.pre("Bash"))

    def test_mcp_result_mismatching_explicit_issue_does_not_bind(self):
        response = {"content": [{"type": "text",
                                "text": "=== ingest-review: issue-514 round 1 ==="}]}
        self.assertIsNone(self.observe("Bash", {"command": self.command}, response))
        self.assertIsNone(self.pre("Edit"))

    def test_nontarget_commands_do_nothing(self):
        self.assertIsNone(hook.run("post", done("echo hello", self.output), root=self.root))
        self.assertFalse((self.root / "tmp" / "_karte").exists())


if __name__ == "__main__":
    unittest.main()
