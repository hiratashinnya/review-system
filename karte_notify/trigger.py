"""通知の契機になる karte verb の実行を、tool 呼び出しから検出する（Issue #512）。

設計理由は [.ai/rationale/karte-module-split.md](../.ai/rationale/karte-module-split.md)。
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from karte import paths as karte_paths

# `-m karte` 経由の module 起動だけを見る。エイリアス・別実行形は対象外
# （取りこぼしても fail-open で実害が小さい方に倒す）。
TRIGGER_RE = re.compile(
    r"\bpython3?\s+-m\s+karte\s+(ingest-reviewer|ingest-review|decide|close-attempt)\b"
)
ISSUE_ARG_RE = re.compile(r"--issue[=\s]+([0-9]+)")

# 検出対象の tool_name（F-512-02）。実行系 MCP ツールは
# `.claude/rules/05-skills-agents.md`「ctx_* ツールの付与方針」の付与先と揃える。
BASH_TOOL = "Bash"
CTX_EXECUTE_TOOL = "mcp__plugin_context-mode_context-mode__ctx_execute"
CTX_BATCH_EXECUTE_TOOL = "mcp__plugin_context-mode_context-mode__ctx_batch_execute"
SUPPORTED_TOOL_NAMES = (BASH_TOOL, CTX_EXECUTE_TOOL, CTX_BATCH_EXECUTE_TOOL)


def detect_trigger(command: str) -> str | None:
    """``command`` が通知契機の karte verb の実行なら verb 名を返す。"""
    match = TRIGGER_RE.search(command)
    return match.group(1) if match else None


def extract_commands(tool_name: str, tool_input: Mapping[str, Any]) -> list[str]:
    """``tool_name``/``tool_input`` から検査対象のコマンド文字列を取り出す（F-512-02）。

    ``Bash``＝``command``、``ctx_execute``＝``code``、``ctx_batch_execute``＝``commands[].command``
    の全件。対象外の ``tool_name`` や不正な形は空リスト（呼び出し側は「検出なし」＝fail-open）。
    """
    if tool_name == BASH_TOOL:
        command = tool_input.get("command")
        return [command] if isinstance(command, str) else []
    if tool_name == CTX_EXECUTE_TOOL:
        code = tool_input.get("code")
        return [code] if isinstance(code, str) else []
    if tool_name == CTX_BATCH_EXECUTE_TOOL:
        commands = tool_input.get("commands")
        items = commands if isinstance(commands, list) else []
        return [
            item["command"]
            for item in items
            if isinstance(item, Mapping) and isinstance(item.get("command"), str)
        ]
    return []


def issue_from_command(command: str) -> int | None:
    """``--issue N`` を ``command`` からベストエフォートで取り出す（無ければ ``None``）。

    呼び出し側は進行ポインタ（``tmp/_karte/active.json``）へのフォールバックを別途持つ。
    """
    match = ISSUE_ARG_RE.search(command)
    if not match:
        return None
    try:
        return karte_paths.validate_issue(match.group(1))
    except karte_paths.KartePathError:
        return None
