# Codex project files

This directory contains project-scoped Codex configuration and customizations.

- すべての説明・報告・質問は日本語で行う。ユーザーが明示的に別言語を指定した場合を除き、main thread・subagent・レビュー報告・PR コメントのいずれも日本語で統一する。
- `.codex/agents` contains Codex custom subagent TOML files converted from
  the repository source agents.
- Repository skills live in `.agents/skills`, which is Codex's documented
  repo-scoped skill discovery path.

Keep Codex-specific files here instead of placing them under another assistant-specific directory.
