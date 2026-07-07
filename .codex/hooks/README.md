# Codex CLI rate-limit recovery

Codex CLI supports lifecycle hooks. This repo uses a `Stop` hook to inspect a
stopped Codex turn, run `/status` when the pane looks rate-limited, parse the
reported reset time, and resume the thread after the reset.

The hook is intentionally local/tmux-only. Cloud and non-tmux environments are
safe no-ops.

## Files

| File | Role |
|---|---|
| `.codex/hooks.json` | Registers the project-local `Stop` hook. Trust it with `/hooks` before relying on it. |
| `codex-rate-limit-stop-hook.sh` | Stop hook handler. Detects cloud/no-tmux no-op cases, sends `/status`, captures the status output, and starts the one-shot watcher. |
| `codex-rate-limit-watcher.sh` | Waits until the parsed reset time and submits `continue` only when the pane is idle. It also still supports the legacy continuous watcher mode. |
| `codex-with-rate-limit-recovery.sh` | Legacy wrapper that starts the continuous watcher for the current tmux pane, then `exec codex "$@"`. |

## Usage

Use normal Codex CLI inside tmux from this trusted repo. On first use, open
`/hooks` and trust the project-local Stop hook.

```bash
tmux new -s codex 'codex'
```

The wrapper remains available as a fallback if you want pane scanning even
without hooks:

```bash
.codex/hooks/codex-with-rate-limit-recovery.sh --model gpt-5
```

## Safety behavior

- Requires tmux. Without tmux, the hook exits without starting background work.
- Cloud environments are explicit no-ops when `CODEX_RL_CLOUD=1`,
  `CODEX_RL_CLOUD_ENV=1`, `CODEX_CLOUD=1`, `CODEX_CLOUD_ENVIRONMENT_ID`, or
  `CODEX_ENVIRONMENT_ID` is set.
- The Stop hook does not run `/status` after every turn by default. It first
  checks the Stop payload and pane tail for rate-limit text. Set
  `CODEX_RL_STATUS_ON_EVERY_STOP=1` to force `/status` on every Stop event.
- Injects only when the target pane still has foreground command `codex` or `node`.
- Does not inject while the pane tail looks busy, for example while an interrupt hint is visible.
- The preferred reset source is `/status`. If a reset time cannot be parsed from
  status output, the watcher falls back to pane polling and then banner-clear
  detection.
- Weekly limits are detected and skipped.
- Uses a per-pane lock so only one watcher controls a pane.

## Environment variables

| Variable | Default | Description |
|---|---:|---|
| `CODEX_RL_CONTINUE_MSG` | `continue` | Prompt sent after reset. |
| `CODEX_RL_CLOUD` | unset | Truthy value disables recovery in cloud/hosted environments. |
| `CODEX_RL_CLOUD_ENV` | unset | Same as `CODEX_RL_CLOUD`; useful when a cloud setup wants a project-specific flag. |
| `CODEX_RL_STATUS_ON_EVERY_STOP` | `0` | When truthy, the Stop hook sends `/status` on every Stop event. Default only does so when rate-limit text is visible. |
| `CODEX_RL_STATUS_COOLDOWN` | `60` | Minimum seconds between `/status` requests per tmux pane. Prevents `/status` from recursively triggering more Stop-hook status requests. |
| `CODEX_RL_STATUS_WAIT` | `3` | Seconds to wait after sending `/status` before capturing the pane. |
| `CODEX_RL_STATUS_CAPTURE_LINES` | `140` | Number of pane lines captured after `/status`. |
| `CODEX_RL_SCAN_INTERVAL` | `20` | Seconds between idle scans for a rate-limit banner. |
| `CODEX_RL_RESET_POLL_INTERVAL` | `15` | Seconds between reset-time parse retries. |
| `CODEX_RL_RESET_POLL_MAX` | `40` | Reset-time parse retry count. |
| `CODEX_RL_BANNER_POLL_INTERVAL` | `30` | Seconds between banner-clear checks when no reset time is parsed. |
| `CODEX_RL_BANNER_POLL_MAX` | `720` | Banner-clear check cap. |
| `CODEX_RL_MARGIN` | `30` | Extra seconds after the parsed reset time before submitting. |
| `CODEX_RL_MAX_ATTEMPTS` | `1` | Injection attempts per recovery. |
| `CODEX_RL_RETRY_BACKOFF` | `300` | Backoff seconds multiplied by attempt number. |
| `CODEX_RL_VERIFY_WAIT` | `20` | Seconds to wait after injection before checking activity. |
| `CODEX_RL_PANE_CMD_RE` | `^(codex\|node)$` | Foreground command regex allowed for injection. |
| `CODEX_RL_STARTUP_WAIT` | `30` | Seconds the watcher waits for the wrapper to `exec codex`. |
| `CODEX_RL_STATE_DIR` | `~/.codex/rate-limit-recovery` | Log and lock directory. |

Logs are written to `~/.codex/rate-limit-recovery/launcher.log` and
`~/.codex/rate-limit-recovery/watcher.log`. Stop hook diagnostics are written
to `~/.codex/rate-limit-recovery/stop-hook.log`, with the last raw Stop payload
stored as `last-stop-payload.json`.
