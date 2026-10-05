"""Conditional Stop replays and overlapping validation attempts stay current."""
import json
import unittest
import test_skills


class SkillOrderingTests(unittest.TestCase):
    setUp = test_skills.SkillTests.setUp
    event = test_skills.SkillTests.event
    activate = test_skills.SkillTests.activate
    verify = test_skills.SkillTests.verify

    def start(self, identifier):
        self.assertEqual(self.event("PreToolUse", identifier=identifier,
                                    tool_input={"command": "test"}), {})

    def finish(self, identifier, failure=None):
        self.event("PostToolUseFailure" if failure == "hook" else "PostToolUse",
                   identifier=identifier, tool_input={"command": "test"},
                   tool_response={"exit_code": 1 if failure else 0})

    def assert_gates(self, blocked, identifier):
        stop = self.event("Stop", last_assistant_message="done")
        delivery = self.event("PreToolUse", identifier=identifier, tool_input={"command": "deliver"})
        self.assertEqual((bool(stop), bool(delivery)), (blocked, blocked))

    def test_same_stop_tracks_unwatched_condition_in_both_directions(self):
        path = self.root / "definition.json"
        definition = json.loads(path.read_text())
        definition["steps"][0].update(kind="conditional", when={"path_exists": "ENABLE"})
        path.write_text(json.dumps(definition))
        for initially_enabled in (False, True):
            with self.subTest(initially_enabled=initially_enabled):
                self.base["session_id"] = str(initially_enabled)
                flag = self.root / "ENABLE"
                if initially_enabled:
                    flag.mkdir(exist_ok=True)
                self.activate()
                for enabled in (initially_enabled, not initially_enabled, initially_enabled):
                    if enabled:
                        flag.mkdir(exist_ok=True)
                    elif flag.exists():
                        flag.rmdir()
                    self.assertEqual(bool(self.event("Stop", last_assistant_message="done")), enabled)
                if flag.exists():
                    flag.rmdir()

    def test_later_failure_wins_over_older_success_and_recovers(self):
        for failure in ("exit", "hook"):
            for older_first in (True, False):
                with self.subTest(failure=failure, older_first=older_first):
                    self.base["session_id"] = f"{failure}-{older_first}"
                    self.activate()
                    self.start("A")
                    self.start("B")
                    completions = [("A", None), ("B", failure)]
                    for identifier, result in completions if older_first else reversed(completions):
                        self.finish(identifier, result)
                    self.assert_gates(True, "blocked")
                    self.verify("C")
                    self.assert_gates(False, "recovered")

    def test_late_older_failure_preserves_newer_success(self):
        for failure in ("exit", "hook"):
            with self.subTest(failure=failure):
                self.base["session_id"] = failure
                self.activate()
                self.start("A")
                self.start("B")
                self.finish("B")
                self.finish("A", failure)
                self.assert_gates(False, "deliver")

    def test_duplicate_older_events_do_not_replace_latest_attempt(self):
        self.activate()
        self.start("A")
        self.start("B")
        self.start("A")
        self.finish("A")
        self.finish("A")
        self.assert_gates(True, "pending")
        self.finish("B")
        self.start("A")
        self.finish("A")
        self.finish("B")
        self.assert_gates(False, "complete")
