# Claude Review MCP

Project-local MCP wrapper for read-only review calls through `claude -p`.

## Codex config

Add a server entry to `~/.codex/config.toml`:

```toml
[mcp_servers.claude_review]
command = "python3"
args = ["/home/hiras/ws_codex/review_system/.codex/mcp/claude_review/server.py"]
```

Restart Codex after changing MCP configuration.

The allowed workspace root defaults to the server startup directory. Set
`CLAUDE_REVIEW_MCP_WORKSPACE_ROOT` if the MCP host may launch the server from a
broader directory than the repository.

## Tools

- `claude_review`: runs `claude -p` in read-only plan mode. `model` accepts
  `opus` or `fable`; default is `opus`, and `opus` is passed as the fallback.
- `claude_review_status`: probes `claude --version`, `gh --version`, and local
  rate-limit state without running `claude -p`. Version probe output is not
  returned; status reports only bounded availability/failure categories. It
  also runs `claude --help` to report whether the installed CLI exposes every
  required capability.

Before a review, the wrapper runs the same capability preflight and requires
`-p`, `--model`, `--fallback-model`, `--safe-mode`, `--permission-mode`,
`--tools`, `--output-format`, and `--no-session-persistence`. An unsupported
CLI is rejected before GitHub context is fetched or a review prompt is sent.
Capability detection is intentional: the contract does not infer support from
a version string. Only options defined at the start of CLI help option lines
count; mentions in usage examples, descriptions, or removed/deprecated lines
do not satisfy the preflight. The parser tracks help section transitions:
`Options`, `Global options`, and `Flags` are definition sections, `Usage` keeps
compatibility with compact help, and every other or unknown heading is
non-defining until a supported option heading appears. This generic
fail-closed section rule avoids relying on a list of known negative headings.

When `pr_number` is provided, the wrapper reads PR metadata and diff with:

- `gh pr view <number> --json number,title,author,baseRefName,headRefName,url,body,files,commits`
- `gh pr diff <number>`

That context is appended to the prompt sent to Claude. If either command fails,
Claude is not called.

`pr_number` uses JSON Schema integer semantics and must be between `1` and the
GitHub GraphQL `Int` maximum `2147483647`, inclusive. Integral JSON numbers
such as `1.0` normalize to `1`; strings (including digit strings), booleans,
zero, negative, fractional, non-finite, and over-limit values are rejected
before state inspection, `gh`, or Claude subprocess execution.

If `workspace` is omitted, the wrapper uses the MCP server startup cwd. If it
is provided, the wrapper resolves it with realpath and only allows paths under
that startup cwd. Paths outside that tree return a tool error before any
`gh` or `claude` command is run.

## Safety

The wrapper passes:

```text
--model <opus|fable> --fallback-model opus --safe-mode --permission-mode plan --tools Read,Glob,Grep,LS --output-format json --no-session-persistence
```

It does not pass edit, write, shell, bypass, or accept-edits permissions.

Before calling `claude -p`, it checks only the wrapper-owned cooldown file:

- `${XDG_STATE_HOME:-~/.local/state}/claude-review-mcp/rate-limit.json`

The wrapper does not inspect Claude Code hook state such as
`~/.claude/rate-limit-recovery/last-payload.json`; that file can belong to a
different pane or session. If the wrapper's own file indicates a future reset
time, the wrapper returns a tool error without spending Claude quota. Otherwise,
rate-limit detection happens from the actual `claude -p` result, and any detected
cooldown is stored for the next call.

New cooldown files use state schema `1` as an exact JSON integer (JSON booleans,
floats, strings, non-finite constants, and future versions are not schema 1), with
`source: "claude_process_error"`. A schema-1 state with a future `reset_at`
blocks normally. A v0.1 legacy state has neither `schema_version` nor `source`;
when it has `error: "rate_limit"` and a future reset it also blocks, preventing
an upgrade from spending quota during a real legacy cooldown. Expired states
are safely ignored only after the state has been recognized as valid current or
legacy data. Malformed or unrecognized states fail closed and require operator
inspection or removal even when `reset_at` is absent, null, unknown, or expired.
Only a recognized rate-limit state without a known reset remains non-active,
matching the existing unknown-reset behavior.

## Claude response contract

Wrapper response contract `1.0` accepts exactly the following success
semantics while allowing additional metadata fields:

```json
{
  "type": "result",
  "subtype": "success",
  "is_error": false,
  "result": "non-empty review text"
}
```

Missing or unknown `type`/`subtype`, a non-false `is_error`, a non-empty
`error` field, malformed JSON, and a missing or empty `result` fail closed.
JSON object keys must be unique at every nesting depth, and non-standard JSON
constants (`NaN`, `Infinity`, and `-Infinity`) are rejected; parser last-wins
behavior is never used to resolve conflicting fields.
This intentionally rejects older result-only fixtures and unsupported future
envelope shapes instead of guessing that they mean success.

Free-form text in a validated success `result` is review content, not a
diagnostic channel. Consequently prose such as `rate_limit_error handling is
broken` or discussion of HTTP 429 is returned normally. Explicit structured
errors, stderr, failed-process diagnostics, and a whole-result legacy banner
are classified separately. A whole result consisting of bare `429` or a
canonical rate-limit banner (including matching outer quotes) is treated as a
diagnostic and fails closed.

The allowlist above is based on the repository fixtures and the verified
counterexamples recorded in the remediation plan. A live Claude success/error
sample has not been collected for this contract; that remains an owner-approved
gate. If a live envelope differs, extend the contract only after preserving a
redacted provenance fixture and reviewing the compatibility impact.

GitHub PR metadata and diffs are appended inside fenced blocks with explicit
instructions to treat them as untrusted review evidence, not as model
instructions.

The Claude capability preflight reads option definitions only from indented
rows under an exact `Options:`, `Global options:`, or `Flags:` heading. The
legacy compact `Usage:` layout is also accepted, but any other top-level line
ends that block. Headings with suffix text, unknown punctuation, examples,
descriptions, and unindented flag mentions do not satisfy the capability gate.

Capability preflight, version probes, `gh pr view`, `gh pr diff`, and the Claude
child process share one external diagnostic boundary. Exceptions and completed
nonzero exits emit only a fixed allowlisted stage label plus a bounded exit
status when one is a real JSON-independent integer. Raw stdout, stderr,
exception text, argv, ANSI content, and prompts are never copied to tool errors
or status details; truncating raw text is intentionally not considered safe.
The rate-limit classifier may inspect raw Claude diagnostics internally, but
the external response contains only the fixed rate-limit category and a
validated reset time when available. Completed nonzero diagnostics otherwise
use a fixed safe summary.

## Tests

Normal tests mock subprocess calls and do not spend Claude quota:

```bash
python3 -m py_compile .codex/mcp/claude_review/server.py
python3 -m unittest tests.unit.test_claude_review_mcp
```

Any live smoke test with `claude -p` is intentionally manual.
