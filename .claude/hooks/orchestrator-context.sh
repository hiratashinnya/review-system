#!/usr/bin/env bash
# SessionStart フックハンドラ("startup"/"clear"/"compact" で発火・"resume" では発火させない)。
#
# 役割:
#   主文脈を「オーケストレーション＋ユーザーとのコミュニケーション」に限定するための
#   委譲ルール(Orchestrator Task Delegation Rules)を、セッション開始時のコンテキストへ
#   注入する。主文脈とサブエージェント間の二重作業(ステップ細部までの指示→サブエージェント
#   側での再展開)によるトークン浪費を防ぐことが目的。
#   続けて `.claude/main-context/*.md`(主文脈専用の規範の正本)の全文を名前順に連結する。
#   SessionStart は主文脈のイベントなのでサブエージェントへは届かない。毎ターンの
#   UserPromptSubmit(inject-governance.sh)には要約の写し(governance-directives.md 項12)だけを載せ、
#   全文はここで startup/clear/compact のときに載せる(全文を毎ターン積むと文脈を圧迫するため)。
#
# 発火条件(matcher で担保・本スクリプトは絞り込まない):
#   settings.json 側の matcher を "startup|clear|compact" とし、"resume"(セッション再開)を
#   明示的に除外する。resume は既存の会話コンテキストを引き継ぐため、委譲ルールを
#   再注入する必要がない(要件①)。
#   "compact" は公式仕様上 SessionStart イベントの source フィールドが取り得る値の一つで、
#   コンパクション(自動/手動の要約による文脈圧縮)後にセッションが再開する際に発火する
#   (Claude Code に独立した PostCompaction イベントは存在しない)。コンパクションでは
#   委譲ルールの指示文もコンテキストから失われ得るため、"compact" を含めて再注入対象とする。
#
# コンテキスト本文の分離(要件③):
#   注入する本文は本スクリプトに埋め込まず、同ディレクトリの
#   orchestrator-context/orchestrator-task-delegation-rules.md と `.claude/main-context/*.md` に分離する。
#   本文の更新はテキストファイルの編集のみで完結させ、スクリプト変更を不要にする。
#
# 失敗時(fail-open・セッション開始を妨げない):
#   どの経路でも exit 0。読めない/UTF-8 として不正なファイルは stderr に警告して飛ばし、
#   残りの注入は続ける。python3 での組み立て自体に失敗したら、委譲ルールだけを従来の
#   jq/sed 経路で注入する(主文脈専用の規範は届かない旨を stderr に出す)。
#   フックの stderr は通常の対話画面には出ないので、確認は `claude --debug` で行う。
set -u

warn() { printf '[orchestrator-context] %s\n' "$1" >&2; }

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTEXT_FILE="${HOOK_DIR}/orchestrator-context/orchestrator-task-delegation-rules.md"
MAIN_CONTEXT_DIR="${HOOK_DIR}/../main-context"

payload="$(python3 - "$CONTEXT_FILE" "$MAIN_CONTEXT_DIR" <<'PYEOF'
import json
import re
import sys
from pathlib import Path


def read(path, label):
    # 文字コード不正(UnicodeDecodeError)も含め、1ファイルの失敗で注入全体を落とさない。
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as ex:
        print(f"[orchestrator-context] {label}を読めないため飛ばす: {path}: {ex}", file=sys.stderr)
        return ""


parts = []
rules = Path(sys.argv[1])
if rules.is_file():
    text = read(rules, "委譲ルール").strip()
    if text:
        parts.append(text)

for path in sorted(Path(sys.argv[2]).glob("*.md")):
    body = re.sub(r"<!--.*?-->", "", read(path, "主文脈専用の規定"), flags=re.S).strip()
    if body:
        parts.append(f"# 主文脈専用の規定（正本＝`.claude/main-context/{path.name}`）\n\n{body}")

if not parts:
    sys.exit(3)  # 注入するものが無い(従来の「コンテキストファイルが無ければ何もしない」と同じ扱い)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "\n\n---\n\n".join(parts),
    }
}, ensure_ascii=False))
PYEOF
)"
status=$?

if [ "$status" -eq 0 ] && [ -n "$payload" ]; then
  printf '%s\n' "$payload"
  exit 0
fi
if [ "$status" -eq 3 ]; then
  exit 0
fi
warn "python3 での組み立てに失敗(status=${status})。委譲ルールだけを注入する(主文脈専用の規範は届かない)"

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
