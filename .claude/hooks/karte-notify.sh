#!/usr/bin/env bash
# PostToolUse（matcher: Bash）— karte ingest-review / close-attempt の実行直後に
# `karte status --json` の判定を AI の要約を経ずに systemMessage でオーナーへ直送する
# （Issue #512）。実体は python 側（`karte_notify.hook`）。
#
# 対象外コマンド（karte ingest-review/close-attempt 以外の全ての Bash 呼び出し）は
# 無出力 exit 0（判定は python 側の :func:`karte_notify.hook.run` が行う）。本フックは
# 統制（deny）を一切行わない可視化専用の助言機構であり、失敗しても作業を止めない
# （fail-open。診断は stderr へ・`claude --debug` で拾える）。
#
# cwd 非依存の起動（`issue_start` 系フックと同じ作法）: `python3 -m` は sys.path[0] に
# プロセスの cwd を先に置くため、別ツリー（linked worktree）を cwd にして起動されると
# cwd 側の同名モジュールが $CLAUDE_PROJECT_DIR 側の実体を覆い隠しうる。
#   * `cd "$PROJECT_ROOT"` … cwd 自体を正本側へ寄せる。
#   * `PYTHONSAFEPATH=1`  … cwd の暗黙追加そのものを止める（3.11+。旧版では無視される）。
set -uo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
cd "$PROJECT_ROOT" || exit 0
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONSAFEPATH=1
python3 -m karte_notify.hook
exit 0
