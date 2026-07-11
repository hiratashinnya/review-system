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

Every `claude_review` call automatically injects the shared review instructions
from:

- `.codex/mcp/claude_review/common_instructions.md`

Set `CLAUDE_REVIEW_MCP_COMMON_INSTRUCTIONS` to point at a different file if a
repo needs a different shared contract. Relative paths are resolved under the
workspace root.

## Tools

- `claude_review`: runs `claude -p` in read-only plan mode. `model` accepts
  `opus` or `fable`; default is `opus`, and `opus` is passed as the fallback.
- `claude_review_status`: checks `claude --version`, `gh --version`, and local
  rate-limit state without running `claude -p`; it also reports the common
  instructions path.

When `pr_number` is provided, the wrapper reads PR metadata and diff with:

- `gh pr view <number> --json number,title,author,baseRefName,headRefName,url,body,files,commits`
- `gh pr diff <number>`

That context is appended to the prompt sent to Claude. If either command fails,
Claude is not called.

If `workspace` is omitted, the wrapper uses the MCP server startup cwd. If it
is provided, the wrapper resolves it with realpath and only allows paths under
that startup cwd. Paths outside that tree return a tool error before any
`gh` or `claude` command is run.

## Safety

The wrapper passes:

```text
--model <opus|fable> --fallback-model opus --permission-mode plan --tools Read,Glob,Grep,LS --output-format json --no-session-persistence
```

It does not pass edit, write, shell, bypass, or accept-edits permissions.

Before calling `claude -p`, it checks only the wrapper-owned cooldown file:

- `${XDG_STATE_HOME:-~/.local/state}/claude-review-mcp/rate-limit.json`

The wrapper does not inspect Claude Code hook state such as
`~/.claude/rate-limit-recovery/last-payload.json`; that file can belong to a
different pane or session. If the wrapper's own file indicates a future reset
time from a `claude_process_error` entry, the wrapper returns a tool error
without spending Claude quota. Legacy or malformed state entries, including
entries without a parseable future `reset_at`, are not treated as blocks.
Otherwise, rate-limit detection happens from the actual `claude -p` process
result and only records strong error signals such as "you've hit your session
limit", "too many requests", `429`, or `rate_limit`. For successful JSON output,
the free-text `result` field is only treated as a rate-limit error when it
starts like an error message; ordinary successful review text that merely
discusses rate-limit handling is not stored as a cooldown.

GitHub PR metadata and diffs are appended inside fenced blocks with explicit
instructions to treat them as untrusted review evidence, not as model
instructions.

The common instructions file is trusted project configuration and is injected
before the caller's task-specific prompt. Callers should pass only the concrete
review request, such as the PR number, risk focus, and any owner-approved scope.

## Tests

Normal tests mock subprocess calls and do not spend Claude quota:

```bash
python3 -m py_compile .codex/mcp/claude_review/server.py
python3 -m unittest tests.unit.test_claude_review_mcp
```

Any live smoke test with `claude -p` is intentionally manual.
