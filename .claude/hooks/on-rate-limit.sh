#!/usr/bin/env bash
# StopFailure(rate_limit) フックハンドラ。
#
# 役割:
#   レートリミット検知時に、WSL 環境でだけ「自動再開ウォッチャ(resume-watcher.sh)」を
#   切り離し起動する。クラウド(=非WSL)では何もしない no-op。
#
# 前提となる公式仕様(調査済み):
#   - StopFailure は出力・終了コードが「無視」される。よってフック自身は再開/リトライを
#     制御できない。できるのは副作用(別プロセスの起動・ログ)のみ。
#   - stdin で {session_id, transcript_path, cwd, hook_event_name, ...} を受け取る。
#     error_type のトップレベル文字列フィールドは公式に未確定で、実機では空で届くことを確認した
#     (2026-06-30)。よって発火の絞り込みは settings.json の matcher(=rate_limit)に委ね、
#     本スクリプトでは error_type を必須にしない(空/不明なら matcher を信頼して継続)。
#     リセット時刻は含まれない。
#
# 設計方針:
#   - 環境ゲートは「WSL を積極検知できたときだけ動く」許可リスト方式。
#     検知できない環境(クラウド/その他)は自動的に無害化される。
#   - 再開方式は tmux 端末注入(対話セッションのペインへ "続けて" を送出)。
set -u

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 共有ガード(状態パス・ペイン判定・tmux timeout ラッパ)。resume-watcher.sh と共有。
# lib が無ければ本フックは機能しない=誤動作より即中断が安全。明示的に失敗ログして exit。
if ! source "${HOOK_DIR}/lib-pane-guard.sh" 2>/dev/null; then
  # 状態ディレクトリを作るのは lib 自身なので、lib 読込失敗時は未作成のことがある。
  # FATAL を痕跡ゼロで握り潰さないよう、ここで best-effort に mkdir してから追記する。
  mkdir -p "${HOME}/.claude/rate-limit-recovery" 2>/dev/null || true
  printf '%s [hook] FATAL: lib-pane-guard.sh を読み込めません; abort\n' "$(date '+%F %T')" \
    >> "${HOME}/.claude/rate-limit-recovery/hook.log" 2>/dev/null || true
  exit 0
fi
STATE_DIR="$RL_STATE_DIR"
LOG="${STATE_DIR}/hook.log"

# ログ書式は共有ファクトリ rl_log_line に集約(watcher と同一書式・Issue #240 C3)。
log() { rl_log_line "$LOG" "[hook]" "$*"; }

# --- stdin JSON を素朴に読む(標準ツールのみ・jq 非依存) ---
payload="$(cat)"
# 実ペイロードの形を学習するため生 stdin を保存する(error_type のフィールド名/値が未確定なため。
# 次回実発火時にここを見れば正しいフィールド名で厳密化できる)。
printf '%s' "$payload" > "${STATE_DIR}/last-payload.json" 2>/dev/null || true
get() {
  printf '%s' "$payload" \
    | sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" \
    | head -n1
}
error_type="$(get error_type)"
session_id="$(get session_id)"

log "fired error_type='${error_type}' session='${session_id}'"

# 発火の絞り込みは settings.json の matcher(=rate_limit)が error type で既に行う(公式仕様)。
# stdin の error_type は実機で空のことを確認したため(2026-06-30)、ここで rate_limit を必須にすると
# matcher が選んだ本物の rate_limit を取りこぼす(=旧バグ。watcher が一度も起動しなかった原因)。
# よって「明示的に rate_limit 以外と判明したときだけ」スキップし、空/不明は matcher を信頼して継続する。
if [ -n "${error_type}" ] && [ "${error_type}" != "rate_limit" ]; then
  log "error_type='${error_type}' is explicitly non-rate_limit; skip"
  exit 0
fi

# --- 環境ゲート: WSL を積極検知できたときだけ動く(=クラウドでは no-op で無害) ---
is_wsl=0
[ -n "${WSL_DISTRO_NAME:-}" ] && is_wsl=1
grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null && is_wsl=1
if [ "${is_wsl}" -ne 1 ]; then
  log "non-WSL environment detected; no-op (safe on cloud/other)"
  exit 0
fi

# --- tmux 注入方式: claude が動いているペインを特定 ---
pane="${TMUX_PANE:-}"
if [ -z "${TMUX:-}" ] || [ -z "${pane}" ]; then
  log "not inside tmux (TMUX/TMUX_PANE empty); cannot inject keys. abort. (tmux 内で claude を起動してください)"
  exit 0
fi

# --- ①検知時刻を記録し、status-bar へ一瞬フラッシュ(out-of-band=入力欄には触れない) ---
# LLM が解除後も「まだ制限中」と誤認し、サブエージェント使用等の通常プロセスから逸脱する
# 事象への対策。検知時刻は状態ファイルへ記録し、②(resume-watcher.sh)が解除時の送信
# メッセージへ折り込むことで LLM にも確実に届ける(＝送信されるので文脈に入る)。
# 人間向けには tmux の status-bar へ一瞬フラッシュするだけ。tmux 入力欄(=②と共有する
# 繊細な状態)には一切書き込まないため、マーカー/行クリア/注入ロックといった調整が不要。
if [ "${CLAUDE_RL_ANNOUNCE_HIT:-1}" != "0" ]; then
  hit_time="$(date '+%Y-%m-%d %H:%M:%S')"
  # 状態ファイルへアトミックに記録(tmp→mv)。②が rl_hit_file 経由で読む。
  # 1行目=検知した session_id・2行目=検知時刻の2行形式で書く(Issue #240 D1)。
  # watcher は起動時に自分の session_id と照合し、不一致(別セッション/別エピソードが
  # 残した stale なファイル)なら検知時刻を破棄する。session_id が空でも時刻は残す
  # (照合をスキップ=後方互換)。②が消費・削除するため通常運用では残らない。
  hit_file="$(rl_hit_file "$pane")"
  if printf '%s\n%s\n' "$session_id" "$hit_time" > "${hit_file}.tmp" 2>/dev/null; then
    # mv 失敗時は .tmp を残さず後始末(状態ディレクトリを汚さない)。
    mv -f "${hit_file}.tmp" "$hit_file" 2>/dev/null || rm -f "${hit_file}.tmp" 2>/dev/null || true
  fi
  # status-bar へフラッシュ(入力欄には触れない・失敗しても無視・timeout ラップ)。
  rl_tmux display-message -t "$pane" "[rate-limit-hook] ${hit_time} にレートリミット検知。解除まで自動待機します。" 2>>"$LOG" || true
  log "recorded hit time ${hit_time} to ${hit_file}; flashed status-bar (pane=${pane})"
fi

# --- ウォッチャを切り離して起動(フックは即終了。出力は無視されるため fire-and-forget) ---
# transcript_path は watcher で未使用のため渡さない(Issue #240 C1)。
setsid bash "${HOOK_DIR}/resume-watcher.sh" "${pane}" "${session_id}" \
  >> "${LOG}" 2>&1 < /dev/null &
log "spawned resume-watcher for pane=${pane}"
exit 0
