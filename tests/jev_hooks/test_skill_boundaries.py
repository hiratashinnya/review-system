"""Replay, schema variants and recovery after validation failures."""
import json
import unittest
import test_skills


class SkillBoundaryTests(unittest.TestCase):
    setUp = test_skills.SkillTests.setUp
    event = test_skills.SkillTests.event
    activate = test_skills.SkillTests.activate
    verify = test_skills.SkillTests.verify

    def test_replayed_validation_cannot_certify_edited_code(self):
        self.activate()
        self.verify("same")
        (self.root / "code.py").write_text("unverified = True")
        self.verify("same")
        self.assertTrue(self.event("Stop"))

    def test_conditional_optional_and_recovery(self):
        path = self.root / "definition.json"
        definition = json.loads(path.read_text())
        definition["steps"][0].update(kind="conditional", when={"path_exists": "ENABLE"})
        definition["steps"].append({"id": "optional", "kind": "optional", "watch": [],
                                     "evidence": {"tool": "Bash", "input": {"command": "optional"}}})
        definition["stop_requires"].append("optional")
        definition["operations"][0].pop("input")
        definition["recovery"] = [{"tool": "Bash", "input": {"command": "inspect"}}]
        path.write_text(json.dumps(definition))
        self.activate()
        self.assertEqual(self.event("Stop"), {})
        (self.root / "ENABLE").touch()
        self.assertTrue(self.event("Stop"))
        self.assertEqual(self.event("PreToolUse", identifier="inspect", tool_input={"command": "inspect"}), {})
        self.verify("recovery")
        self.assertEqual(self.event("Stop"), {})
