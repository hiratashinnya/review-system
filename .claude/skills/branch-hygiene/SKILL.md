---
name: branch-hygiene
description: マージ済み・用済みのローカルブランチ ref を実データを失わず整理する。fetch → --merged/--no-merged の二分 → not-merged 群を PR 状態（OPEN 維持／MERGED-squash 削除可／CLOSED・PR無しはオーナー判断）で分類 → 判断群は origin/main との diff で superseded 判定 → 分類表を提示して停止 → 承認後に -d／検証済み -D。origin ref は触らない。agent worktree の削除はしない（gitgate へ委譲）。Issue 運用は issue-pipeline。
---

## 共通本文

この資産の共通本文は [branch-hygiene の共通本文](../../../.ai/skills/branch-hygiene/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有

- repository の `CLAUDE.md` と、そこから参照される `.claude/rules/*.md` を先に読む。共通本文の実行前報告・独断禁止・PR7（意見なき停止の禁止）は Claude Code ではこれらの規範を指す。
- 分類表の提示と削除可否の確認には `AskUserQuestion` を使ってよい。ただし判断材料（分類表の全文・各オーナー判断ブランチの §2-3 実態と理由付き推奨）は**先にチャットへ日本語で全文**出す（ID・1行要約だけで投げない）。
- agent worktree（`.claude/worktrees/`）の後始末は `.claude/hooks/subagent-stop-gate.sh` と `python3 -m gitgate` が持つ。このスキルからは `git worktree remove` / `git worktree prune` を呼ばない（委譲先＝共通本文 §5・`.ai/troubleshooting/issue-pipeline.md`）。
- `git branch -D` は `.claude/hooks/agent-command-gate.sh` のロール別ゲートで gated ロール（issue-implementer / issue-fixer / pr-reviewer）には拒否される。このスキルは主文脈で実行する前提。
