#!/usr/bin/env bash
# PostToolUse（matcher: Task|Agent）— gh-create-issue サブエージェントの成果物は
# SubagentStop フック（subagent-draft-display.sh）が表示済みであることを、
# additionalContext で主文脈へ伝える（再掲によるトークンの二重消費を防ぐ）。
# 実体は python 側（`draft_display.notice`）。
#
# stdin の事前フィルタ: `gh-create-issue` を含まない Task/Agent 呼び出しでは python を
# 起動しない。python 側は subagent_type の完全一致を要求するので、部分文字列検査で
# 「無ければ python 側も必ず対象外」と言える（偽陰性なし）。
#
# fail-open・無統制（PostToolUse はブロックできない）。診断は stderr（`claude --debug`）。
set -uo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
cd "$PROJECT_ROOT" || exit 0

payload="$(cat)"
case "$payload" in
  *gh-create-issue*)
    ;;
  *)
    exit 0
    ;;
esac

export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONSAFEPATH=1
printf '%s' "$payload" | python3 -m draft_display notice
exit 0
