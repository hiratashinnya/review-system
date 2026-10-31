"""read-only工程の直接編集ツールを拒否するPreToolUse入口。

例外は `pr-reviewer` の Write だけで、`tmp/_handoff/pr-reviewer--*.md` への書込みに限る（Issue #375）。
"""
import json
import os
import sys
from .gated_roles import READ_ONLY_ROLES

HANDOFF_WRITER = "pr-reviewer"


def _deny(reason):
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}


def _handoff_write_allowed(payload):
    """Write の対象が reviewer handoff の規則に合うか（検査不能は不許可＝fail-close）。"""
    try:
        from karte.handoff_path import resolve_reviewer_handoff
        from karte.paths import main_worktree_root
        file_path = payload["tool_input"]["file_path"]
        root = main_worktree_root(os.environ.get("CLAUDE_PROJECT_DIR") or payload["cwd"])
        resolve_reviewer_handoff(file_path, root)
    except Exception:
        return False
    return True


def decision(payload):
    role = payload.get("agent_type")
    if role not in READ_ONLY_ROLES:
        return None
    if role == HANDOFF_WRITER and payload.get("tool_name") == "Write":
        if _handoff_write_allowed(payload):
            return None
        return _deny("pr-reviewer が書けるのは tmp/_handoff/pr-reviewer--<key>.md だけです。")
    return _deny("read-only工程では直接編集できません。担当authorへ戻してください。")


def main():
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        result = decision(payload)
    except (ValueError, TypeError):
        result = _deny("工程ロールを検証できません。")
    if result:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
