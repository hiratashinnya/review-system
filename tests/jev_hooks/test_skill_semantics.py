"""Semantic operation relevance cannot replace observed validation evidence."""
import unittest
import test_skills
from jev_hooks.runner import run_event


class SemanticEvaluator:
    def evaluate(self, evidence, question_ids):
        role = evidence.get("skill_context", {}).get("role")
        value = role == "operation"
        return {key: {"value": value, "confidence": 1.0} for key in question_ids}


class SkillSemanticTests(unittest.TestCase):
    setUp = test_skills.SkillTests.setUp
    activate = test_skills.SkillTests.activate
    event = test_skills.SkillTests.event
    verify = test_skills.SkillTests.verify

    def test_equivalent_operation_is_gated_before_success(self):
        self.activate()
        event = dict(self.base, hook_event_name="PreToolUse", tool_name="Bash",
                     tool_use_id="semantic-delivery", tool_input={"command": "deliver --ready"})
        self.assertTrue(run_event(event, self.config, SemanticEvaluator()))

    def test_semantic_unknown_keeps_recovery_open(self):
        self.activate()
        self.assertEqual(self.event("PreToolUse", identifier="recover",
                                    tool_input={"command": "test --verbose"}), {})

    def test_semantic_step_requires_pair_exit_and_latest_snapshot(self):
        import json
        path = self.root / "definition.json"
        definition = json.loads(path.read_text())
        definition["steps"][0]["evidence"]["semantic"] = "Run the validation suite"
        path.write_text(json.dumps(definition))
        self.activate()
        class StepEvaluator:
            def evaluate(self, evidence, question_ids):
                return {key: {"value": evidence.get("skill_context", {}).get("role") == "step", "confidence": 1}
                        for key in question_ids}
        def execute(kind, identifier, output=None):
            return run_event(dict(self.base, hook_event_name=kind, tool_name="Bash", tool_use_id=identifier,
                tool_input={"command": "test --verbose"}, tool_response=output), self.config, StepEvaluator())
        execute("PostToolUse", "unpaired", {"exit_code": 0})
        self.assertTrue(self.event("Stop"))
        execute("PreToolUse", "failed")
        execute("PostToolUse", "failed", {"exit_code": 1})
        self.assertTrue(self.event("Stop"))
        execute("PreToolUse", "claim")
        execute("PostToolUse", "claim", "all tests passed")
        self.assertTrue(self.event("Stop"))
        execute("PreToolUse", "valid")
        execute("PostToolUse", "valid", {"exit_code": 0})
        self.assertEqual(self.event("Stop"), {})

    def test_recovery_yes_does_not_override_a_protected_compound_operation(self):
        self.activate()
        class BothEvaluator:
            def evaluate(self, evidence, question_ids):
                return {key: {"value": True, "confidence": 1} for key in question_ids}
        event = dict(self.base, hook_event_name="PreToolUse", tool_name="Bash", tool_use_id="compound",
                     tool_input={"command": "test && deliver"})
        self.assertTrue(run_event(event, self.config, BothEvaluator()))
