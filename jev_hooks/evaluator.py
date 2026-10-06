"""Jev とオフライン判定器の共通境界。例外本文・入力証拠は記録しない。"""

import asyncio
import math

from .evaluator_transport import bounded_request
from .configuration_failure import ConfigurationFault
from .questions import question_specs


def unknown(fault: str = "insufficient_evidence") -> dict:
    return {"value": None, "confidence": 0.0, "fault": fault}


def normalize_answer(answer, threshold: float) -> dict:
    if not isinstance(answer, dict):
        answer = {"choice": getattr(answer, "choice", None),
                  "confidence": getattr(answer, "confidence", None)}
    choice, confidence = answer.get("choice"), answer.get("confidence")
    if (choice not in ("yes", "no", "unknown") or type(confidence) not in (int, float)
            or not math.isfinite(confidence) or not 0 <= confidence <= 1):
        return unknown("invalid_response")
    if choice == "unknown" or confidence < threshold:
        return {"value": None, "confidence": confidence, "fault": "uncertain"}
    return {"value": choice == "yes", "confidence": confidence}


class JevEvaluator:
    """単一リクエスト中の個別 Choice をコード側で正規化する。"""

    def __init__(self, config: dict):
        self.config = config
        self.last_model = config.get("model", "jev-1.13.0")

    def evaluate(self, evidence: dict, question_ids: list[str]) -> dict:
        if not question_ids:
            return {}
        try:
            response = asyncio.run(bounded_request(
                self.config, evidence, question_specs(question_ids)))
            self.last_model = response.model
            threshold = float(self.config.get("confidence_threshold", .85))
            if not math.isfinite(threshold) or not 0 <= threshold <= 1:
                raise ValueError("invalid_threshold")
            return {key: normalize_answer(response.answers.get(key), threshold)
                    for key in question_ids}
        except ConfigurationFault:
            raise
        except Exception as error:
            fault = "timeout" if isinstance(error, TimeoutError) else "evaluation_error"
            return {key: unknown(fault) for key in question_ids}


class MockEvaluator:
    """意味精度を主張せず、指定された結果で制御ロジックを検証する。"""

    def __init__(self, answers: dict | None = None):
        self.answers = answers or {}
        self.last_model = "mock"

    def evaluate(self, evidence: dict, question_ids: list[str]) -> dict:
        results = {}
        for key in question_ids:
            answer = self.answers.get(key)
            if isinstance(answer, dict):
                results[key] = dict(answer)
            elif type(answer) is bool:
                results[key] = {"value": answer, "confidence": 1.0}
            else:
                results[key] = unknown()
        return results


def make_evaluator(config: dict):
    if config.get("evaluator", "mock") == "mock":
        return MockEvaluator(config.get("mock_answers", {}))
    if config.get("evaluator") == "jev":
        return JevEvaluator(config)
    raise ValueError("unsupported_evaluator")
