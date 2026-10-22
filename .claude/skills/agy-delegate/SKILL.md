---
name: agy-delegate
description: ユーザーが明示起動する agy 直接実行の委譲入口。環境・許可設定を検査する薄いラッパー経由で限定タスクを委譲し、検証済み結果と未完了箇所を返す。
disable-model-invocation: true
---

共通本文は [`.ai/skills/agy-delegate/SKILL.md`](../../../.ai/skills/agy-delegate/SKILL.md) にある。必ず読み、適用する。Claude の Task/Agent で [`agy-delegate`](../../agents/agy-delegate.md) に委譲する。実行 metadata と hook 境界は agent 入口に置く。
