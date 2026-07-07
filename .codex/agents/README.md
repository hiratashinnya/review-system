# Codex custom agents

These project-scoped Codex custom agents are converted from `.claude/agents`.
Each `.toml` file defines one custom subagent with:

- `name`
- `description`
- `developer_instructions`

Claude-only front matter such as `tools` and `model` is intentionally omitted
because Codex custom agents inherit optional session settings unless explicitly
overridden.
