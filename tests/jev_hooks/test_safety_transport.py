"""Inspect actual SDK HTTP bodies using local MockTransport only."""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from jev_hooks.evaluator import JevEvaluator
from jev_hooks.questions import QUESTIONS
from jev_hooks.semantic_eval import main as semantic_main


@unittest.skipUnless(importlib.util.find_spec("typesafe_sdk"), "optional SDK not installed")
class SafetyTransportTests(unittest.TestCase):
    def test_evaluator_and_semantic_cli_have_same_safe_http_boundary(self):
        import httpx2
        from typesafe_sdk import AsyncTypeSafeClient

        requests = []
        headers = []
        canaries = ["canary-dictionary-name", "declared-canary", "token-canary", "file-canary",
                    "header-canary", "bearer-canary", "prompt-canary", "private-canary",
                    "key-value-canary", "bearer-key-canary", "key-form-value-canary"]
        evidence = {"user_request": ["declared-canary"],
                    "public_messages": ["token=token-canary", "Bearer bearer-canary"],
                    "last_assistant_message": "canary-dictionary-name",
                    "current_tool_input": {"canary-dictionary-name": "ordinary",
                                           "nested": [{"headers": {"Authorization": "header-canary"},
                                                       "prefix-canary-dictionary-name": "key-value-canary",
                                                       "Bearer bearer-key-canary": "key-form-value-canary"}]},
                    "private_reasoning": "private-canary",
                    "skill_context": {"applicability": "prompt-canary",
                                      "selector": {"input": {"command": "git push --token=declared-canary"}}},
                    "current_turn_tool_ids": ["read"],
                    "tool_calls": {"read": {"name": "Read", "input": {"file_path": "/x/.env"}}},
                    "tool_results": {"read": {"content": "file-canary"}}}
        config = {"evaluator": "jev", "retries": 0,
                  "secret_env_vars": ["APP_SECRET", "PROMPT_SECRET"]}

        def handler(request):
            payload = json.loads(request.content)
            requests.append(payload)
            headers.append(request.headers["Authorization"])
            answers = {key: {"type": "choice", "choice": "unknown", "confidence": 1.,
                             "probabilities": {"yes": 0., "no": 0., "unknown": 1.}}
                       for key in payload["questions"]}
            return httpx2.Response(200, json={"model": "jev-1.13.0", "answers": answers,
                                             "usage": {"input_tokens": 1, "output_tokens": 1}})

        def factory(**kwargs):
            return AsyncTypeSafeClient(**kwargs, transport=httpx2.MockTransport(handler))

        identifier = "r1_waiting_for_answer"
        with patch("typesafe_sdk.AsyncTypeSafeClient", factory):
            with patch.dict(os.environ, {"TYPESAFE_API_KEY": "canary-dictionary-name", "APP_SECRET": "declared-canary",
                                         "PROMPT_SECRET": "prompt-canary"}, clear=True):
                with patch.dict(QUESTIONS, {identifier: QUESTIONS[identifier] + " prompt-canary"}):
                    result = JevEvaluator(config).evaluate(evidence, [identifier])
                    self.assertIsNone(result[identifier]["value"])
                    with tempfile.TemporaryDirectory() as directory:
                        path = Path(directory)
                        (path / "config.json").write_text(json.dumps(config))
                        (path / "corpus.jsonl").write_text(json.dumps({"id": "safe", "question": identifier,
                                                           "expected": None, "evidence": evidence}) + "\n")
                        argv = ["semantic_eval", "--config", str(path / "config.json"),
                                "--corpus", str(path / "corpus.jsonl")]
                        output = io.StringIO()
                        with patch("sys.argv", argv), contextlib.redirect_stdout(output):
                            semantic_main()
                        self.assertNotIn("canary", output.getvalue())
        self.assertEqual(len(requests), 2)
        for payload in requests:
            for canary in canaries:
                self.assertNotIn(canary, json.dumps(payload))
        self.assertEqual(headers, ["Bearer canary-dictionary-name"] * 2)
        self.assertEqual(requests[0]["state"], requests[1]["state"])
