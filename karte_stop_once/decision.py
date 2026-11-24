"""Evaluate hard-stop guidance without changing Karte verdict or escalation."""
import hashlib
import json


def evaluate(status: dict) -> dict | None:
    """Use independent existing predicates. Do not treat harmful-open alone as STOP."""
    if not isinstance(status, dict) or type(status.get("issue")) is not int:
        raise ValueError("invalid status payload")
    reasons = []
    undecided = status.get("undecided_disposition", [])
    if undecided:
        reasons.append(("UNDECIDED_REAL", sorted(undecided)))
    if status.get("verdict") == "no-harm-only":
        reasons.append(("NO_HARM_ONLY", sorted(status.get("blocking_findings", []))))
    stalled = status.get("stalled_findings", [])
    if stalled:
        reasons.append(("STALL", sorted(stalled)))
    saturated = status.get("saturated_groups", [])
    if saturated:
        reasons.append(("SATURATION", saturated))
    if status.get("escalate") and not (stalled or saturated):
        raise ValueError("inconsistent escalate")
    if not reasons:
        return None
    evidence = {"issue": status["issue"], "reasons": reasons}
    digest = hashlib.sha256(json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {"issue": status["issue"], "reasons": reasons, "digest": digest}


def instruction(event: dict) -> str:
    reasons = "; ".join(f"{code}: {', '.join(map(str, items)) or '(詳細なし)'}"
                        for code, items in event["reasons"])
    return (
        "【強制STOP】\n"
        f"Issue #{event['issue']} でオーナー判断が必要です。根拠: {reasons}\n"
        "このまま是正・再レビュー・実装・push・PR操作を続けることは工程違反です。"
        "技術的にツールが動くことは、続行の承認ではありません。\n"
        "直ちに作業を停止し、停止理由・選択肢・推奨・判断で決めてほしい事項をオーナーに示してください。"
        "拒否されたツールをそのまま再実行しないでください。"
        "AskUserQuestionで判断を仰ぐことは許可されています。"
        "オーナーの決定を得るまでは自己判断で次工程へ進まないでください。"
        "※同じSTOP事象の機械denyは1回だけです。2回目以降の許可は承認ではありません。"
    )
