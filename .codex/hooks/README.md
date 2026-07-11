# Codex CLI hooks

Codex CLI supports lifecycle hooks. This repo registers two project-local hooks
in `.codex/hooks.json` (trust them with `/hooks` before relying on them):

1. A `PreToolUse` hook (`agent-command-gate.sh`) that mechanically enforces the
   `issue-implementer` / `pr-reviewer` push/merge boundary — the Codex counterpart
   of `.claude/hooks/agent-command-gate.sh`.
2. A `Stop` hook (`codex-rate-limit-*.sh`) for rate-limit recovery. It now asks
   Codex's structured `account/rateLimits/read` app-server API whether the account
   is rate-limited and, if so, when it resets, then resumes the thread after the
   reset (Issue #195). Tmux pane text scraping (`/status` + banner regex) is kept
   only as a fallback for when that API is unavailable. This hook is intentionally
   local/tmux-only; cloud and non-tmux environments are safe no-ops.

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

### Dogfooding results (Issue #188, 2026-07-11, `codex-cli` 0.142.5)

Ran a real, non-interactive `codex exec` session (in a disposable local clone,
not this checkout) with `AGENT_COMMAND_GATE_DEBUG_PAYLOAD` set and
`--dangerously-bypass-hook-trust`, prompting the main agent to explicitly spawn
a subagent named `issue-implementer` (per `.codex/agents/issue-implementer.toml`)
to run `git status` then `git merge main`, and separately a subagent named
`pr-reviewer` (per `.codex/agents/pr-reviewer.toml`) to run `git log -1
--oneline` then `git push origin HEAD:refs/heads/<test-branch>`.

**Result: the premise the gate is built on did not hold in this exec-mode
test, in a more fundamental way than "the string differs".**

- The model's `spawn_agent` tool call with `agent_type: "issue-implementer"`
  (and separately `"pr-reviewer"`) was rejected by the Codex router itself:
  `codex_core::tools::router: error=unknown agent_type 'issue-implementer'`
  / `... 'pr-reviewer'` on stderr. The project-scoped `.codex/agents/*.toml`
  files exist, match the documented schema (`name` / `description` /
  `developer_instructions`), and the filename matches `name`, but this
  installed release did not accept those names as valid `agent_type` values
  for `spawn_agent` when driven through `codex exec`.
- After the rejection, the main agent silently fell back to spawning a plain
  (unnamed/default) subagent and asked it, via prompt text only, to
  role-play "as if" it were `issue-implementer` / `pr-reviewer`. So the real
  `agent_type` sent to any hook for that subagent's tool calls would have been
  absent/default, not `"issue-implementer"`/`"pr-reviewer"` — this gate's
  `role` would resolve to `"unknown"` (always allowed) for that session.
- Independently of the above, `AGENT_COMMAND_GATE_DEBUG_PAYLOAD` was **never
  written** during this session (the log file did not exist afterward), even
  with `--dangerously-bypass-hook-trust` set. The `PreToolUse` hook did not
  fire at all for the Bash calls the (fallback, unnamed) subagent made in this
  exec-mode run.
- The two commands that were supposed to probe the gate ran without it: the
  `git merge main` failed, but from a sandbox filesystem restriction
  (`cannot lock ref 'ORIG_HEAD' ... Read-only file system`), not from
  `permissionDecision:"deny"`. The `git push` to a disposable test branch
  actually **succeeded** (it landed in the local clone's `origin`, a
  filesystem path, not on GitHub — verified with `gh api .../branches/<name>`
  → 404 — and the stray local branch was deleted immediately after).

**Interpretation and residual risk**: this does not confirm the gate works as
designed, and it does not identify a corrected `agent_type` string to encode
either — it shows that, at least via `codex exec`, the named custom-agent path
this gate assumes (`SubagentHookContext.agent_type` == the `.codex/agents/*.toml`
`name`) was not reachable at all in this release; the runtime fell back to an
unnamed agent before any hook input existed to inspect. Whether the officially
documented, interactive usage path (`tmux new -s codex 'codex'`, trusting hooks
via `/hooks`, then spawning agents from an interactive session) resolves
`agent_type` correctly for these same custom names is still untested — running
that experiment safely requires a live tmux session and repeated
`--dangerously-bypass-*` style invocations, which is more invasive than this
follow-up investigation's scope covered. Treat the gate's `agent_type` match as
**unverified in practice** (not merely "not yet re-verified") until an
interactive-mode test is run, and continue to rely on the prompt-level
discipline in `issue-implementer.toml` / `pr-reviewer.toml` as the primary
control, not this hook.

### Root cause confirmed (Issue #192, 2026-07-11): untrusted, not a schema bug

The owner ran `/hooks` in a real interactive Codex CLI TUI session on this repo and
observed **`PreToolUse`: 0 hits, `Stop`: 1 hit** — direct, first-party evidence (not
`codex exec`-mode inference) that the `agent-command-gate.sh` `PreToolUse` hook has
never fired in normal, everyday use either, while the rate-limit `Stop` hook works.

**Investigation method.** Read the actual `openai/codex` source for this installed
version (`codex-cli` 0.142.5) via `gh api repos/openai/codex/contents/...`:

- `codex-rs/config/src/hook_config.rs` (`HooksFile`, `HookEventsToml`) — confirms the
  on-disk JSON schema this repo's `.codex/hooks.json` already uses is correct:
  `{"hooks": {"PreToolUse": [...], "Stop": [...]}}`, with `PreToolUse`/`Stop`/etc. as
  the literal (PascalCase) JSON keys via `#[serde(rename = "PreToolUse")]` and
  friends. **There is no schema mismatch** — this hypothesis from the issue turned
  out to be false.
- `codex-rs/hooks/src/lib.rs` (`hook_event_key_label`, `hook_key`) and
  `codex-rs/hooks/src/engine/discovery.rs` (`append_matcher_groups`) — show that each
  hook handler is keyed as `"{source_path}:{event_label}:{group_index}:{handler_index}"`
  (e.g. `.../hooks.json:stop:0:0`, matching this repo's existing
  `~/.codex/config.toml` entry) and is only added to the executable handler list when
  `enabled && (bypass_hook_trust || trust_status ∈ {Managed, Trusted})`. Trust is
  **per hook key, not per file** — adding a new hook to `hooks.json` does not extend
  the trust of hooks already present.

**Empirical, read-only confirmation in this exact repo.** `hooks/list` is a
query-only JSON-RPC method on `codex app-server` (the same one the interactive
`/hooks` TUI command calls internally — see `codex-rs/tui/src/hooks_rpc.rs`); trust
is only ever granted by the separate, mutating `config/batchWrite` method (also
in `hooks_rpc.rs`), which this investigation never invoked. Driving `codex
app-server --stdio` by hand with `initialize` → `initialized` → `hooks/list` against
this real repo path returned:

```
pre_tool_use:0:0  enabled=true  trustStatus=untrusted  hash=sha256:9fcd24e5...
stop:0:0          enabled=true  trustStatus=trusted    hash=sha256:43a2f93d...
```

`~/.codex/config.toml` was diffed before/after and is byte-identical — this call
made no changes, matching its read-only contract.

Note on scope: issue #192's acceptance criteria asked for a disposable-clone
verification. This step intentionally ran against the real repo/config instead,
because trust keys embed the hooks.json's absolute path — a disposable clone at a
different path cannot reproduce or answer *this* repo's actual trust state, and the
call used is read-only (no hook command execution, no `--dangerously-bypass-hook-trust`,
no config write), unlike the `git merge`/`git push` experiments in the #188
dogfooding that did warrant a disposable clone.

**Root cause**: the `Stop` hook was added on 2026-07-08 (commit `7d801c9`) and was
trusted at that time. The `PreToolUse` gate was added later, on 2026-07-11 (commit
`5982f73`, issue #181/PR #187), as a *new* hook key that has never been through the
(human-review) trust flow since. Codex's hook engine is fail-closed by design here:
an untrusted handler is simply never added to the executable list, so `0` hits is
the expected, correct behavior of the trust gate — not a bug in this repo's
`.codex/hooks.json`, and not a fail-open.

**Remediation is a one-time trust decision, not a code change** — `.codex/hooks.json`
needs no edit. Two mechanically equivalent ways to grant it:

- (A) **Recommended.** Open an interactive Codex CLI session in this repo
  (`tmux new -s codex 'codex'`), run `/hooks`, review the `PreToolUse` entry
  (`bash "$(git rev-parse --show-toplevel)/.codex/hooks/agent-command-gate.sh"`,
  matcher `Bash`), and trust it. This keeps the human-review step that Codex's hook
  trust model is designed around.
- (B) Not performed here. The identical effect can be produced non-interactively via
  the same `config/batchWrite` RPC `hooks_rpc.rs` uses
  (`hooks.state."<repo>/.codex/hooks.json:pre_tool_use:0:0".trusted_hash =
  "<current hash from hooks/list>"`). This PR does not do this: granting execution
  trust to a hook that runs on every future `Bash` tool call is a security-relevant
  decision this investigation treats as the owner's call, not something to grant
  unilaterally — same reasoning as the "no unilateral scope/schedule decisions"
  principle in this repo's `CLAUDE.md`. The trusted hash is tied to the hook's
  normalized content (event + matcher + command + timeout — see
  `command_hook_hash`/`NormalizedHookIdentity` in `discovery.rs`), so it will need to
  be re-trusted whenever this hook's registration in `hooks.json` changes.

This supersedes the "unverified in practice" framing of the Issue #188 dogfooding
above for the *interactive* path specifically: the interactive path's `agent_type`
resolution is still unverified, but it is now known to be moot until the
`PreToolUse` hook is trusted — until then it cannot fire at all, regardless of what
`agent_type` a spawned subagent would report.

## Files

| File | Role |
|---|---|
| `.codex/hooks.json` | Registers the project-local `PreToolUse` and `Stop` hooks. Trust them with `/hooks` before relying on them. |
| `agent-command-gate.sh` | PreToolUse handler enforcing the issue-implementer/pr-reviewer push/merge boundary. Denies via `permissionDecision:deny`; allows by emitting nothing. |
| `codex-rate-limit-query.py` | Structured rate-limit query helper (Issue #195). Drives `codex app-server --stdio` over JSON-RPC (`initialize` → `initialized` → `account/rateLimits/read`) and prints normalized `RL_*=value` lines (reached / reset epoch / window / used%). Standard-library only. Exit 0 = queried; non-zero = API unavailable (caller falls back to text). |
| `codex-rate-limit-stop-hook.sh` | Stop hook handler. Detects cloud/no-tmux no-op cases; queries the rate-limit API and, when reached, spawns the watcher with the API reset epoch (`--recover-once-epoch`). Falls back to `/status` + banner text only when the API is unavailable. |
| `codex-rate-limit-watcher.sh` | Waits until the reset time and submits `continue` only when the pane is idle. In `--recover-once-epoch` mode it sleeps to the API-provided epoch and re-confirms via the API that the limit cleared before injecting; it also still supports the legacy status-text (`--recover-once`) and continuous watcher modes. |
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
- The preferred detector and reset source is now the structured
  `account/rateLimits/read` app-server API (Issue #195): `rateLimitReachedType`
  (non-null = limited) and the binding window's `resetsAt`. Only when that API
  cannot be reached does the Stop hook fall back to `/status` text plus the
  banner regex, and the watcher to `/status` parsing / pane polling / banner-clear
  detection.
- Weekly / long limits are detected and skipped. Via the API this is any reached
  window longer than `CODEX_RL_MAX_AUTO_WINDOW_MINS` (default 360, i.e. the 5-hour
  window recovers but the weekly one does not); via the text fallback the weekly
  banner regex is skipped as before.
- Uses a per-pane lock so only one watcher controls a pane.

### Structured rate-limit API (Issue #195)

The Stop hook and watcher used to decide "are we rate-limited, and when do we
reset?" purely by regex-matching the rendered Codex tmux banner (Issue #182 had
to harden that regex against false-fires). That is inherently fragile — it
depends on exact banner wording, terminal wrapping, and scrollback.

Codex exposes the same information as structured data over its app-server
protocol. `codex-rate-limit-query.py` drives `codex app-server --stdio` with a
JSON-RPC handshake and calls `account/rateLimits/read`:

```
initialize                       (clientInfo)
initialized                      (notification)
account/rateLimits/read          (params: null)  -> GetAccountRateLimitsResponse
```

The response's `rateLimits` snapshot carries `primary`/`secondary` windows
(`usedPercent`, `windowDurationMins`, `resetsAt`), a top-level
`rateLimitReachedType` (an enum, or `null` when not limited), and `planType`.
Verified live against `codex-cli` 0.144.1 (the method is listed in the app-server
`ClientRequest.json`; the response shape matches
`v2/GetAccountRateLimitsResponse.json` from `codex app-server generate-json-schema`).
A real idle sample: `primary` = 5h window (`windowDurationMins:300`), `secondary`
= weekly (`10080`), `rateLimitReachedType: null`.

Detection rule (Issue #195 acceptance criterion 2): **`rateLimitReachedType`
non-null == rate limited**, and the *binding* window's `resetsAt` is used
verbatim as the reset time. The binding window is the exhausted (`usedPercent >=
100`) window that resets latest (so recovery waits for every maxed window); when
that window is longer than `CODEX_RL_MAX_AUTO_WINDOW_MINS` (weekly/long), auto-
recovery is skipped, mirroring the old weekly-skip. The Stop hook passes the
resolved epoch to the watcher via `--recover-once-epoch <pane> <epoch> <window>`;
the watcher sleeps until it and re-queries the API to confirm the limit cleared
before injecting `continue`.

**Replace vs. fallback (acceptance criterion 3).** The API is the *primary*
detector and is trusted fully when it answers (it is the account's own
authoritative state, not a screen guess). The existing text/regex path is
**kept as a fallback**, reached only when the API cannot be queried: `codex`
not on `PATH`, not logged in, an app-server error/timeout, or an older Codex
release without the method. This is the conservative choice — it strictly adds
reliability without removing the previously tested safety net, and matches this
codebase's defensive "never guess-fire, degrade gracefully" style. Disable the
API path entirely with `CODEX_RL_API_CHECK=0` (forces the legacy text behavior).

**Known residual trade-offs**, flagged rather than resolved unilaterally:

- Per-Stop cost. Each eligible Stop may spawn a short-lived `codex app-server`
  process (~1–2s). This is bounded by the existing per-pane cooldown
  (`CODEX_RL_STATUS_COOLDOWN`, default 60s) so it cannot fire on every turn, and
  the push-style `AccountRateLimitsUpdatedNotification` (which could remove
  polling entirely) is intentionally left for a future change to keep this PR
  focused on the read API.
- Account/session identity. The API reports the state of the logged-in account
  for `~/.codex`, which is assumed to be the same account driving the tmux pane.
  If a pane runs Codex under a different login, the API answer could disagree
  with that pane's banner; the fallback still covers the API-unavailable case.

### Rate-limit banner detection (Issue #182) — fallback path

As of Issue #195 the regex below is the **fallback** detector, used only when
the structured API above is unavailable. The regex previously used to decide
"does this pane look rate-limited"
(`RATE_LIMIT_RE`) was a single broad `OR` of loose terms (bare `rate limit`,
`usage limit`, `too many requests`, ...). Those words are common in ordinary
coding conversation (e.g. implementing a rate limiter, or pasting an
unrelated HTTP 429 log), so the gate could false-fire and, in the worst case,
end with an **unattended `continue` being injected into the pane** — see
Issue #182 for the audit finding.

Both `codex-rate-limit-stop-hook.sh` and `codex-rate-limit-watcher.sh` now
require **two independent regexes to both match** before treating pane/status
text as a real rate-limit banner:

- `RATE_LIMIT_PHRASE_RE` — a limit-hit phrase (`hit`/`reached`/`exceeded`
  `your`/`the` `<rate|usage|session|request|5-hour|weekly|daily|account>`
  `limit`, or `<...> limit reached/exceeded`, or `429` + `too many requests`).
- `RATE_LIMIT_RESET_RE` — a reset/retry cue (`resets HH:MMam/pm`, `resets
  <weekday>`, `try again in <N>`, `retry in/after <N>`).

A real captured banner always pairs the two, e.g. `You've hit your session
limit · resets 10:50pm (Asia/Tokyo)` (real Stop payload captured in PR #66).
Neither alone is sufficient. Both halves are overridable via
`CODEX_RL_RATE_LIMIT_PHRASE_RE` / `CODEX_RL_RATE_LIMIT_RESET_RE` (see table
below) for local tuning without editing the scripts.

As one more confirmation step before the riskier "no parseable reset time"
fallback (waiting for the banner to clear and then injecting blind) is armed,
the watcher now also requires the AND-matched banner to reappear on **2
consecutive polls** (`wait_for_reset_and_recover`'s acquire loop, and the
legacy continuous watch loop) before trusting it, instead of acting on a
single snapshot. This does not apply to the reset-time-known fast path (the
sleep-until-`resets_at`-then-inject flow already documented above): requiring
banner presence again right before injection would reintroduce the "banner
already cleared after reset = looks like it never happened" regression fixed
in PR #66, so injection there stays gated on `is_working` only, as before.

Both scripts can be `source`d with `CODEX_RL_SOURCE_FOR_TEST=1` to unit-test
the text-matching functions (`has_rate_limit_text`, `text_has_rate_limit_
banner`, `parse_reset_from_text`, ...) directly against sample text without
running the tmux-dependent hook/watcher body — see
`tests/unit/test_codex_rate_limit_banner_regex.py`.

**Known residual trade-off**: the AND requirement trades recall for
precision. A genuine rate-limit banner that never shows any reset/retry cue
(e.g. a plan that only says "upgrade to continue" with no time information)
will no longer arm automatic recovery — but automatic recovery could not
usefully act on that case anyway (there is nothing to wait for), so this is
treated as an acceptable, conservative trade-off consistent with this
codebase's existing "never guess-fire" design (see PR #86). Conversely, a
message that coincidentally contains both a limit-hit phrase and an unrelated
reset-time-shaped phrase (e.g. "we hit the request limit for our internal
rate limiter, resets at 9am") could still combine to a false positive; this
residual risk was flagged to the repo owner in Issue #182's implementation
report rather than resolved unilaterally, since further tightening trades
away more recall.

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
| `CODEX_RL_RATE_LIMIT_PHRASE_RE` | see script | Limit-hit phrase half of the AND banner regex (Issue #182; fallback path). |
| `CODEX_RL_RATE_LIMIT_RESET_RE` | see script | Reset/retry-cue half of the AND banner regex (Issue #182; fallback path). |
| `CODEX_RL_API_CHECK` | `1` | When truthy, query the structured `account/rateLimits/read` API first (Issue #195). Set `0` to force the legacy text/regex path only. |
| `CODEX_RL_API_TIMEOUT` | `12` | Seconds `codex-rate-limit-query.py` waits for the rateLimits response before giving up (→ text fallback). |
| `CODEX_RL_MAX_AUTO_WINDOW_MINS` | `360` | Reached windows longer than this (e.g. the weekly 10080) are treated as long/weekly and skipped for auto-recovery. |
| `CODEX_RL_APP_SERVER_CMD` | `codex app-server --stdio` | Command the query helper runs to launch the app-server (shell-split). |
| `CODEX_RL_QUERY_HELPER` | `<hook dir>/codex-rate-limit-query.py` | Path to the query helper the hooks invoke. |
| `CODEX_RL_RESET_CONFIRM_INTERVAL` | `30` | Seconds between post-reset API confirmations (`--recover-once-epoch`) that the limit cleared. |
| `CODEX_RL_RESET_CONFIRM_MAX` | `5` | Max post-reset API confirmation attempts before injecting anyway. |
| `CODEX_RL_QUERY_CMD` | unset | Test-only override: eval'd instead of the helper; must print `RL_*=value` lines. |

Logs are written to `~/.codex/rate-limit-recovery/launcher.log` and
`~/.codex/rate-limit-recovery/watcher.log`. Stop hook diagnostics are written
to `~/.codex/rate-limit-recovery/stop-hook.log`, with the last raw Stop payload
stored as `last-stop-payload.json`.
