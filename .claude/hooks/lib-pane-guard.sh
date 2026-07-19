#!/usr/bin/env bash
# 共有ライブラリ: レートリミット自動再開フックの2スクリプト
#   (on-rate-limit.sh / resume-watcher.sh)
# が共通で source して使う、状態パス・ペイン判定・tmux 呼び出しラッパ。
#
# 設計(out-of-band 方式):
#   ①検知時刻は tmux 入力欄へは打たない。状態ファイル(hit-time.<slug>)へ記録し、
#   status-bar(display-message)へ一瞬フラッシュするだけにする。②は状態ファイルを
#   読み、解除時の送信メッセージへ「検知/解除/現在」を折り込んで LLM に届ける。
#   これにより「入力欄という共有状態へ複数プロセスが書き込む」構図が無くなり、
#   マーカー・行クリア(C-u)・注入ロックといった調整と、それに伴うバグ(手打ち
#   テキストの消去/連結など)が原理的に不要になる。
#
# 目的(横断):
#   - ペイン前景判定と状態パス生成を1箇所へ集約し、2ファイルへの二重実装(片方
#     だけ更新して不整合になる drift)を防ぐ。
#   - すべての tmux 呼び出しを timeout でラップし、tmux サーバのハングが呼び出し元を
#     無限ブロックする(=resume-watcher.sh では取得済みの flock を永久保持し、以後
#     そのペインの自動再開を殺す)のを防ぐ。
#
# ※ source 専用(直接実行しない)。set -u 下で source される前提。

# 状態ファイル置き場(両スクリプト共通)。
RL_STATE_DIR="${HOME}/.claude/rate-limit-recovery"
mkdir -p "$RL_STATE_DIR" 2>/dev/null || true

# 注入を許可する前景コマンド(既定=claude 本体=node 実行・完全一致)。env で上書き可。
RL_PANE_CMD_RE="${CLAUDE_RL_PANE_CMD_RE:-^(claude|node)$}"

# tmux 呼び出しの timeout 秒(ハング対策)。env で上書き可。
RL_TMUX_TIMEOUT="${CLAUDE_RL_TMUX_TIMEOUT:-3}"

# timeout でラップした tmux 実行。tmux サーバがハングしても RL_TMUX_TIMEOUT 秒で必ず返る。
rl_tmux() { timeout "$RL_TMUX_TIMEOUT" tmux "$@"; }

# tmux ペインID を状態ファイル名に使える文字だけへ正規化(両スクリプトで共有)。
rl_pane_slug() { printf '%s' "$1" | tr -c 'A-Za-z0-9' '_'; }

# ①が検知時刻を書き、②が読む状態ファイルのパス(ペインごと)。
rl_hit_file() { printf '%s/hit-time.%s' "$RL_STATE_DIR" "$(rl_pane_slug "$1")"; }

# 指定ペインが生存し、前景コマンドが claude 系(=キー注入して安全)か。
# ペインが閉じている/シェル等に戻っている場合に誤送出しないためのガード。
rl_is_claude_pane() {
  local pane="$1" cmd
  cmd="$(rl_tmux display-message -p -t "$pane" '#{pane_current_command}' 2>/dev/null)" || return 1
  [ -n "$cmd" ] || return 1   # ペインが存在しない/取得不可 → 注入しない
  # -- でパターン終端を明示(RL_PANE_CMD_RE は env で上書き可能=`-`始まりでもオプション誤認しない)
  printf '%s' "$cmd" | grep -qiE -- "$RL_PANE_CMD_RE"
}
