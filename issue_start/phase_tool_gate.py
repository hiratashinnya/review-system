"""read-only工程の直接編集ツールを拒否するPreToolUse入口。

例外は `pr-reviewer` の Write だけで、`tmp/_handoff/pr-reviewer--*.md` への書込みに限る（Issue #375）。
拒否の理由は「パスが不正」と「ゲート自体の故障」を区別して返す（故障は stderr にも原因を出す）。
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


def _gate_failure(exc):
    print(f"phase_tool_gate: ゲート自体が動かない（{type(exc).__name__}: {exc}）", file=sys.stderr)
    return _deny(
        f"ゲート自体の故障のため pr-reviewer の Write を拒否しました（{type(exc).__name__}: {exc}）。"
        "パスの問題ではありません。ハーネスの異常として主文脈へ報告してください。"
    )


def _handoff_write_denial(payload):
    """handoff への Write を許すなら ``None``。許さないなら拒否の応答（パス不正とゲート故障を区別）。"""
    try:
        from karte.handoff_path import resolve_reviewer_handoff
        from karte.path_errors import KartePathError
        from karte.paths import main_worktree_root
    except Exception as exc:  # noqa: BLE001 — import の失敗はすべてゲートの故障として扱う
        return _gate_failure(exc)
    try:
        file_path = payload["tool_input"]["file_path"]
    except (KeyError, TypeError):
        return _deny("Write の入力に tool_input.file_path がありません（パスを検証できないため拒否）。")
    try:
        root = main_worktree_root(os.environ.get("CLAUDE_PROJECT_DIR") or payload["cwd"])
        resolve_reviewer_handoff(file_path, root)
    except KartePathError as exc:
        return _deny(f"パス不正: pr-reviewer が書けるのは tmp/_handoff/pr-reviewer--<key>.md だけです（{exc}）。")
    except Exception as exc:  # noqa: BLE001 — git・ファイル系の失敗などはゲートの故障として扱う
        return _gate_failure(exc)
    return None


def decision(payload):
    role = payload.get("agent_type")
    if role not in READ_ONLY_ROLES:
        return None
    if role == HANDOFF_WRITER and payload.get("tool_name") == "Write":
        return _handoff_write_denial(payload)
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
