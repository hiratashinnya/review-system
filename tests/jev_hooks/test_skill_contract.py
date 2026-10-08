"""Validation evidence belongs to the exact contract of its own Skill step."""
import json
import unittest
import test_skills


class SkillContractTests(unittest.TestCase):
    setUp = test_skills.SkillTests.setUp
    event = test_skills.SkillTests.event
    activate = test_skills.SkillTests.activate
    verify = test_skills.SkillTests.verify

    def replace_step_fields(self, changes, index=0):
        path = self.root / "definition.json"
        definition = json.loads(path.read_text())
        definition["steps"][index].update(changes)
        path.write_text(json.dumps(definition))

    def start(self, identifier, command):
        self.assertEqual(self.event("PreToolUse", identifier=identifier,
                                    tool_input={"command": command}), {})

    def finish(self, identifier, command):
        self.event("PostToolUse", identifier=identifier, tool_input={"command": command},
                   tool_response={"exit_code": 0})

    def assert_gates(self, blocked, identifier):
        self.assertEqual(bool(self.event("Stop", last_assistant_message="done")), blocked)
        self.assertEqual(bool(self.event("PreToolUse", identifier=identifier,
                                        tool_input={"command": "deliver"})), blocked)

    def contracts(self):
        return [("evidence", {"evidence": {"tool": "Bash", "input": {"command": "test-v2"}}}, "test-v2"),
                ("watch", {"watch": ["*.py", "absent.txt"]}, "test")]

    def test_contract_change_invalidates_success_and_new_validation_recovers(self):
        for kind, changes, command in self.contracts():
            with self.subTest(kind=kind):
                self.base["session_id"] = kind
                self.replace_step_fields({"evidence": {"tool": "Bash", "input": {"command": "test"}},
                                          "watch": ["*.py"]})
                self.activate()
                self.verify("A")
                self.assert_gates(False, "before")
                self.replace_step_fields(changes)
                self.assert_gates(True, "changed")
                self.start("B", command)
                self.finish("B", command)
                self.assert_gates(False, "recovered")

    def test_contract_change_rejects_old_pending_result_and_recovers(self):
        for kind, changes, command in self.contracts():
            with self.subTest(kind=kind):
                self.base["session_id"] = kind
                self.replace_step_fields({"evidence": {"tool": "Bash", "input": {"command": "test"}},
                                          "watch": ["*.py"]})
                self.activate()
                self.start("A", "test")
                self.replace_step_fields(changes)
                self.finish("A", command)
                self.assert_gates(True, "old-result")
                self.start("B", command)
                self.finish("B", command)
                self.assert_gates(False, "recovered")

    def test_unrelated_step_change_preserves_success(self):
        path = self.root / "definition.json"
        definition = json.loads(path.read_text())
        definition["steps"].append({"id": "optional", "kind": "optional", "watch": [],
                                     "evidence": {"tool": "Bash", "input": {"command": "other"}}})
        path.write_text(json.dumps(definition))
        self.activate()
        self.verify("A")
        self.assert_gates(False, "before")
        self.replace_step_fields({"evidence": {"tool": "Bash", "input": {"command": "other-v2"}}}, 1)
        self.assert_gates(False, "after")
