# Codex project files

Codex-specific project functionality belongs under this directory, not under
`.claude/`.

- すべての説明・報告・質問は日本語で行う。ユーザーが明示的に別言語を指定した場合を除き、main thread・subagent・レビュー報告・PR コメントのいずれも日本語で統一する。
- `.codex/agents` contains Codex custom subagent TOML files converted from
  the repository source agents.
- `.codex/rules/*.rules` contains project-native command execution policy.
  Native rules deny direct merge command prefixes; shared hooks inspect global
  options, wrappers, APIs, and inspectable indirect forms for every role.
- Repository skills live in `.agents/skills`, which is Codex's documented
  repo-scoped skill discovery path.

Keep this directory writable in local checkouts so Codex helpers, hooks, agents,
and other project-scoped Codex files can be updated without mixing them into the
Claude Code configuration tree.
