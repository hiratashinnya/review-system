#!/usr/bin/env bash
# PostToolUse(Write|Edit) フックハンドラ。
#
# 役割:
#   正本 `CLAUDE.md` を編集したのに配送用の写し `governance-directives.md` を追従させ忘れる
#   drift を、機械的に検知してリマインドする。
#
# なぜ必要か（実際に起きた・PR #276 / Codex レビュー指摘 #6）:
#   `governance-directives.md` は CLAUDE.md 中核規範の写しで、UserPromptSubmit フックが毎ターン
#   注入する。PR #276 では CLAUDE.md 側に「このリポジトリ＝2つのプロジェクトが同居」節が入ったのに
#   写しを追従させ忘れ、「docs/ は一律非正本」という**誤った規範を毎ターン注入し続ける**状態になった。
#   「片方直すの忘れました」は再現性のあるミスなので、人の注意力ではなくハーネスで検知する。
#
# 検知方式（nag ではなく状態比較）:
#   写しの中に `<!-- synced-from: CLAUDE.md@<sha256 先頭12桁> -->` を1行埋めておき、
#   現在の CLAUDE.md のハッシュと突き合わせる。**一致していれば何も言わない**（毎回の小言を避ける）。
#   食い違っている間だけ警告を出し続ける（追従して sha を更新するまで消えない＝fail-safe な向き）。
#
# 入力: PostToolUse フックの stdin JSON（`tool_input.file_path` を見る）。
# 出力: 追従漏れのときだけ additionalContext を返す。それ以外は無出力。
# 失敗時: **常に exit 0**（fail-open）。このフックは補助であり、作業を止める役ではない。
#   異常は stderr に出す（`claude --debug` で拾える）。
# 標準ライブラリのみで JSON を扱う（jq 非依存・CLAUDE.md の "python3 標準ライブラリのみ" 方針）。
set -u

warn() { printf '[check-governance-drift] %s\n' "$1" >&2; }

tmpfile="$(mktemp)" || { warn "mktemp に失敗"; exit 0; }
trap 'rm -f "$tmpfile"' EXIT
cat > "$tmpfile"

repo_root="${CLAUDE_PROJECT_DIR:-$(dirname "$(dirname "$(dirname "$0")")")}"

python3 - "$tmpfile" "$repo_root" <<'PYEOF' || warn "python 実行に失敗（追従チェックを skip）"
import hashlib
import json
import os
import re
import sys

payload_path, repo_root = sys.argv[1], sys.argv[2]
CANON = "CLAUDE.md"
COPY = os.path.join(".claude", "hooks", "governance-directives.md")
MARKER_RE = re.compile(r"<!--\s*synced-from:\s*CLAUDE\.md@([0-9a-f]{12})\s*-->")

try:
    with open(payload_path, encoding="utf-8") as f:
        payload = json.load(f)
except Exception as exc:  # 壊れた payload でも作業は止めない
    print(f"[check-governance-drift] payload を読めない: {exc}", file=sys.stderr)
    sys.exit(0)

tool_input = payload.get("tool_input")
edited = tool_input.get("file_path") if isinstance(tool_input, dict) else None
if not isinstance(edited, str) or not edited:
    sys.exit(0)

# 編集対象が正本 CLAUDE.md でなければ何もしない（写し自身の編集も対象外＝追従作業を邪魔しない）。
if os.path.basename(edited) != CANON:
    sys.exit(0)
canon_path = os.path.join(repo_root, CANON)
if os.path.realpath(edited) != os.path.realpath(canon_path):
    sys.exit(0)  # 別プロジェクトの同名ファイル

copy_path = os.path.join(repo_root, COPY)
try:
    canon_bytes = open(canon_path, "rb").read()
    copy_text = open(copy_path, encoding="utf-8").read()
except OSError as exc:
    print(f"[check-governance-drift] 正本/写しを読めない: {exc}", file=sys.stderr)
    sys.exit(0)

current = hashlib.sha256(canon_bytes).hexdigest()[:12]
m = MARKER_RE.search(copy_text)
recorded = m.group(1) if m else None

if recorded == current:
    sys.exit(0)  # 追従済み。黙る。

if recorded is None:
    detail = f"`{COPY}` に `synced-from` マーカーが無い"
else:
    detail = f"記録 `{recorded}` ≠ 現在 `{current}`"

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": (
            f"⚠️ 規範の追従漏れ検知：`{CANON}`（正本）を編集したが、"
            f"毎ターン注入される写し `{COPY}` が追従していない（{detail}）。\n"
            f"CLAUDE.md の中核規範（PR7・起票規律・独断禁止・委譲ルール・課金方針・正本の所在）に"
            f"関わる変更なら、写しにも反映すること。**写しの誤りは毎ターン注入されるため影響が大きい**"
            f"（実例＝PR #276 / Codex 指摘 #6：`docs/` の正本性を誤ったまま注入し続けた）。\n"
            f"反映が済んだら（または今回の変更が中核規範に無関係だと判断したら）、写しの1行目付近の\n"
            f"`<!-- synced-from: CLAUDE.md@{current} -->` を現在値 `{current}` に更新して警告を解除する。"
        ),
    }
}, ensure_ascii=False))
PYEOF
exit 0
