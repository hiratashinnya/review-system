"""Realistic JSONL evidence boundaries and delayed writes."""
import json
import tempfile
import unittest
from pathlib import Path
from jev_hooks.config import load_config
from jev_hooks.evidence import collect


class EvidenceTests(unittest.TestCase):
    def test_public_only_before_current_call_and_stop_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.jsonl"
            records = [{"message": {"role": "assistant", "content": [
                {"type": "thinking", "thinking": "secret thought"},
                {"type": "tool_use", "id": "ask", "name": "AskUserQuestion", "input": {}}]}},
                {"message": {"role": "assistant", "content": [{"type": "text", "text": "too late"}]}}]
            path.write_text("\n".join(map(json.dumps, records)))
            state = {"calls": {}, "results": {}, "blocks": {}}
            event = {"hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion",
                     "tool_use_id": "ask", "transcript_path": str(path)}
            evidence = collect(event, state, load_config())
            self.assertEqual(evidence["public_messages"], [])
            self.assertTrue(evidence["history_complete"])
            path.write_text('{"partial":')
            event.update(hook_event_name="Stop", last_assistant_message="authoritative")
            evidence = collect(event, state, load_config())
            self.assertEqual(evidence["public_messages"], ["authoritative"])
            self.assertFalse(evidence["history_complete"])

    def test_new_user_turn_resets_cancellation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.jsonl"
            path.write_text(json.dumps({"message": {"role": "user", "content": "new task"}}))
            state = {"calls": {}, "results": {}, "blocks": {"R1": 2}, "question_cancelled": True}
            collect({"hook_event_name": "Stop", "transcript_path": str(path)}, state, load_config())
            self.assertFalse(state["question_cancelled"])
            self.assertEqual(state["blocks"], {})
