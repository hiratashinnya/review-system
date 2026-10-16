from __future__ import annotations

from typing import Any, Mapping



def _caller_agent_type(payload: Mapping[str, Any]) -> str | None:
    """Task/Agent dispatch の**呼び出し元**の agent_type を top-level payload から読む
    （Issue #517・F-510-02 で ``subagent_type`` を対象から外して訂正）。

    ``tool_input.agent_type``/``tool_input.subagent_type`` は dispatch **先**（callee）の値
    であり、ここでは意図的に見ない——取り違えると「誰が呼んだか」の判定が「誰を呼んだか」の
    値で行われてしまう。**top-level 側も ``subagent_type`` は見ない**：`Task`/`Agent` ツールでは
    ``subagent_type`` が dispatch 先を指す tool_input のフィールド名そのものであり、payload の
    top-level にも同名フィールドが現れた場合、それが「呼び出し元の識別子」なのか「dispatch 先を
    指すフィールドが何らかの理由で top-level にも複製されたもの」なのか構造的に一意に決まらない。
    旧実装はここに ``subagent_type`` を含めていたため、main context 自身が gated ロール
    （`issue-fixer` 等）へ正当に dispatch する呼び出しで、top-level にも ``subagent_type``
    （tool_input と同じ値）が乗る形を「呼び出し元が gated ロールである」と誤判定し、
    `/issue-pipeline` の Task dispatch 全体を止めうるバグがあった（F-510-02）。
    `.claude/hooks/agent-command-gate.sh`（Bash・実行系 MCP 経路）の ``first_string`` が
    ``subagent_type`` を含めているのは、そちらの tool_input（Bash の場合は ``command`` のみ）に
    同名フィールドが存在せず衝突しないためで、Task/Agent 経路にそのまま流用できる規約ではない。
    top-level の ``agent_type``/``agent.type`` は tool_input 側にこの名前の callee フィールドが
    存在しない（callee は常に ``subagent_type``（Claude）/``agent_type``（Codex tool_input内）
    経由で、top-level の ``agent_type``/``agent.type`` と衝突しない）ため曖昧さが無く、
    引き続き呼び出し元識別に使う。
    フィールドが存在しない環境（未確認）では常に ``None`` を返し、呼び出し側の判定は
    無害な no-op になる（frontmatter からの `Task` 除去＝第一層が主たる防御であることに変わりはない）。
    """
    value = payload.get("agent_type")
    if isinstance(value, str) and value:
        return value
    agent = payload.get("agent")
    if isinstance(agent, dict):
        value = agent.get("type")
        if isinstance(value, str) and value:
            return value
    return None
