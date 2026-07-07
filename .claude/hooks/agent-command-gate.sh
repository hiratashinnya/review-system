#!/usr/bin/env bash
# PreToolUse(Bash) フックハンドラ。
#
# 役割:
#   "issue-implementer" / "pr-reviewer" サブエージェント種別に対して、push と merge の
#   非対称な権限境界を機械的に強制する（プロンプト指示ではなくハーネスで拒否するため、
#   プロンプトインジェクションやモデルの判断ミスでは回避できない——ただし正規表現ベースの限界は下記参照）。
#     - issue-implementer: push・PR作成は可、merge は不可（実装→PR作成までで STOP）。
#     - pr-reviewer:        merge は可、push は不可（レビュー中に無レビューの変更を紛れ込ませられない）。
#   それ以外の agent_type（main／general-purpose／各 *-author 等）はこのゲートの対象外。
#
# 既知の限界（Issue #129・多層防御の一枚に過ぎない）:
#   コマンド置換($()/バッククォート)・サブシェル・eval・別インタプリタ経由(python -c 'os.system(...)')・
#   git alias(git -c alias.m=merge m)・ラッパースクリプト実行等は、この正規表現ベースの判定では
#   検知できない（迂回余地が残る）。本フックは「素朴な直接呼び出しを機械的に塞ぐ」一次防御であり、
#   pr-reviewer.md 側のプロンプトレベルの絶対規範（自己承認バイパス禁止）と併用する前提。
#
# 入力: PreToolUse フックの stdin JSON（少なくとも agent_type と tool_input.command を含む想定。
#   フィールド名の確定情報が乏しいため subagent_type もフォールバックで見る）。
# 標準ライブラリのみで JSON をパースする（jq 非依存・CLAUDE.md の "python3 標準ライブラリのみ" 方針に合わせる）。
# 実装注意: `python3 - <<EOF ... EOF` は heredoc がそのまま python の stdin になり、外側で
# パイプされた本来の stdin（フック入力 JSON）が読めなくなる。よって stdin を一旦ファイルに
# 落としてから python にファイル引数として渡す。
set -u

tmpfile="$(mktemp)"
trap 'rm -f "$tmpfile"' EXIT
cat > "$tmpfile"

python3 - "$tmpfile" <<'PYEOF'
import json
import re
import sys

try:
    with open(sys.argv[1]) as f:
        payload = json.load(f)
except Exception:
    sys.exit(0)  # パース不能なら通常のパーミッションフローに委ねる（fail-open ではなく無関与）

agent_type = payload.get("agent_type") or payload.get("subagent_type") or ""
command = (payload.get("tool_input") or {}).get("command") or ""

# (?!-) excludes git's own merge-base/merge-tree subcommands (false-positive fix, Issue #129).
# [;&|\n] anchor set includes a bare newline so a plain multi-line Bash command (not just an
# adversarial one-liner) is also caught (Issue #129 finding). Deeper evasions (command
# substitution, subshells, eval, other interpreters, git aliases) are NOT caught by this regex —
# see the module docstring above; this is one defense-in-depth layer, not a complete sandbox.
DENY_FOR_IMPLEMENTER = re.compile(r"(^|[;&|\n]|&&)\s*(git\s+merge(?!-)|gh\s+pr\s+merge)\b")
DENY_FOR_REVIEWER = re.compile(r"(^|[;&|\n]|&&)\s*git\s+push\b")

reason = None
if agent_type == "issue-implementer" and DENY_FOR_IMPLEMENTER.search(command):
    reason = "issue-implementer role: merge is reserved for pr-reviewer. Push + open a PR, then stop and report."
elif agent_type == "pr-reviewer" and DENY_FOR_REVIEWER.search(command):
    reason = "pr-reviewer role: push is reserved for issue-implementer. Reviewers may inspect/comment/merge only, never push code."

if reason:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
PYEOF
exit 0
