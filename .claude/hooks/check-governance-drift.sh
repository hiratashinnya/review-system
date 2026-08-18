#!/usr/bin/env bash
# PostToolUse(Write|Edit) フックハンドラ。
#
# 役割:
#   正本（`CLAUDE.md` ＋ `.claude/rules/*.md`）を編集したのに配送用の写し
#   `governance-directives.md` を追従させ忘れる drift を、機械的に検知してリマインドする。
#
# 正本が「集合」である理由（Issue #387 / PR #383）:
#   規範本文は CLAUDE.md 単体から `.claude/rules/NN-*.md` へ分割された。CLAUDE.md 単体の
#   ハッシュを見張り続けると、**規範の大半を占める rules 側の変更に一切反応しない**。
#   そのため対象を正本集合の連結ハッシュへ拡張する。marker の形式（1行）は維持する。
#
# なぜ必要か（実際に起きた・PR #276 / Codex レビュー指摘 #6）:
#   `governance-directives.md` は CLAUDE.md 中核規範の写しで、UserPromptSubmit フックが毎ターン
#   注入する。PR #276 では CLAUDE.md 側に「このリポジトリ＝2つのプロジェクトが同居」節が入ったのに
#   写しを追従させ忘れ、「docs/ は一律非正本」という**誤った規範を毎ターン注入し続ける**状態になった。
#   「片方直すの忘れました」は再現性のあるミスなので、人の注意力ではなくハーネスで検知する。
#
# 検知方式（nag ではなく状態比較）:
#   写しの中に `<!-- synced-from: CLAUDE.md@<sha256 先頭12桁> -->` を1行埋めておき、
#   現在の正本集合の連結ハッシュと突き合わせる。**一致していれば何も言わない**（毎回の小言を避ける）。
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
import glob
import hashlib
import json
import os
import re
import sys

payload_path, repo_root = sys.argv[1], sys.argv[2]
ENTRYPOINT = "CLAUDE.md"
RULES_GLOB = os.path.join(".claude", "rules", "*.md")
COPY = os.path.join(".claude", "hooks", "governance-directives.md")
MARKER_RE = re.compile(r"<!--\s*synced-from:\s*CLAUDE\.md@([0-9a-f]{12})\s*-->")


def canonical_relpaths():
    """正本集合を相対パス（posix 表記）の昇順で返す。

    依存仕様は `tests/unit/test_governance_sync.py` と同一である必要がある。
    """
    rules = sorted(
        os.path.relpath(p, repo_root).replace(os.sep, "/")
        for p in glob.glob(os.path.join(repo_root, RULES_GLOB))
    )
    return [ENTRYPOINT] + rules


def canonical_hash(relpaths):
    """「相対パス + NUL + 生バイト + NUL」を順に連結した sha256 の先頭12桁。

    相対パスを混ぜるのは、ファイルの分割・改名・並び替えを内容の移動と区別するため。
    """
    digest = hashlib.sha256()
    for rel in relpaths:
        with open(os.path.join(repo_root, rel), "rb") as fh:
            body = fh.read()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(body)
        digest.update(b"\0")
    return digest.hexdigest()[:12]

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

# 編集対象が正本集合のどれでもなければ何もしない（写し自身の編集も対象外＝追従作業を邪魔しない）。
# 別プロジェクトの同名ファイルを弾くため、basename ではなく realpath 一致で判定する。
try:
    relpaths = canonical_relpaths()
except OSError as exc:
    print(f"[check-governance-drift] 正本集合を列挙できない: {exc}", file=sys.stderr)
    sys.exit(0)

edited_real = os.path.realpath(edited)
canonical_reals = {
    os.path.realpath(os.path.join(repo_root, rel)): rel for rel in relpaths
}
edited_rel = canonical_reals.get(edited_real)
if edited_rel is None:
    sys.exit(0)

copy_path = os.path.join(repo_root, COPY)
try:
    current = canonical_hash(relpaths)
    copy_text = open(copy_path, encoding="utf-8").read()
except OSError as exc:
    print(f"[check-governance-drift] 正本/写しを読めない: {exc}", file=sys.stderr)
    sys.exit(0)

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
            f"⚠️ 規範の追従漏れ検知：`{edited_rel}`（正本集合の一部）を編集したが、"
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
