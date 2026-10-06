"""Code composes independent semantic answers and bounds corrective loops."""
from .evidence import question_cancelled

RULE_VERSION = "1.1"

REASONS = {
    "R1": "必要な調査と背景説明を公開チャットで済ませてから、標準の AskUserQuestion を呼んでください。",
    "R2": "許可済み・利用可能な関連調査手段で事実を調べ、結果を確認してください。結論が出なければその限界を説明してください。",
    "R3": "質問前の公開チャットに背景・確認済み事実・未確定点・選択肢の違いと必要な推奨理由を簡潔に説明してください。",
    "R4": "Skill の必須前提を完了してください: ",
}


def questions(event, evidence):
    kind = event["hook_event_name"]
    if kind == "Stop":
        return ["r1_waiting_for_answer", "r1_question_already_asked", "r2_researchable", "r2_research_available", "r2_research_relevant"]
    if kind == "PreToolUse" and event.get("tool_name") == "AskUserQuestion":
        return ["r2_researchable", "r2_research_available", "r2_research_relevant",
                "r3_explanation_sufficient"]
    return []


def violations(event, evidence, answers, missing, config):
    def answer(identifier, expected):
        result = answers.get(identifier, {})
        return result.get("value") is expected and not result.get("fault") and (
            result.get("confidence", 0) >= config["confidence_threshold"])
    found = {"R4": REASONS["R4"] + ", ".join(missing)} if missing else {}
    cancelled = question_cancelled(evidence)
    stop = event["hook_event_name"] == "Stop"
    asking = event.get("tool_name") == "AskUserQuestion"
    if stop and not cancelled and config["question_tool_available"] and all((
            answer("r1_waiting_for_answer", True), answer("r1_question_already_asked", False))):
        found["R1"] = REASONS["R1"]
    if (stop or asking) and evidence["research_tools"] and all((
            answer("r2_researchable", True), answer("r2_research_available", True),
            answer("r2_research_relevant", False))):
        found["R2"] = REASONS["R2"]
    if asking and not cancelled and evidence["history_complete"] and answer("r3_explanation_sufficient", False):
        found["R3"] = REASONS["R3"]
    return found


def decide(event, found, state, config):
    state["denied_rules"] = []
    if event["hook_event_name"] not in {"Stop", "PreToolUse"}:
        return {}
    if event.get("stop_hook_active"):
        found = {key: value for key, value in found.items() if key == "R4"}
    blocked = []
    for rule, reason in found.items():
        count = state["blocks"].get(rule, 0)
        if rule == "R4" or count < config["max_blocks_per_rule"]:
            blocked.append(reason)
            if config["mode"] == "enforce":
                state["denied_rules"].append(rule)
            state["blocks"][rule] = count + 1
    if not blocked or config["mode"] == "shadow":
        return {}
    reason = "\n".join(blocked)
    if event["hook_event_name"] == "Stop":
        return {"decision": "block", "reason": reason}
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": "deny", "permissionDecisionReason": reason}}
