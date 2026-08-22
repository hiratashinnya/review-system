---
name: issue-pipeline
description: 複数のオープン GitHub Issue を実装→PR→レビュー→マージ→クローズで1件ずつ処理するオーケストレータ。処置順の確定、issue-implementer/pr-reviewer サブエージェントへの委譲（model は bloom-model-tier、レビュー model はリスクベース）、オーナーとの意思決定、進捗管理を扱う。Issue 処理を end-to-end で進めるときに使う。doc-system-v2 ノード著作には使わない（spec-pipeline / impl-design-pipeline を使う）。
---

## 共通本文

この資産の共通本文は [issue-pipeline の共通本文](../../../.ai/skills/issue-pipeline/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex CLI 固有の dispatch 契約

- GitHub の Issue/PR 操作は connector-first とし、利用可能な GitHub connector/tool を先に使い、不足する機能だけ `gh` CLI で補う。
- Issue 実装 dispatch の `task_name` は exact `issue_<Issue番号>` とする。PreToolUse の managed gate は平文 task name、payload/cwd、git worktree、GitHub origin から repository／Issue を再束縛し、Codex の暗号化 message は binding に使わない。
- Codex の `spawn_agent` には Claude の `isolation` パラメータがない。主文脈と作業ツリーを共有するため、実装中に主文脈で branch 操作をしない。hook 無効 harness や direct shell は保護済み経路として扱わない。
- 実装担当は `.codex/agents/issue-implementer.toml`、レビュー担当は `.codex/agents/pr-reviewer.toml` の developer_instructions にある恒常契約を適用する。Codex 側の push／merge 境界はプロンプト規律で担保し、Claude の hook 機械ゲートを持ち込まない。
- 実装の model／effort は Bloom ルーブリック、初回レビューの effort は共通本文のリスク信号で選ぶ。再レビューは既定 `high`、レート制限を理由に降格しない。
