# Codex project files

Codex-specific project functionality belongs under this directory, not under
`.claude/`.

- すべての説明・報告・質問は日本語で行う。ユーザーが明示的に別言語を指定した場合を除き、main thread・subagent・レビュー報告・PR コメントのいずれも日本語で統一する。
- `.codex/agents` contains Codex custom subagent TOML files converted from
  the repository source agents.
- Repository skills live in `.agents/skills`, which is Codex's documented
  repo-scoped skill discovery path.

Keep this directory writable in local checkouts so Codex helpers, hooks, agents,
and other project-scoped Codex files can be updated without mixing them into the
Claude Code configuration tree.

Rate-limit recovery is implemented as a project-local Codex `Stop` hook. Trust
the hook with `/hooks` in local tmux sessions. Set `CODEX_RL_CLOUD=1` or
`CODEX_RL_CLOUD_ENV=1` in cloud/hosted environments to make the hook a no-op.
