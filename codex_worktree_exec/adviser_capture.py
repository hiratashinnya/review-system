"""相談回答を担当成果物から参照できる値として返す。review finding/ledgerは書かない。"""
from .adviser_request import request_digest
from .adviser_budget import seconds, validate_budget

ORIGIN_FIELDS = {"run_id", "issue", "target_key", "caller_role", "phase", "work_unit",
                 "snapshot_oid", "input_refs", "model"}


class AdviceCaptureError(ValueError):
    """失敗/部分出力の既存runへの記録材料を保持する。"""
    def __init__(self, message, record):
        super().__init__(message)
        self.record = record


def capture_advice(request: dict, answer: dict, metrics: dict) -> dict:
    """trusted dispatcherの要求全体とtrusted meterを照合し、採否未決で返す。"""
    origin = {key: request[key] for key in ORIGIN_FIELDS}
    record = {**origin, "request_digest": request_digest(request), "metrics": metrics,
              "budget": {key: value for key, value in request.items()
                         if key.startswith(("max_", "reserve_")) or key.endswith("_used")
                         or key == "cost_used_microusd"}, "status": "failed"}
    try:
        validate_budget(request)
        _validate_answer(request, answer, metrics, record["request_digest"])
    except (ValueError, KeyError, TypeError) as error:
        record.update(failure_reason=str(error),
                      output_status=answer.get("status", "missing") if isinstance(answer, dict) else "invalid")
        raise AdviceCaptureError(str(error), record) from None
    return {**record, "status": "complete", "answer": answer["answer"],
            "calls_used": request["calls_used"] + 1,
            "seconds_used": request["seconds_used"] + metrics["elapsed_seconds"],
            "tokens_used": request["tokens_used"] + metrics["tokens"],
            "cost_used_microusd": request["cost_used_microusd"] + metrics["cost_microusd"],
            "adoption": "pending", "adoption_reason": "", "verification_result": "pending"}


def _validate_answer(request, answer, metrics, digest):
    expected = ORIGIN_FIELDS | {"request_digest", "status", "answer"}
    if not isinstance(answer, dict) or set(answer) != expected:
        raise ValueError("partial adviser output")
    if (any(answer[key] != request[key] for key in ORIGIN_FIELDS)
            or answer["request_digest"] != digest or answer["status"] != "complete"
            or not isinstance(answer["answer"], str) or not answer["answer"].strip()):
        raise ValueError("adviser response mismatch/failure")
    if not isinstance(metrics, dict) or set(metrics) != {"status", "tokens", "cost_microusd", "elapsed_seconds"}:
        raise ValueError("trusted metering required")
    if metrics["status"] != "success":
        raise ValueError("consultation failed")
    seconds(metrics["elapsed_seconds"])
    for key in ("tokens", "cost_microusd"):
        if type(metrics[key]) is not int or metrics[key] < 0:
            raise ValueError("invalid usage metrics")
    for metric, used, reserve, maximum in (
            ("tokens", "tokens_used", "reserve_tokens", "max_tokens"),
            ("cost_microusd", "cost_used_microusd", "reserve_cost_microusd", "max_cost_microusd"),
            ("elapsed_seconds", "seconds_used", "reserve_seconds", "max_seconds")):
        if metrics[metric] > request[reserve] or request[used] + metrics[metric] >= request[maximum]:
            raise ValueError("adviser budget reached")
