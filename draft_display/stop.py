"""SubagentStop（matcher ``gh-create-issue``）: handoff 本文をチャットへ表示し、主文脈へ状況を伝える。

``systemMessage`` はモデルを経由せずオーナーへ届く。同じ出力の ``hookSpecificOutput.additionalContext``
で主文脈へ「表示済み・再掲不要」または「表示できなかった・対処」を伝える（失敗を黙らせない）。
停止は決してブロックしない（可視化専用・fail-open）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TextIO

from . import handoff
from .payload import load_payload, string_field


def _evidence(stderr: TextIO, **fields: Any) -> None:
    stderr.write(
        json.dumps({"hook": "draft-display-stop", **fields}, ensure_ascii=False, sort_keys=True) + "\n"
    )


DISPLAYED_CONTEXT = (
    "[gh-create-issue] サブエージェントの成果物 {rel}（draft 本文・予定値 preview・完了報告）は"
    " SubagentStop フックがオーナーのチャットへ表示済み。**本文・preview・完了報告を再掲・要約・言い換えしない**。"
    "このファイルを Read もしない。オーナー判断が必要なら、最終応答の QUESTIONS だけを"
    " AskUserQuestion で短く尋ね、次の dispatch へ回答を渡す。"
)
TRUNCATED_CONTEXT = " 表示は {limit} バイトで切り詰めた。残りが必要なときだけ {rel} を Read する。"
FAILED_CONTEXT = (
    "[gh-create-issue] サブエージェントの成果物をチャットへ自動表示できなかった（{reason}）。"
    "オーナーには表示されていないので、{action}"
)
_FAILURES = {
    "NO_HANDOFF_LINE": (
        "最終応答に規定形の HANDOFF: 行が無い",
        "サブエージェントの不具合として最終応答の SUMMARY 相当をオーナーへ報告し、"
        "推測で GitHub を変更しない。",
    ),
    "HANDOFF_UNREADABLE": (
        "HANDOFF: 行が指すファイルを安全に読めない",
        "指されたパスが tmp/_handoff/gh-create-issue--<key>.md の通常ファイルとして存在するか確認し、"
        "存在すれば Read して本文をそのままオーナーへ提示する（要約で代替しない）。",
    ),
}


def _emit(stdout: TextIO, *, context: str, system_message: str | None = None) -> None:
    output: dict[str, Any] = {
        "hookSpecificOutput": {"hookEventName": "SubagentStop", "additionalContext": context}
    }
    if system_message is not None:
        output["systemMessage"] = system_message
    json.dump(output, stdout, ensure_ascii=False)
    stdout.write("\n")


def _fail(stdout: TextIO, stderr: TextIO, reason: str, **fields: Any) -> int:
    label, action = _FAILURES[reason]
    _emit(stdout, context=FAILED_CONTEXT.format(reason=label, action=action))
    _evidence(stderr, result="skip", reason=reason, **fields)
    return 0


def run(*, stdin: TextIO, stdout: TextIO, stderr: TextIO, project_root: Path) -> int:
    payload = load_payload(stdin)
    if payload is None:
        return 0
    if string_field(payload, "agent_type", "subagent_type") != handoff.AGENT_TYPE:
        return 0
    rel = handoff.find_handoff_rel(string_field(payload, "last_assistant_message") or "")
    if rel is None:
        return _fail(stdout, stderr, "NO_HANDOFF_LINE")
    path = handoff.resolve_handoff(project_root, rel)
    loaded = handoff.read_for_display(path) if path is not None else None
    if path is None or loaded is None:
        return _fail(stdout, stderr, "HANDOFF_UNREADABLE", handoff=rel)
    body, truncated = loaded
    message = f"[gh-create-issue サブエージェントの成果物: {rel}]\n\n{body}"
    context = DISPLAYED_CONTEXT.format(rel=rel)
    if truncated:
        message += f"\n\n…（{handoff.MAX_DISPLAY_BYTES} バイトで切詰め。全文は {rel}）"
        context += TRUNCATED_CONTEXT.format(limit=handoff.MAX_DISPLAY_BYTES, rel=rel)
    _emit(stdout, context=context, system_message=message)
    _evidence(stderr, result="displayed", handoff=rel, truncated=truncated)
    return 0
