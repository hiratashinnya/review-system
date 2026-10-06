"""Retain public question context and shell intent with uniform argument projection."""
import json
import unittest
from jev_hooks.outbound_evidence import outbound_evidence
from jev_hooks.outbound_inputs import project_input


class SafetyProjectionTests(unittest.TestCase):
    def test_r3_question_and_public_explanation_are_preserved(self):
        questions = [{"question": "どちらの .env で配色を指定しますか？", "header": "配色",
                      "options": [{"label": "青", "description": "落ち着いた色"}], "multiSelect": False}]
        evidence = {"current_tool_input": {"questions": questions, "extra": "omit-me"},
                    "public_messages": ["背景と選択肢を説明しました。"], "history_complete": True}
        result = outbound_evidence(evidence, ())
        self.assertEqual(result["current_tool_input"], {"questions": questions})
        self.assertEqual(result["public_messages"], evidence["public_messages"])
        self.assertTrue(result["history_complete"])

    def test_normal_file_input_contains_path_without_content(self):
        result = project_input({"file_path": "app.py", "content": "opaque-file-value",
                                "old_string": "opaque-old", "new_string": "opaque-new"}, ())
        self.assertEqual(result, {"file_path": "app.py"})

    def test_r4_shell_intent_is_the_same_in_all_copies(self):
        inputs = {"command": "test --verbose && git push --force origin private-argument-canary"}
        selector = {"tool": "Bash", "input": inputs, "semantic": "Validate and publish", "requires": ["test"]}
        evidence = {"current_tool_input": inputs, "current_turn_tool_ids": ["call"],
                    "tool_calls": {"call": {"name": "Bash", "input": inputs}},
                    "tool_results": {"call": {"content": "shell-output-canary"}},
                    "skill_context": {"current_tool": {"name": "Bash", "input": inputs},
                                      "selector": selector, "protected_operations": [selector], "role": "operation"}}
        result = outbound_evidence(evidence, ())
        expected = "test --verbose && git push --force [ARGUMENT OMITTED] [ARGUMENT OMITTED]"
        self.assertEqual(result["current_tool_input"], {"command": expected})
        self.assertEqual(result["tool_calls"]["call"]["input"], result["current_tool_input"])
        context = result["skill_context"]
        for record in (context["current_tool"], context["selector"], *context["protected_operations"]):
            self.assertEqual(record["input"], result["current_tool_input"])
        self.assertEqual(context["selector"]["semantic"], "Validate and publish")
        self.assertNotIn("canary", json.dumps(result))

    def test_sensitive_body_in_selector_and_operations_is_omitted(self):
        inputs = {"file_path": ".env", "content": "DB_URI=unknown-opaque-canary"}
        selector = {"tool": "Write", "input": inputs, "semantic": "Update configuration", "requires": ["test"]}
        context = {"selector": selector, "protected_operations": [selector],
                   "current_tool": {"name": "Write", "input": inputs}}
        result = outbound_evidence({"skill_context": context, "current_tool_input": inputs}, ())
        self.assertNotIn("canary", json.dumps(result))
        for record in (result["skill_context"]["selector"], *result["skill_context"]["protected_operations"]):
            self.assertIn("OMITTED", record["input"])

    def test_shell_heredoc_body_and_assignment_are_omitted(self):
        result = project_input({"command": "DB_URI=opaque-assignment-canary cat > .env <<'EOF'\nopaque-heredoc-canary\nEOF"}, (), "Bash")
        self.assertEqual(result, {"command": "cat [ARGUMENT OMITTED] [ARGUMENT OMITTED] [HEREDOC OMITTED]"})
        self.assertNotIn("canary", json.dumps(result))
