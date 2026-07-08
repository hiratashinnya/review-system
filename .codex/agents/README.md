# Codex custom agents

These project-scoped Codex custom agents are migrated from the repository source agent definitions.
Each `.toml` file defines one custom subagent with:

- `name`
- `description`
- `developer_instructions`

Source-platform-only front matter such as `tools` and `model` is intentionally omitted
because Codex custom agents inherit optional session settings unless explicitly
overridden.

All custom agents must explain, report, and ask questions in Japanese unless the
user explicitly requests another language.
