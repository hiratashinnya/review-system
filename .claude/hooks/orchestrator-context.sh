#!/usr/bin/env bash
# SessionStart フックハンドラ("startup"/"clear" のみ・"resume" では発火させない)。
#
# 役割:
#   主文脈を「オーケストレーション＋ユーザーとのコミュニケーション」に限定するための
#   委譲ルール(Orchestrator Task Delegation Rules)を、セッション開始時のコンテキストへ
#   注入する。主文脈とサブエージェント間の二重作業(ステップ細部までの指示→サブエージェント
#   側での再展開)によるトークン浪費を防ぐことが目的。
#
# 発火条件(matcher で担保・本スクリプトは絞り込まない):
#   settings.json 側の matcher を "startup|clear" とし、"resume"(セッション再開)を
#   明示的に除外する。resume は既存の会話コンテキストを引き継ぐため、委譲ルールを
#   再注入する必要がない(要件①)。
#
# コンテキスト本文の分離(要件③):
#   注入する本文は本スクリプトに埋め込まず、同ディレクトリの
#   orchestrator-context/orchestrator-task-delegation-rules.md に分離する。
#   本文の更新はテキストファイルの編集のみで完結させ、スクリプト変更を不要にする。
set -u

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTEXT_FILE="${HOOK_DIR}/orchestrator-context/orchestrator-task-delegation-rules.md"

if [ ! -f "$CONTEXT_FILE" ]; then
  # コンテキストファイルが無い場合は注入せずに正常終了する(壊れた設定でセッション開始を
  # 妨げない=fail-open)。
  exit 0
fi

context="$(cat "$CONTEXT_FILE")"

if command -v jq >/dev/null 2>&1; then
  jq -n --arg ctx "$context" \
    '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
else
  # jq が無い環境向けの簡易フォールバック(標準ツールのみでの最小 JSON エスケープ)。
  escaped="$(printf '%s' "$context" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk '{printf "%s\\n", $0}')"
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$escaped"
fi

exit 0
