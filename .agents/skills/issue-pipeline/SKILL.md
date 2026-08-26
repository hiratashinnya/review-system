---
name: issue-pipeline
description: 複数のオープン GitHub Issue を実装→PR→レビュー→マージ→クローズで1件ずつ処理するオーケストレータ。処置順の確定、issue-implementer/pr-reviewer サブエージェントへの委譲（model は bloom-model-tier、レビュー model はリスクベース）、オーナーとの意思決定、進捗管理を扱う。Issue 処理を end-to-end で進めるときに使う。doc-system-v2 ノード著作には使わない（spec-pipeline / impl-design-pipeline を使う）。
---

## 共通本文

この資産の共通本文は [issue-pipeline の共通本文](../../../.ai/skills/issue-pipeline/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex CLI 固有の dispatch 契約

- GitHub の Issue/PR 操作は connector-first とし、利用可能な GitHub connector/tool を先に使い、不足する機能だけ `gh` CLI で補う。
- Codex implementer の `task_name` は exact `issue_<Issue番号>`、fixer は exact `issue_<Issue番号>_fix_r<round>` とする。task key は一度使ったら release 後も再利用しない。
- `spawn_agent` の前に専用 `.worktrees/<name>` を用意し、`python3 -m issue_start.codex_binding prepare --issue N --round R --repository OWNER/REPO --workspace ABS --branch BRANCH --expected-oid OID --handoff REL --role issue-implementer|issue-fixer --task-key KEY` を主文脈で成功させる。prepare は Issue・round・repository・workspace・branch・expected OID・handoff・role・task key を main worktree の ownership ledger へ期限付きで記録する。暗号化 message は binding に使わない。
- spawn の PreToolUse は binding を一度だけ consume し、全 tool PreToolUse は cwd/origin/branch と expected OID（または agent が作った descendant）を再検証する。別cwd・別origin・別branch・stale OID・未登録worktree・欠落handoff・期限切れ・task再利用は fail-close。hook 無効 harness や direct shell は保護済み経路として扱わない。
- agent 終了後は `python3 -m issue_start.codex_binding collect --task-key KEY --repo-root MAIN` で handoff を main worktree へ回収し、続けて `python3 -m issue_start.codex_binding release --task-key KEY --repo-root MAIN` で ownership を解放する。成功時は ledger の `released` と `collected_to` を確認し、失敗時は非終端 entry を消さず同じ task key で回収を再試行する。
- 実装担当は `.codex/agents/issue-implementer.toml`、是正担当は `.codex/agents/issue-fixer.toml`、レビュー担当は `.codex/agents/pr-reviewer.toml` の developer_instructions にある恒常契約を適用する。implementer/fixer は push 可・merge 不可、reviewer は自己修正/push 不可という hook 機械ゲートを維持する。
- この binding 機構を導入する bootstrap PR 自身に finding が出た場合、未導入の Codex fixerを worker・implementer・別roleへ偽装して迂回しない。bootstrap PR は独立 reviewer の finding を記録して STOP し、merge 後の main から正規 fixer transport を起動するか、オーナーが明示した bootstrap 処置だけを別記録で行う。
- 実装の model／effort は Bloom ルーブリック、初回レビューの effort は共通本文のリスク信号で選ぶ。再レビューは既定 `high`、レート制限を理由に降格しない。
