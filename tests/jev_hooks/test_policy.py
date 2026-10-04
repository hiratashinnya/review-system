"""Control tests use declared mock labels, not claims about model accuracy."""
import unittest
from jev_hooks.config import load_config
from jev_hooks.policy import decide, violations


def labels(**values):
    return {key: {"value": value, "confidence": .99} for key, value in values.items()}


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.config.update(mode="enforce", research_tools=["Read"])
        self.event = {"hook_event_name": "Stop"}
        self.evidence = {"research_tools": ["Read"], "tool_calls": {}, "tool_results": {},
                         "history_complete": True}

    def rules(self, **answers):
        return violations(self.event, self.evidence, labels(**answers), [], self.config)

    def test_r1_violation_nonviolation_unknown_and_asked(self):
        for waiting, asked, expected in [(True, False, True), (False, False, False),
                                       (None, False, False), (True, True, False), (True, None, False)]:
            self.assertEqual("R1" in self.rules(r1_waiting_for_answer=waiting,
                             r1_question_already_asked=asked), expected)

    def test_r2_relevant_research_only_and_unknown(self):
        for relevant, expected in [(False, True), (True, False), (None, False)]:
            self.assertEqual("R2" in self.rules(r2_researchable=True,
                r2_research_available=True, r2_research_relevant=relevant), expected)
        self.assertNotIn("R2", self.rules(r2_researchable=False))
        self.evidence["research_tools"] = []
        self.assertNotIn("R2", self.rules(r2_researchable=True,
            r2_research_available=True, r2_research_relevant=False))

    def test_r3_requires_complete_public_history(self):
        self.event.update(hook_event_name="PreToolUse", tool_name="AskUserQuestion")
        for value, expected in [(False, True), (True, False), (None, False)]:
            self.assertEqual("R3" in self.rules(r3_explanation_sufficient=value), expected)
        self.evidence["history_complete"] = False
        self.assertNotIn("R3", self.rules(r3_explanation_sufficient=False))

    def test_unavailable_question_tool_does_not_exempt_research(self):
        self.config["question_tool_available"] = False
        found = self.rules(r1_waiting_for_answer=True, r1_question_already_asked=False,
            r2_researchable=True, r2_research_available=True, r2_research_relevant=False)
        self.assertEqual(set(found), {"R2"})

    def test_budget_shadow_and_explicit_prerequisites(self):
        state = {"blocks": {}}
        for _ in range(2):
            self.assertEqual(decide(self.event, {"R1": "fix"}, state, self.config)["decision"], "block")
        self.assertEqual(decide(self.event, {"R1": "fix"}, state, self.config), {})
        self.event["stop_hook_active"] = True
        self.assertEqual(decide(self.event, {"R4": "test"}, state, self.config)["decision"], "block")
        self.config["mode"] = "shadow"
        self.assertEqual(decide(self.event, {"R4": "test"}, state, self.config), {})
