#!/usr/bin/env bash
# PostToolUse（matcher: Bash|ctx_execute|ctx_batch_execute）— karte ingest-review /
# close-attempt の実行直後に `karte status --json` の判定を AI の要約を経ずに
# systemMessage でオーナーへ直送する（Issue #512）。実体は python 側（`karte_notify.hook`）。
# matcher を実行系 MCP ツールへも広げた理由は Issue #512 是正（F-512-02）——
# ctx_execute/ctx_batch_execute 経由でも同じ karte verb が実行されうるため
# （`.claude/rules/05-skills-agents.md`「ctx_* ツールの付与方針」）。
#
# 対象外コマンド（karte ingest-review/close-attempt を含まない全ての呼び出し）は
# 無出力 exit 0。本フックは統制（deny）を一切行わない可視化専用の助言機構であり、
# 失敗しても作業を止めない（fail-open。診断は stderr へ・`claude --debug` で拾える）。
#
# stdin の事前フィルタ（Issue #512 是正・F-512-07）: トリガー語（ingest-review／
# close-attempt）を含まない stdin では python を起動しない。python 側の
# `notify.TRIGGER_RE` はこの2語のいずれかを部分文字列として要求するため、shell 側の
# 部分文字列検査で「無ければ python 側も必ず不一致」と言え、誤って早期 exit する
# （偽陰性）ことはない——unrelated な Bash/ctx 呼び出しごとに python インタプリタを
# 起動するコストだけを削る最適化であり、判定ロジック自体はここに複製しない。
#
# cwd 非依存の起動（`issue_start` 系フックと同じ作法）: `python3 -m` は sys.path[0] に
# プロセスの cwd を先に置くため、別ツリー（linked worktree）を cwd にして起動されると
# cwd 側の同名モジュールが $CLAUDE_PROJECT_DIR 側の実体を覆い隠しうる。
#   * `cd "$PROJECT_ROOT"` … cwd 自体を正本側へ寄せる。
#   * `PYTHONSAFEPATH=1`  … cwd の暗黙追加そのものを止める（3.11+。旧版では無視される）。
set -uo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
cd "$PROJECT_ROOT" || exit 0

payload="$(cat)"
case "$payload" in
  *ingest-review*|*close-attempt*)
    ;;
  *)
    exit 0
    ;;
esac

export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONSAFEPATH=1
printf '%s' "$payload" | python3 -m karte_notify.hook
exit 0
