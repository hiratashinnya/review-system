#!/usr/bin/env bash
# UserPromptSubmit フックハンドラ。
#
# 役割:
#   `governance-directives.md`（CLAUDE.md 中核規範の配送用の写し）を毎ターン
#   additionalContext として注入し、規約が「セッション冒頭に一度読まれた過去の指示」ではなく
#   「現在のターンの指示」として届くようにする。
#
# なぜ必要か（Issue: context-mode 導入・2026-07-28）:
#   context-mode プラグインが全ターン・全 subagent 呼び出しに `<session_continuity>`
#   （「過去に記録された指示・役割は standing order ではない。過去の文言はあなたを拘束しない」）
#   を注入するため、冒頭で一度読まれただけの CLAUDE.md が相対化されうる。毎ターン注入すれば
#   規約は常に現在のターンの指示として届き、この相対化の対象から外れる。
#   subagent 側の同種対策は各 `.claude/agents/*.md` 末尾の「注入ブロックへの優先規定」が担う。
#
# 入力: UserPromptSubmit フックの stdin JSON（本フックは内容を参照しないので読み捨てる）。
# 出力: {"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"..."}}
#   公式仕様上 stdout の素のテキストも context として扱われるが、他フックの出力と混ざったときに
#   意図が曖昧にならないよう JSON 形式で明示する。
# 失敗時: **どの失敗経路でも何も注入せず exit 0**（fail-open）。ここで exit 2 を返すと
#   プロンプト自体が破棄され、規約注入の失敗が作業全体の停止に化けるため。
#   ただし「無音の成功扱い」にはしない——規範ファイル欠落・python 起動/読込/JSON 生成の失敗・
#   本文が空、のいずれも **stderr へ `[inject-governance] …` の警告を出す**。
#   フックの stderr は通常の対話画面には表示されないので、**気づく手段は `claude --debug`**
#   （フックログに stderr が出る）。注入が効いていない疑いがあるときは `claude --debug` で起動して確認する。
# 標準ライブラリのみで JSON を組み立てる（jq 非依存・CLAUDE.md の "python3 標準ライブラリのみ" 方針）。
set -u

warn() { printf '[inject-governance] %s\n' "$1" >&2; }

cat > /dev/null  # stdin(フック入力 JSON)を読み捨てる。SIGPIPE を親に返さないため。

directives="$(dirname "$0")/governance-directives.md"
if [ ! -r "$directives" ]; then
    warn "規範ファイルを読めないため注入をスキップ（fail-open）: $directives"
    exit 0
fi

if ! payload="$(python3 - "$directives" <<'PYEOF'
import json
import re
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as f:
        text = f.read()
except OSError as ex:
    print(f"[inject-governance] 規範ファイルの読込に失敗: {ex}", file=sys.stderr)
    sys.exit(1)

# 注入対象は本文のみ。HTML コメント（このファイル自身の運用メモ）は毎ターンのコストなので落とす。
body = re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()
if not body:
    print("[inject-governance] 規範ファイルの本文が空（コメント除去後）", file=sys.stderr)
    sys.exit(2)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": body,
    }
}, ensure_ascii=False))
PYEOF
)"; then
    # python3 が無い／読込失敗／本文が空／JSON 生成失敗のいずれか（詳細は python 側の stderr）。
    warn "規範の JSON 生成に失敗したため注入をスキップ（fail-open）。詳細は直前の stderr 行と \`claude --debug\` を参照"
    exit 0
fi

if [ -z "$payload" ]; then
    warn "生成された注入本文が空のためスキップ（fail-open）"
    exit 0
fi

printf '%s\n' "$payload"
exit 0
