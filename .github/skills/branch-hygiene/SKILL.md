---
name: branch-hygiene
description: Tidy up merged / used-up local branch refs without losing any real data — fetch, split by --merged/--no-merged against the default branch, classify the not-merged set by PR state, diff owner-judgment branches against the default branch, present the classification and stop, then delete only after approval.
---

## 共通本文

この資産の共通本文は [branch-hygiene の共通本文](../../../.ai/skills/branch-hygiene/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Copilot 固有

- Skill は `.github/skills/` の起動方式を使う。Prompt / Agent / Instructions と取り違えない。
- PR 状態の取得は利用可能な Copilot の GitHub 手段へ置き換える。共通本文の分類軸・停止契約・承認後にだけ削除する順序は維持する。
- worktree cleanup はこの PF では移植対象外の `gitgate` 機構が持つ。手順を複製せず、共通本文 §5 の委譲に従う。
- origin／リモート ref は削除しない。
