# Codex CLI rate-limit recovery

Codex CLI does not use the Claude `StopFailure(rate_limit)` hook described in
`.claude/hooks/README.md`, so this repo provides a tmux watcher under
`.codex/hooks` instead.

## Files

| File | Role |
|---|---|
| `codex-with-rate-limit-recovery.sh` | Starts the watcher for the current tmux pane, then `exec codex "$@"`. |
| `codex-rate-limit-watcher.sh` | Watches the Codex pane for rate-limit text, waits for the reset, and submits `continue` only when the pane is idle. |

## Usage

Run Codex through the wrapper inside tmux:

```bash
tmux new -s codex '/home/hiras/ws_claude/review-system/.codex/hooks/codex-with-rate-limit-recovery.sh'
```

Arguments are passed through:

```bash
.codex/hooks/codex-with-rate-limit-recovery.sh --model gpt-5
```

## Safety behavior

- Requires tmux. Outside tmux, the wrapper simply starts `codex` without recovery.
- Injects only when the target pane still has foreground command `codex` or `node`.
- Does not inject while the pane tail looks busy, for example while an interrupt hint is visible.
- If a reset time cannot be parsed, it waits for the rate-limit banner to disappear twice before injecting.
- Weekly limits are detected and skipped.
- Uses a per-pane lock so only one watcher controls a pane.

## Environment variables

| Variable | Default | Description |
|---|---:|---|
| `CODEX_RL_CONTINUE_MSG` | `continue` | Prompt sent after reset. |
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
`~/.codex/rate-limit-recovery/watcher.log`.
