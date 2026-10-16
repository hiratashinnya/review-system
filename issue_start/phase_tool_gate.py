"""read-only工程の直接編集ツールを拒否するPreToolUse入口。"""
import json
import sys
from .gated_roles import READ_ONLY_ROLES


def decision(payload):
    if payload.get("agent_type") in READ_ONLY_ROLES:
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": "read-only工程では直接編集できません。担当authorへ戻してください。",
        }}
    return None


def main():
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        result = decision(payload)
    except (ValueError, TypeError):
        result = {"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": "工程ロールを検証できません。",
        }}
    if result:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
