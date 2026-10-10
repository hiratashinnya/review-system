# Codex CLI hooks

Codex CLI supports lifecycle hooks. This repo registers project-local hooks
in `.codex/hooks.json` (trust them with `/hooks` before relying on them):

1. A `PreToolUse` hook (`agent-command-gate.sh`) that mechanically enforces the
   `issue-implementer` / `pr-reviewer` push/merge boundary — the Codex counterpart
   of `.claude/hooks/agent-command-gate.sh`.
2. Dispatch/merge `PreToolUse` hooks for Issue-start and PR-merge policy.
3. A Bash `PreToolUse` hook (`codex-launch-intent-gate.sh`) that shape-checks the
   exact minimal-input supervisor command before the authoritative runtime checks.

## PreToolUse command gate (issue-implementer / pr-reviewer boundary)

Issue #452 で Codex workspace-binding transport と all-tool binding hook は退役した。
`spawn_agent` の implementer/fixer は issue-start gate が常時
`ISSUE_START_TRANSPORT_UNAVAILABLE` で拒否し、正規経路は repo supervisor の別 process に限る。

### Codex supervisor launch-intent gate

親AIが手入力できる正規commandは次の4値だけである。

```text
python3 -m issue_start.codex_supervisor (run|resume) --issue N --role ROLE --change-plan-id ID [--fixer-round N]
```

repository/workspace/branch/OID/task key/handoff/protected plan/model/effort/executable/runtime/profile/promptは
`managed-entrypoints-v2.json`、host main worktreeのprivateな
`tmp/_codex_control/change-plans/<ID>.json`、canonical worktree ledger、live Gitから同じgeneratorが
導出する。owner approvalはhost control-planeの運用記録であり、個人の暗号学的な本人証明とは称さない。
inner agentがchild workspaceへ置いた同名planはauthorityにならない。

production stateはowner承認後に`python3 -m issue_start.codex_launch_control issue`で発行する。このCLIは
PreToolUse launch hookの対象ではないcontrol-plane専用入口で、登録済み`.worktrees/*`とcapture済み構造化sourceを
受ける。worktree作成とGitHub captureはcaller責務であり、issuerはnetwork/model/Claudeを使用しない。
ledger pending→sources→ledger complete→planの順で公開し、partial stateはlaunchが拒否、同一要求retryが修復する。

network denyのinner processでもACを読めるよう、change planはprivate control root内の構造化Issue/AC
snapshotについてpath、SHA-256、取得元・取得時刻・取得主体を保持する。fixerは構造化karte snapshotの
exact roundとopen finding IDも必須である。generatorは同じFDで検査・読取したsnapshotのdigestと意味を
照合してpromptへ展開し、URLだけをtask promptとはみなさない。private rootはcurrent-user所有0700、
fileは0600/single-linkを要求し、各componentをdirfd/openat/O_NOFOLLOWで辿る。PreToolUseは実行前に
同generatorをdry-runし、型・値域・role/round/Issue/AC/karte整合、host approval record、canonical
ledger/live Git、manifestのmodel/effort/profile/template/path、実行ファイルのowner/mode/digest/versionを
fail-close検査する。raw commandと先頭に`rtk`を1個置く形だけが正規形であり、fieldの順序・個数も
上記どおり固定する。追加・重複field、compound command、`env`・assignment・別wrapperによる変形は
拒否する。無関係なBashとdirect `codex exec`はこのhookの対象外である。

このhookは早期フィードバックでありauthority/receiptではない。supervisor自身が4入力以外を受け取らず、
process起動直前に同じrequestからintentを再生成してplan/manifest/Issue/karte/ledger/role/executable/Gitと
実command/profileを再照合する。change-planのowner側永続化とcanonical ledger entryの発行はhost control
planeの責務で、同entryへimmutable intent digestとattemptを追記し、第2entryを作らない。
snapshot/change-planを作るcontrol planeはmodel-originated write surfaceの外に置かなければならない。

任意のshell wrapperや別interpreterに隠したdirect Codex起動をPreToolUseで完全封鎖することは範囲外である。
それを行うには全commandのshell解析・pre-exec brokerへ戻る必要があるため、既知の残余リスクとして受容する。

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

### Checking whether the hook actually fired (Issue #192)

Issue #192 (see the "Root cause confirmed" section below) found that trust is
granted per hook key, not per file. A key includes the absolute `hooks.json`
path, event, matcher-group index, and handler index, so moving a checkout gives
the hook a different key. There was previously **no way to
confirm the `PreToolUse` gate had actually executed** short of setting the
opt-in `AGENT_COMMAND_GATE_DEBUG_PAYLOAD` beforehand — which is easy to forget
to set *before* the moment you actually want to check.

To close that gap, `agent-command-gate.sh` now writes a minimal, **always-on**
trace line every time it runs, independent of `AGENT_COMMAND_GATE_DEBUG_PAYLOAD`:

**Look at `~/.codex/agent-command-gate-trace.log`.** Each line is one JSON
record: `ts` (UTC timestamp), `agent_type` (as received; `null` if absent or
the payload itself wasn't valid JSON), `tool_name`, and `decision`
(`"allow"`/`"deny"`). For example:

```json
{"agent_type": "issue-implementer", "decision": "allow", "tool_name": "Bash", "ts": "2026-07-11T06:03:16+00:00"}
```

If this file has fresh entries after you run a Bash/git/gh command, the
`PreToolUse` hook fired for that call (the current key is trusted and Codex invoked it) —
this is the direct signal Issue #192 was missing. If the file is empty or
stale, the hook did not run (most likely: its current key was not trusted via
`/hooks`, or the checkout moved to a path with a different key).

Design notes:

- **On by default, not opt-in.** An opt-in-only design would have the same
  "forgot to set the env var before the session I actually wanted to check"
  problem this issue set out to fix, so the default is on.
- **No sensitive or bulky content.** Only the four fields above are recorded —
  never the command text or the raw payload (that remains
  `AGENT_COMMAND_GATE_DEBUG_PAYLOAD`'s opt-in job, redacted).
- **Bounded size.** The file rotates to a single `.1` backup once it exceeds
  ~1&nbsp;MB (no unbounded growth); no external log rotation setup is required.
- **Overridable / disableable.** Set `AGENT_COMMAND_GATE_TRACE_LOG=/other/path`
  to redirect it, or `AGENT_COMMAND_GATE_TRACE_LOG=` (empty) to turn it off
  entirely (this is also how the test suite avoids writing to the real
  `~/.codex/` during `python3 -m unittest`).
- **Security logic is unchanged.** This trace is purely diagnostic; it does not
  read, and cannot influence, the allow/deny decision.
- The Claude counterpart (`.claude/hooks/agent-command-gate.sh`) writes the
  same shape of record to `~/.claude/agent-command-gate-trace.log` for parity.

### 退役transportの調査記録: Codex 0.146.0 Issue-start tool name

The official Codex manual and `rust-v0.146.0` source define `spawn_agent` as
the canonical hook tool name and `Agent` as its matcher-only compatibility
alias. A trusted, interactive Codex CLI 0.146.0 run in a disposable clone
observed `tool_name: "collaborationspawn_agent"` on PreToolUse stdin for the UI
`collaboration.spawn_agent` call. The Issue-start matcher therefore catches the
known `spawn_agent`, `Agent`, and `collaborationspawn_agent` spellings. After
Issue #452, known Codex implementer/fixer calls are denied before manifest or
payload parsing; this record does not define an available Codex binding transport.

Claude Code 2.1.221 Pro produced a separate compatibility case: its configured
`Task` matcher caught a real Agent tool call whose PreToolUse `tool_name` was
`Agent` and whose input retained the Claude `subagent_type` / `prompt` /
`description` shape. The manifest therefore accepts `Agent` only on the Claude
transport when `subagent_type` and `prompt` are present and Codex
`agent_type` / `message` / `task_name` fields are absent. A Codex-shaped
`Agent` payload and any ambiguous/mixed/similar name remain fail-closed.

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

**Remediation for this key is a trust decision, not a code change** —
`.codex/hooks.json` needs no edit. Two mechanically equivalent ways to grant it:

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

### A moved checkout silently invalidates hook trust (Issue #530, 2026-09-30)

Issue #530 confirmed that the hook key includes the absolute `hooks.json` path.
When this repository moved to a different path, all six registered hooks had
new keys with no matching `[hooks.state."<key>"]` entry in
`~/.codex/config.toml`. `hooks/list` reported them as `untrusted`, and Codex
silently omitted them from execution. Codex does not warn when this happens.

Run `python3 -m codex_hook_trust check` from the repository to list untrusted
hooks. The command is read-only: it does not change `~/.codex/config.toml`.
Tests may substitute the Codex executable with `--codex /path/to/fake-codex` or
the `CODEX_HOOK_TRUST_CODEX` environment variable.

Before trusting individual hooks, first verify that Codex trusts the project
directory itself. In `~/.codex/config.toml`, the current repository's absolute
path should have a project entry like this:

```toml
[projects."<absolute repository path>"]
trust_level = "trusted"
```

If `hooks/list` reports zero hooks or fewer hooks than `.codex/hooks.json`
defines, trust the project in Codex first, then rerun the check. Individual
hook trust cannot restore registrations that Codex has not discovered.

Recovery options are to review and trust each hook in an interactive `/hooks`
session, or to register the `currentHash` from `hooks/list` under its exact key:

```toml
[hooks.state."<key>"]
trusted_hash = "<currentHash>"
```

The key is path-specific, and `currentHash` represents the hook registration.
Repeat the trust check after moving a checkout or changing a hook registration.

## Files

| File | Role |
|---|---|
| `.codex/hooks.json` | Registers the project-local `PreToolUse` hooks. Trust them with `/hooks` before relying on them. |
| `agent-command-gate.sh` | PreToolUse handler enforcing the issue-implementer/pr-reviewer push/merge boundary. Denies via `permissionDecision:deny`; allows by emitting nothing. |
| `issue-start-gate.sh` | PreToolUse handler registered in `.codex/hooks.json` for the `spawn_agent` / `Agent` / `collaborationspawn_agent` matcher. Thin wrapper over the shared `issue_start` core (see `.ai/Individually-managed-lists.md` hook table row 3). |
| `codex-launch-intent-gate.sh` | Bash PreToolUse handler. Resolves the main worktree from `--git-common-dir`, then runs `python3 -m issue_start.codex_launch_intent hook` to shape-check the exact minimal-input supervisor command (see "Codex supervisor launch-intent gate"). Early feedback only, not the authority; unrelated Bash and direct `codex exec` are out of scope. |

## Removed: Codex rate-limit auto-recovery (Issue #569)

Codex is no longer used as an interactive main context; it runs as a sub-executor via
`codex exec`. The tmux-pane `Stop` hook that injected `continue` after a rate-limit reset
(the rate-limit Stop-hook scripts and the legacy launcher wrapper) was therefore removed, along with
its `Stop` entry in `.codex/hooks.json`, the `CODEX_RL_*` variables and their tests. It had
already stopped recovering in practice (Issue #508, merged into #569). If `codex exec` fails
on a rate limit, re-submit with the same model and configuration; do not downgrade.
