"""相談回答を担当成果物から参照できる値として返す。review finding/ledgerは書かない。"""
from .adviser_request import request_digest


def capture_advice(request: dict, answer: dict, metrics: dict) -> dict:
    """成功・完全出力・trusted meterの予算を確認し、採否未決の回答を返す。"""
    digest = request_digest(request)
    expected = {"request_digest", "run_id", "model", "status", "answer"}
    if not isinstance(answer, dict) or set(answer) != expected:
        raise ValueError("partial adviser output")
    if (answer["request_digest"] != digest or answer["run_id"] != request["run_id"]
            or answer["model"] != request["model"] or answer["status"] != "complete"
            or not isinstance(answer["answer"], str) or not answer["answer"].strip()):
        raise ValueError("adviser response mismatch/failure")
    if not isinstance(metrics, dict) or set(metrics) != {"status", "tokens", "cost_microusd"}:
        raise ValueError("trusted metering required")
    if metrics["status"] != "success":
        raise ValueError("consultation failed")
    for key in ("tokens", "cost_microusd"):
        if type(metrics[key]) is not int or metrics[key] < 0:
            raise ValueError("invalid usage metrics")
    if (metrics["tokens"] > request["reserve_tokens"]
            or metrics["cost_microusd"] > request["reserve_cost_microusd"]):
        raise ValueError("adviser budget reached")
    if (request["tokens_used"] + metrics["tokens"] >= request["max_tokens"]
            or request["cost_used_microusd"] + metrics["cost_microusd"] >= request["max_cost_microusd"]):
        raise ValueError("adviser budget reached")
    return {"request_digest": digest, "run_id": request["run_id"], "model": request["model"],
            "answer": answer["answer"], "input_refs": request["input_refs"], "metrics": metrics,
            "adoption": "pending", "adoption_reason": "", "verification_result": "pending"}
