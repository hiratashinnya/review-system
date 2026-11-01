---
name: agy-delegate
description: ユーザーが明示起動する agy 直接実行の委譲入口。環境・許可設定を検査する薄いラッパー経由で限定タスクを委譲し、検証済み結果と未完了箇所を返す。
---

共通本文は [`.ai/skills/agy-delegate/SKILL.md`](../../../.ai/skills/agy-delegate/SKILL.md) にある。必ず読み、適用する。Codex の spawn_agent で [`agy-delegate`](../../../.codex/agents/agy-delegate.toml) に委譲する。[silent-failure-diagnosis の共通本文](../../../.ai/skills/silent-failure-diagnosis/SKILL.md) も必読とする。Claude の metadata や hook を Codex に適用したと解釈しない。
