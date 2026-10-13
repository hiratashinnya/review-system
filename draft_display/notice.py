"""PostToolUse（matcher ``Task|Agent``）: 表示済みの成果物を再掲しないよう主文脈へ注入する。

``SubagentStop`` 側が書いたレシートで「フックが実際に表示した」と確認できたときだけ
「再掲不要」を伝える。レシートが無ければ（フック失敗）逆に本文を Read して提示させる。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, TextIO

from . import handoff
from .payload import load_payload

TOOL_NAMES = frozenset({"Task", "Agent"})

DISPLAYED_NOTICE = (
    "[gh-create-issue] サブエージェントの成果物 {rel}（draft 本文・予定値 preview・完了報告）は"
    " SubagentStop フックがオーナーのチャットへ表示済み。**本文・preview・完了報告を再掲・要約・言い換えしない**。"
    "このファイルを Read もしない。オーナー判断が必要なら、サブエージェント最終応答の QUESTIONS だけを"
    " AskUserQuestion で短く尋ね、次の dispatch へ回答を渡す。"
)
NOT_DISPLAYED_NOTICE = (
    "[gh-create-issue] サブエージェントの成果物 {rel} の自動表示を確認できなかった（フック失敗の恐れ）。"
    "{rel} を Read し、本文をオーナーへ提示してから次へ進む。"
)


def _evidence(stderr: TextIO, **fields: Any) -> None:
    stderr.write(
        json.dumps({"hook": "draft-display-notice", **fields}, ensure_ascii=False, sort_keys=True) + "\n"
    )


def run(*, stdin: TextIO, stdout: TextIO, stderr: TextIO, project_root: Path) -> int:
    payload = load_payload(stdin)
    if payload is None or payload.get("tool_name") not in TOOL_NAMES:
        return 0
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, Mapping) or tool_input.get("subagent_type") != handoff.AGENT_TYPE:
        return 0
    rel = handoff.find_handoff_rel(json.dumps(payload.get("tool_response"), ensure_ascii=False))
    path = handoff.resolve_handoff(project_root, rel) if rel is not None else None
    if rel is None or path is None:
        _evidence(stderr, result="skip", reason="NO_VALID_HANDOFF")
        return 0
    displayed = handoff.has_receipt(path)
    context = (DISPLAYED_NOTICE if displayed else NOT_DISPLAYED_NOTICE).format(rel=rel)
    json.dump(
        {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}},
        stdout, ensure_ascii=False,
    )
    stdout.write("\n")
    _evidence(stderr, result="notified", handoff=rel, displayed=displayed)
    return 0
