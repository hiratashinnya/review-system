"""API不要の評価境界テスト（意味判定精度のテストではない）。"""

import asyncio
import contextlib
import io
import types
import unittest
from unittest.mock import AsyncMock, patch

from jev_hooks.evaluator import JevEvaluator, MockEvaluator, make_evaluator, normalize_answer
from jev_hooks.evaluator_transport import bounded_request, request_answers
from jev_hooks.questions import QUESTIONS, question_specs


class JevEvaluatorTests(unittest.TestCase):
    def test_mock_has_independent_answers_and_unknown(self):
        result = MockEvaluator({"a": True, "b": False}).evaluate({}, ["a", "b", "c"])
        self.assertTrue(result["a"]["value"])
        self.assertFalse(result["b"]["value"])
        self.assertIsNone(result["c"]["value"])
        self.assertIsInstance(make_evaluator({}), MockEvaluator)

    def test_response_confidence_and_unknown_are_separate(self):
        for choice, confidence, expected in [
            ("yes", .95, True), ("no", .95, False), ("unknown", 1, None),
            ("yes", .8, None), ("no", .8, None), ("yes", float("nan"), None),
            ("yes", 1.1, None), ("yes", True, None), ("invalid", 1, None),
        ]:
            with self.subTest(choice=choice, confidence=confidence):
                self.assertIs(normalize_answer({"choice": choice, "confidence": confidence},
                                               .85)["value"], expected)

    def test_official_response_mapping_and_actual_model(self):
        response = types.SimpleNamespace(model="jev-1.13.0", answers={
            "r1_waiting_for_answer": types.SimpleNamespace(choice="yes", confidence=.95)})
        with patch("jev_hooks.evaluator.bounded_request", AsyncMock(return_value=response)) as call:
            evaluator = JevEvaluator({"model": "jev-latest"})
            result = evaluator.evaluate({"public_messages": []}, list(QUESTIONS))
        self.assertTrue(result["r1_waiting_for_answer"]["value"])
        self.assertIsNone(result["r2_researchable"]["value"])
        self.assertEqual(evaluator.last_model, "jev-1.13.0")
        self.assertEqual(set(call.call_args.args[2]), set(QUESTIONS))

    def test_api_fault_does_not_leak_exception_or_print(self):
        for error in [RuntimeError("secret-key"), TimeoutError("secret-key")]:
            stream = io.StringIO()
            with patch("jev_hooks.evaluator.bounded_request", AsyncMock(side_effect=error)):
                with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                    result = JevEvaluator({}).evaluate({}, list(QUESTIONS))
            self.assertTrue(all(value["value"] is None for value in result.values()))
            self.assertNotIn("secret-key", str(result))
            self.assertEqual(stream.getvalue(), "")

    def test_total_deadline_cancels_request(self):
        async def slow(*args):
            await asyncio.sleep(1)
        with patch("jev_hooks.evaluator_transport.request_answers", slow):
            with self.assertRaises(TimeoutError):
                asyncio.run(bounded_request({"timeout_seconds": .001}, {}, {}))

    def test_sdk_options_without_sdk_or_network(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        fake = types.SimpleNamespace(AsyncTypeSafeClient=lambda **kw: client,
                                     RetryPolicy=lambda **kw: kw)
        with patch.dict("sys.modules", {"typesafe_sdk": fake}):
            with patch.dict("os.environ", {"CUSTOM_JEV_KEY": "fixture-not-a-key"}):
                asyncio.run(request_answers({"api_key_env": "CUSTOM_JEV_KEY"}, {}, {}))
        client.system_one.assert_awaited_once_with(state={}, questions={})

    def test_questions_keep_required_exclusions_and_evidence_boundaries(self):
        specs = question_specs(list(QUESTIONS))
        self.assertTrue(all(set(item["criteria"]) == {"yes", "no", "unknown"}
                            for item in specs.values()))
        for phrase in ("rhetorical", "quoted", "optional suggestions"):
            self.assertIn(phrase, QUESTIONS["r1_waiting_for_answer"])
        self.assertIn("merely invoking", QUESTIONS["r2_research_relevant"])
        self.assertIn("public_messages", QUESTIONS["r3_explanation_sufficient"])


if __name__ == "__main__":
    unittest.main()
