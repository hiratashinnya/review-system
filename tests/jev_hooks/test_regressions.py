"""Review regressions: compaction, future speech, replay and real-shaped results."""
import json
import tempfile
import unittest
from pathlib import Path
from jev_hooks.config import load_config
from jev_hooks.evidence import collect
from jev_hooks.fingerprints import successful
from jev_hooks.runner import run_event
from jev_hooks.evaluator import MockEvaluator


class RegressionTests(unittest.TestCase):
    def test_compaction_and_same_block_future_speech(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history"
            records = [{"type": "system", "subtype": "compact_boundary"},
                {"message": {"role": "user", "content": "pick a color"}},
                {"message": {"role": "assistant", "content": [
                    {"type": "tool_use", "id": "q", "name": "AskUserQuestion", "input": {}},
                    {"type": "text", "text": "future explanation"}]}}]
            path.write_text("\n".join(map(json.dumps, records)))
            evidence = collect({"hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion",
                "tool_use_id": "q", "transcript_path": str(path)},
                {"calls": {}, "results": {}, "blocks": {}}, load_config())
            self.assertEqual(evidence["public_messages"], [])
            self.assertFalse(evidence["history_complete"])
            self.assertEqual(evidence["user_request"], ["pick a color"])

    def test_official_bash_shape_requires_machine_receipt(self):
        result = {"content": {"stdout": "tests passed", "stderr": "", "interrupted": False}}
        self.assertFalse(successful(result))
        result["content"]["stdout"] += '\nJEV_VERIFICATION_RECEIPT={"exit_code":0}'
        self.assertTrue(successful(result))
        result["content"]["interrupted"] = True
        self.assertFalse(successful(result))

    def test_stop_without_event_id_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = dict(load_config(), state_dir=tmp, mode="enforce")
            evaluator = MockEvaluator({"r1_waiting_for_answer": True, "r1_question_already_asked": False})
            event = {"session_id": "s", "hook_event_name": "Stop", "last_assistant_message": "answer?"}
            for _ in range(5):
                self.assertEqual(run_event(event, config, evaluator)["decision"], "block")
            event["stop_hook_active"] = True
            self.assertEqual(run_event(event, config, evaluator), {})
