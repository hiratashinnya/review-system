---
name: branch-hygiene
description: マージ済み・用済みのローカルブランチ ref を実データを失わず整理する repo 運用スキル。fetch → --merged/--no-merged の二分 → not-merged 群を PR 状態で分類 → CLOSED・PR無しは origin/main との diff で実態を出す → 分類表を提示して STOP → 承認後に -d／検証済み -D。origin ref は触らない。agent worktree の削除には使わない（gitgate へ委譲）。Issue の end-to-end 運用には使わない（issue-pipeline）。
---

## 共通本文

この資産の共通本文は [branch-hygiene の共通本文](../../../.ai/skills/branch-hygiene/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex CLI 固有

- GitHub の PR 状態取得は connector-first とし、利用可能な GitHub connector/tool を先に使い、不足する機能だけ `gh` CLI で補う。
- 非対話（AskUserQuestion 相当を持たない）。共通本文 §3 の分類表提示・削除可否の確認は**呼び出し元へ STOP 報告**として返し、削除は承認を受けた呼び出し元が実行する。曖昧・矛盾・オーナー判断群の可否は自分で結論づけない。
- worktree 実体の削除経路は Codex 側でも `gitgate` に一元化されている。このスキルから `git worktree remove` / `git worktree prune` を呼ばない（委譲先＝共通本文 §5）。
