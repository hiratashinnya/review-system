"""Concurrent real processes preserve replay and state transaction integrity."""
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from jev_hooks.config import load_config


class ParallelTests(unittest.TestCase):
    def test_parallel_duplicate_commits_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = dict(load_config(), state_dir=tmp, mode="enforce", mock_answers={
                "r1_waiting_for_answer": True, "r1_question_already_asked": False})
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(config))
            event = json.dumps({"hook_event_name": "Stop", "session_id": "parallel",
                                "last_assistant_message": "waiting"})
            processes = [subprocess.Popen([sys.executable, "-m", "jev_hooks", "--config", str(path)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(4)]
            for process in processes:
                process.stdin.write(event)
                process.stdin.close()
                process.stdin = None
            for process in processes:
                stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(json.loads(stdout)["decision"], "block", stderr)
            with sqlite3.connect(Path(tmp) / "state.sqlite3") as db:
                state = json.loads(db.execute("SELECT data FROM sessions").fetchone()[0])
                self.assertEqual(state["blocks"], {"R1": 1})
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
