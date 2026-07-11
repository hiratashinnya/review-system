# Codex CLI hooks

Codex CLI supports lifecycle hooks. This repo registers two project-local hooks
in `.codex/hooks.json` (trust them with `/hooks` before relying on them):

1. A `PreToolUse` hook (`agent-command-gate.sh`) that mechanically enforces the
   `issue-implementer` / `pr-reviewer` push/merge boundary — the Codex counterpart
   of `.claude/hooks/agent-command-gate.sh`.
2. A `Stop` hook (`codex-rate-limit-*.sh`) for rate-limit recovery: it inspects a
   stopped Codex turn, runs `/status` when the pane looks rate-limited, parses the
   reported reset time, and resumes the thread after the reset. This hook is
   intentionally local/tmux-only; cloud and non-tmux environments are safe no-ops.

## PreToolUse command gate (issue-implementer / pr-reviewer boundary)

`agent-command-gate.sh` is the Codex port of the Claude `agent-command-gate.sh`.
Codex CLI (verified against `codex-cli` 0.142.5 / `openai/codex` main) exposes a
`PreToolUse` hook whose input JSON carries `agent_type`, `tool_name`, and
`tool_input`, and whose output can `deny` a tool call via
`hookSpecificOutput.permissionDecision = "deny"` with a non-empty
`permissionDecisionReason` — the same wire shape as Claude Code. Shell commands
arrive with `tool_name = "Bash"` and `tool_input.command` as a string.

The gate denies:

- `issue-implementer`: `git merge` / `gh pr merge` (push + open a PR, then stop).
- `pr-reviewer`: `git push` (review/comment/merge only, never push code).

Every other `agent_type` (including an absent one = the main context) is out of
scope and always allowed, matching the owner decision recorded for the Claude
gate (fail-closing on absent `agent_type` regressed the main context's own push).

### Known limits (tracked in Issue #129 / #181)

- Static inspection of the Bash command string — not a full sandbox. Arbitrary
  wrapper scripts, obfuscation, or code inside another interpreter can evade it.
- The hook only fires once it is trusted via `/hooks`, and it can be disabled by
  `requirements.toml` / `config.toml` hook policy.
- The exact `agent_type` string a spawned subagent reports should be confirmed by
  dogfooding (Claude issue #129 item 1 fail-open risk). Set
  `AGENT_COMMAND_GATE_DEBUG_PAYLOAD=/path/to/log` to record the received payload
  and decision (sensitive keys are redacted).

Treat the gate as one layer of defense together with the prompt-level discipline
in `issue-implementer.toml` / `pr-reviewer.toml`.

## Files

| File | Role |
|---|---|
| `.codex/hooks.json` | Registers the project-local `PreToolUse` and `Stop` hooks. Trust them with `/hooks` before relying on them. |
| `agent-command-gate.sh` | PreToolUse handler enforcing the issue-implementer/pr-reviewer push/merge boundary. Denies via `permissionDecision:deny`; allows by emitting nothing. |
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
- Injects only when the target pane still looks like this repo's Codex pane.
  The default accepts foreground command `codex`, and also accepts a `node`
  wrapper only when the tmux pane current path is inside this trusted repo.
- Does not inject while the pane tail looks busy, for example while an interrupt hint is visible.
- The preferred reset source is machine-readable `rate_limits.*.resets_at`
  captured from the Stop payload or session text. If that is unavailable, the
  watcher parses `/status`; if that also fails, it falls back to pane polling and
  then banner-clear detection.
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
| `CODEX_RL_PANE_CMD_RE` | `^codex$` | Foreground command regex allowed for injection. |
| `CODEX_RL_NODE_WRAPPER_RE` | `^node$` | Foreground command regex treated as a Codex node wrapper only when the pane path is inside this trusted repo. |
| `CODEX_RL_STARTUP_WAIT` | `30` | Seconds the watcher waits for the wrapper to `exec codex`. |
| `CODEX_RL_STATE_DIR` | `~/.codex/rate-limit-recovery` | Log and lock directory. |

Logs are written to `~/.codex/rate-limit-recovery/launcher.log` and
`~/.codex/rate-limit-recovery/watcher.log`. Stop hook diagnostics are written
to `~/.codex/rate-limit-recovery/stop-hook.log`, with the last raw Stop payload
stored as `last-stop-payload.json`.
