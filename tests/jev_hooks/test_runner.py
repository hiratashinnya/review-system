"""Persistence, fault separation, replay, cancellation and stdout integration."""
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from jev_hooks.config import load_config
from jev_hooks.runner import run_event


class Evaluator:
    def __init__(self, fail=False):
        self.fail = fail

    def evaluate(self, evidence, question_ids):
        if self.fail:
            raise RuntimeError("secret SDK credential")
        return {key: {"value": key == "r1_waiting_for_answer", "confidence": 1}
                for key in question_ids}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = load_config()
        self.config.update(mode="enforce", state_dir=self.tmp.name)
        self.event = {"session_id": "session", "hook_event_name": "Stop", "cwd": self.tmp.name}

    def test_replay_persistence_and_budget(self):
        self.event["event_id"] = "first"
        first = run_event(self.event, self.config, Evaluator())
        self.assertEqual(first["decision"], "block")
        self.assertEqual(run_event(self.event, self.config, Evaluator()), first)
        self.event["event_id"] = "second"
        self.assertTrue(run_event(self.event, self.config, Evaluator()))
        self.event["event_id"] = "third"
        self.assertEqual(run_event(self.event, self.config, Evaluator()), {})
        self.event["cwd"] = "/tmp/other-project"
        self.assertTrue(run_event(self.event, self.config, Evaluator()))

    def test_api_failure_and_no_raw_content_persisted(self):
        self.event.update(last_assistant_message="secret-token", tool_input={"key": "secret-token"})
        self.assertEqual(run_event(self.event, self.config, Evaluator(True)), {})
        data = (Path(self.tmp.name) / "state.sqlite3").read_bytes()
        self.assertNotIn(b"secret-token", data)
        self.assertNotIn(b"secret SDK credential", data)

    def test_question_cancellation_stops_r1_loop(self):
        event = dict(self.event, hook_event_name="PostToolUseFailure", tool_name="AskUserQuestion",
                     tool_use_id="cancel", error="user cancelled")
        self.assertEqual(run_event(event, self.config, Evaluator()), {})
        self.assertEqual(run_event(self.event, self.config, Evaluator()), {})

    def test_invalid_input_stdout_json_only(self):
        result = subprocess.run([sys.executable, "-m", "jev_hooks"], input="bad json",
                                text=True, capture_output=True)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertEqual(result.returncode, 0)

    def test_post_success_cancel_without_transcript(self):
        event = dict(self.event, hook_event_name="PostToolUse", tool_name="AskUserQuestion",
                     tool_use_id="cancel-success", tool_response={"cancelled": True})
        self.assertEqual(run_event(event, self.config, Evaluator()), {})
        self.assertEqual(run_event(self.event, self.config, Evaluator()), {})
