"""任意依存導入時の公式SDK互換性試験。通信はMockTransport内に閉じる。"""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

from jev_hooks.evaluator import JevEvaluator
from jev_hooks.questions import QUESTIONS


@unittest.skipUnless(importlib.util.find_spec("typesafe_sdk"), "optional SDK not installed")
class OfficialSdkTransportTests(unittest.TestCase):
    def test_official_sdk_serializes_questions_and_retries_locally(self):
        import httpx2
        from typesafe_sdk import AsyncTypeSafeClient

        requests = []

        def handler(request):
            payload = json.loads(request.content)
            requests.append(payload)
            self.assertEqual(request.url.path, "/v1/systemone")
            self.assertEqual(payload["model"], "jev-1.13.0")
            if len(requests) == 1:
                return httpx2.Response(529, json={"error": "overloaded"})
            answers = {key: {"type": "choice", "choice": "yes", "confidence": 1.0,
                             "probabilities": {"yes": 1., "no": 0., "unknown": 0.}}
                       for key in payload["questions"]}
            return httpx2.Response(200, json={"model": "jev-1.13.0", "answers": answers,
                                             "usage": {"input_tokens": 1, "output_tokens": 1}})

        def factory(**kwargs):
            return AsyncTypeSafeClient(**kwargs, transport=httpx2.MockTransport(handler))

        with patch("typesafe_sdk.AsyncTypeSafeClient", factory):
            with patch.dict(os.environ, {"TYPESAFE_API_KEY": "fixture-not-a-key"}):
                results = JevEvaluator({"retries": 1}).evaluate({}, list(QUESTIONS))
        self.assertEqual(len(requests), 2)
        self.assertTrue(all(result["value"] is True for result in results.values()))
        self.assertTrue(all(spec["type"] == "choice"
                            for spec in requests[0]["questions"].values()))
