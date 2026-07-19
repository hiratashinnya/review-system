#!/usr/bin/env bash
# 共有ライブラリ: レートリミット自動再開フックの2スクリプト
#   (on-rate-limit.sh / resume-watcher.sh)
# が共通で source して使う、ペイン判定・tmux 呼び出しラッパ・定数。
#
# 目的(コードレビュー指摘の是正):
#   - ペイン前景判定ロジックとデフォルト正規表現を1箇所へ集約し、2ファイルへの
#     二重実装による drift(片方だけ更新して不整合)を防ぐ。
#   - すべての tmux 呼び出しを timeout でラップし、tmux サーバのハングが
#     呼び出し元プロセスを無限ブロックする(=resume-watcher.sh では取得済みの
#     flock を永久保持し、以後そのペインの自動再開を殺す)のを防ぐ。
#   - ①の検知ドラフトを②が識別して「自分のドラフトだけ」を消せるよう、共通の
#     マーカー文字列を定義する(ユーザーが手打ちした別テキストを巻き込まない)。
#
# ※ このファイルは source 専用(直接実行しない)。set -u 下で source される前提。

# 注入を許可する前景コマンド(既定=claude 本体=node 実行・完全一致)。env で上書き可。
RL_PANE_CMD_RE="${CLAUDE_RL_PANE_CMD_RE:-^(claude|node)$}"

# ①検知ドラフトの識別マーカー。②はこの文字列が入力欄付近に見えるときだけ行をクリアする。
# grep -F(固定文字列)で判定するため、正規表現メタ文字を含んでいてもそのまま比較される。
RL_DRAFT_MARKER="${CLAUDE_RL_DRAFT_MARKER:-[rate-limit-hook]}"

# tmux 呼び出しの timeout 秒(ハング対策)。env で上書き可。
RL_TMUX_TIMEOUT="${CLAUDE_RL_TMUX_TIMEOUT:-3}"

# timeout でラップした tmux 実行。tmux サーバがハングしても RL_TMUX_TIMEOUT 秒で必ず返る。
rl_tmux() { timeout "$RL_TMUX_TIMEOUT" tmux "$@"; }

# 指定ペインが生存し、前景コマンドが claude 系(=キー注入して安全)か。
# ペインが閉じている/シェル等に戻っている場合に誤送出しないためのガード。
rl_is_claude_pane() {
  local pane="$1" cmd
  cmd="$(rl_tmux display-message -p -t "$pane" '#{pane_current_command}' 2>/dev/null)" || return 1
  [ -n "$cmd" ] || return 1   # ペインが存在しない/取得不可 → 注入しない
  # -- でパターン終端を明示(RL_PANE_CMD_RE は env で上書き可能=`-`始まりでもオプション誤認しない)
  printf '%s' "$cmd" | grep -qiE -- "$RL_PANE_CMD_RE"
}
