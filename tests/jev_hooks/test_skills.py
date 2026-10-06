"""Successful paired execution and unchanged snapshots certify prerequisites."""
import json
import tempfile
import unittest
from pathlib import Path
from jev_hooks.config import load_config
from jev_hooks.runner import run_event


class UnknownEvaluator:
    def evaluate(self, evidence, question_ids):
        raise RuntimeError("API unavailable")


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "SKILL.md").write_text("test before delivery")
        (self.root / "code.py").write_text("value = 1")
        definition = {"id": "sample", "skill_path": "SKILL.md", "steps": [
            {"id": "test", "kind": "required", "evidence": {"tool": "Bash",
             "input": {"command": "test"}}, "watch": ["*.py"]}],
            "operations": [{"tool": "Bash", "input": {"command": "deliver"}, "requires": ["test"]}],
            "stop_requires": ["test"]}
        path = self.root / "definition.json"
        path.write_text(json.dumps(definition))
        self.config = load_config()
        self.config.update(mode="enforce", state_dir=str(self.root / "state"), skill_definitions=[str(path)])
        self.base = {"cwd": str(self.root), "session_id": "skill-session"}

    def event(self, kind, name="Bash", identifier=None, **extra):
        return run_event(dict(self.base, hook_event_name=kind, tool_name=name,
                         tool_use_id=identifier, **extra), self.config, UnknownEvaluator())

    def activate(self):
        self.event("PostToolUse", "Read", "read", tool_input={"file_path": str(self.root / "SKILL.md")},
                   tool_response={"content": "test before delivery"})

    def verify(self, identifier, exit_code=0, edit_during=False):
        inputs = {"command": "test"}
        self.assertEqual(self.event("PreToolUse", identifier=identifier, tool_input=inputs), {})
        if edit_during:
            (self.root / "code.py").write_text("value = 2")
        self.event("PostToolUse", identifier=identifier, tool_input=inputs, tool_response={"exit_code": exit_code})

    def test_unknown_then_block_recovery_failure_and_edit(self):
        self.assertEqual(self.event("Stop"), {})
        self.activate()
        self.assertTrue(self.event("Stop"))
        self.verify("failed", exit_code=1)
        self.assertTrue(self.event("Stop"))
        self.verify("success")
        self.assertEqual(self.event("Stop"), {})
        (self.root / "code.py").write_text("value = 3")
        self.assertTrue(self.event("Stop"))
        self.assertTrue(self.event("PreToolUse", identifier="delivery", tool_input={"command": "deliver"}))
        self.assertEqual(self.event("PreToolUse", "Read", "recover", tool_input={"file_path": "code.py"}), {})

    def test_edit_during_validation_does_not_certify(self):
        self.activate()
        self.verify("racing", edit_during=True)
        self.assertTrue(self.event("Stop"))

    def test_unpaired_post_result_does_not_certify(self):
        self.activate()
        self.event("PostToolUse", identifier="unpaired", tool_input={"command": "test"},
                   tool_response={"exit_code": 0})
        self.assertTrue(self.event("Stop"))

    def test_failed_revalidation_invalidates_prior_success(self):
        self.activate()
        self.verify("pass")
        self.assertEqual(self.event("Stop"), {})
        self.verify("fail", exit_code=1)
        self.assertTrue(self.event("Stop"))

    def test_same_stop_recovers_then_detects_external_edit(self):
        self.activate()
        stop = dict(self.base, hook_event_name="Stop", last_assistant_message="done")
        self.assertTrue(run_event(stop, self.config, UnknownEvaluator()))
        self.verify("valid")
        self.assertEqual(run_event(stop, self.config, UnknownEvaluator()), {})
        (self.root / "code.py").write_text("changed = True")
        self.assertTrue(run_event(stop, self.config, UnknownEvaluator()))
