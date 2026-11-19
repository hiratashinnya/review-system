"""One-shot STOP: scope, replay, owner-question exemption and regression cases."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karte_stop_once import decision, state, hook

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

    def test_nontarget_commands_do_nothing(self):
        self.assertIsNone(hook.run("post", done("echo hello", self.output), root=self.root))
        self.assertFalse((self.root / "tmp" / "_karte").exists())


if __name__ == "__main__":
    unittest.main()
