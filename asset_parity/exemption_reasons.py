"""Reasons transcribed from documented non-mirror decisions."""

_ENV_DEPENDENT = (
    "agy 直接実行はローカル CLI／Windows Credential Manager 認証依存のため非移植"
    "（.claude/tailoring-registry.md）"
)
_ISSUE_PIPELINE_AGENT_COPILOT = (
    "Issue工程ロールは gh CLI／Claude Code フック（agent-command-gate.sh）／"
    "Task 委譲／bloom-model-tier に依存するため Copilot（.github/）には等価物なし"
    "（.claude/tailoring-registry.md）"
)
_ISSUE_FIXER_COPILOT = (
    "Issue 運用パイプラインの是正専任ロール（Issue #308）。親パイプラインと同じ理由で Copilot"
    "（.github/）には等価物が無く、さらに karte CLI と PreToolUse フック（agent-command-gate.sh の"
    "GATED_ROLES / PYTHON_MODULES_BY_ROLE）の両方に依存するため Copilot 側では契約が成立しない"
    "（.claude/tailoring-registry.md）"
)
_ISSUE_PIPELINE_CODEX_RETIRED = "Issue #603 / #538: Codex は execution actor。agent は archive し、Claude Code role を正本とする（.claude/tailoring-registry.md / .ai/rationale/issue-pipeline.md）"
_ISSUE_PIPELINE_SKILL_RETIRED = "Issue #603 / #538: Codex は main context ではない。skill を archive し、Copilot 差分は Issue #468 で追跡（.claude/tailoring-registry.md / .ai/rationale/issue-pipeline.md）"
_CODEX_REVIEW_ENV = (
    "codex CLI／ChatGPT ログイン／~/.codex/sessions に依存する Linux/WSL 専用の第二意見"
    "レビュー委譲。全外部ツリー非移植（Codex CLI を Codex 自身の skill から呼ぶ再帰性が不自然・"
    "Copilot にも等価物なし）（.claude/tailoring-registry.md）"
)
_GH_CREATE_ISSUE_COPILOT = (
    "ユーザー指定が Codex と Claude Code の2環境に限定された明示スコープのため Copilot 版は"
    "作らない。将来 Copilot を対象化する時に形式・tool・対話境界を再評価する"
    "（.claude/tailoring-registry.md）"
)
_GH_CREATE_ISSUE_AGENT_CLAUDE_ONLY = (
    "Claude Code 専用のサブエージェント（Issue #632）。SubagentStop フックによる"
    "チャット直送が Claude Code の hook 機構に依存するため他 PF へは作らない。"
    "Codex は .agents/skills の wrapper が共通本文を直接実行する（.claude/tailoring-registry.md）"
)
_SILENT_FAILURE_DIAGNOSIS_COPILOT = (
    "user-invocable: false の共有リファレンスだが Copilot へは非移植（オーナー再確定 2026-10-12）。"
    "copilot-instructions.md へも本文を展開しないため inlined には当たらない"
    "（.claude/tailoring-registry.md）"
)
