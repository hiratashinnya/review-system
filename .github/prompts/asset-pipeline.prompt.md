---
mode: 'agent'
description: 'Orchestrate the asset-ization pipeline (method -> skill/agent) in the main thread — inventory, asset-auditor reuse/conflict check, proposal (generic vs project-specific), phased build with checkpoints, verification gate. Run only when explicitly invoked.'
---

# 資産化パイプライン（オーケストレータ）

確立したメソッドをスキル/エージェント/規約に資産化する手順を順に回す。**メインスレッドで実行**
（サブエージェントはサブエージェントを呼べないため skill にする）。手法カードは A14。
原則：[spec-principles](../spec-principles/SKILL.md)。

## 手順（各フェーズでチェックポイント）
1. **棚卸し** — 対象活動をカード化。**ユーザーの指摘・質問・課題提起を重点的に拾う**。原則(PR)と活動(A)を分離。
2. **既存資産調査** — `asset-auditor` サブエージェントで**重複/矛盾/競合**を点検し、**新規 vs 既存変更**を判断。
3. **提案** — 振り分け（スキル/エージェント/共有リファレンス/規約）と、各資産の**汎用化前（固有）・汎用化後（抽象）の双方**を提示。
4. **形式適合確認** — ターゲット仕様を一次確認（憶測で作らない）。原則を制約へ翻訳（例：subagent は `AskUserQuestion` 不可→STOP 報告）。
5. **フェーズ毎の実体化** — 最小・最も再利用される単位から。各フェーズでチェックポイント。**台帳/プラン/規約を同期更新**。
6. **検証** — 要否と方法を必ず検討（登録確認・read-only確認・dry-run）。**実施はユーザー確認を求める**。

矛盾（PR7）が出たら停止して打ち上げる。
