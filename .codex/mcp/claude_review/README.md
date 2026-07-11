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

## Tools

- `claude_review`: runs `claude -p` in read-only plan mode. `model` accepts
  `opus` or `fable`; default is `opus`, and `opus` is passed as the fallback.
- `claude_review_status`: checks `claude --version`, `gh --version`, and local
  rate-limit state without running `claude -p`.

When `pr_number` is provided, the wrapper reads PR metadata and diff with:

- `gh pr view <number> --json number,title,author,baseRefName,headRefName,url,body,files,commits`
- `gh pr diff <number>`

That context is appended to the prompt sent to Claude. If either command fails,
Claude is not called.

## Safety

The wrapper passes:

```text
--permission-mode plan --tools Read,Glob,Grep,LS
```

It does not pass edit, write, shell, bypass, or accept-edits permissions.

Before calling `claude -p`, it checks:

- `${XDG_STATE_HOME:-~/.local/state}/claude-review-mcp/rate-limit.json`
- `~/.claude/rate-limit-recovery/last-payload.json`

If either file indicates a future reset time, the wrapper returns a tool error
without spending Claude quota.

## Tests

Normal tests mock subprocess calls and do not spend Claude quota:

```bash
python3 -m py_compile .codex/mcp/claude_review/server.py
python3 -m unittest tests.unit.test_claude_review_mcp
```

Any live smoke test with `claude -p` is intentionally manual.
