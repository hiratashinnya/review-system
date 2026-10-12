---
name: silent-failure-diagnosis
description: 外部プロセス（委譲先の CLI・エージェント、フック、CI、外部サービス）が終了コード 0・status SUCCESS 等の成功シグナルを返しながら、誤答・古い結果・空応答・途中打ち切り・隠れた権限拒否になっている疑いを切り分ける共有リファレンス。正しい拒否の確認、入力を読んだかのアンカー照合、副チャネルの検査、再現、版の同一性、ログの時系列、本番経路の特定、最小権限を扱う。委譲系の agent/skill が参照する共有リファレンスだが、現時点で参照する資産は無い（最初の利用者 agy-delegate は Issue 606 で接続予定）。仕様点検（spec-inspector）・資産監査（asset-auditor）・テスト設計（test-strategy）・特定の委譲先の固有手順（agy-delegate／codex-review）ではない。
---

この Skill の共通本文は [`.ai/skills/silent-failure-diagnosis/SKILL.md`](../../../.ai/skills/silent-failure-diagnosis/SKILL.md) にあります。作業時は必ず共通本文を読み、その内容を適用してください。
