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
#   - stdin で {session_id, transcript_path, cwd, hook_event_name, error_type} を受け取る。
#     リセット時刻は含まれない。
#
# 設計方針:
#   - 環境ゲートは「WSL を積極検知できたときだけ動く」許可リスト方式。
#     検知できない環境(クラウド/その他)は自動的に無害化される。
#   - 再開方式は tmux 端末注入(対話セッションのペインへ "続けて" を送出)。
set -u

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${HOME}/.claude/rate-limit-recovery"
mkdir -p "$STATE_DIR" 2>/dev/null || true
LOG="${STATE_DIR}/hook.log"

log() { printf '%s [hook] %s\n' "$(date '+%F %T')" "$*" >> "$LOG" 2>/dev/null || true; }

# --- stdin JSON を素朴に読む(標準ツールのみ・jq 非依存) ---
payload="$(cat)"
get() {
  printf '%s' "$payload" \
    | sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" \
    | head -n1
}
error_type="$(get error_type)"
session_id="$(get session_id)"
transcript_path="$(get transcript_path)"

log "fired error_type='${error_type}' session='${session_id}'"

# matcher で絞っていても保険として rate_limit 以外は無視
if [ "${error_type}" != "rate_limit" ]; then
  log "error_type is not rate_limit; skip"
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

# --- ウォッチャを切り離して起動(フックは即終了。出力は無視されるため fire-and-forget) ---
setsid bash "${HOOK_DIR}/resume-watcher.sh" "${pane}" "${session_id}" "${transcript_path}" \
  >> "${LOG}" 2>&1 < /dev/null &
log "spawned resume-watcher for pane=${pane}"
exit 0
