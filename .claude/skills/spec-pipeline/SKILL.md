---
name: spec-pipeline
description: Orchestrate the full spec-design pipeline in the main thread — align, I/O & event ledger, inspect, structured analysis, value trace, MVP scope. Run only when explicitly invoked.
disable-model-invocation: true
---

# 仕様設計パイプライン（オーケストレータ）

要件から MVP スコープまでを順に回す。**メインスレッドで実行**（サブエージェントはサブエージェントを呼べないため skill にする）。
原則：[spec-principles](../spec-principles/SKILL.md)。

## 手順（順に・各段でチェックポイント）
1. `/align` — 段取りと確定パラメータ。
2. `/io-event-ledger` — I/O 台帳＋イベントリスト＋カバレッジ。
3. **spec-inspector** サブエージェント — 点検（gap/矛盾）。矛盾は止めて確認。
4. **structured-analysis** サブエージェント — コンテキスト→DFD→単一責務→状態。
5. `/value-trace` — イベント総点検（遮断検出）。
6. `/mvp-scope` — 価値ベースの線引き。

各段の後に成果物を確認し、矛盾（PR7）が出たら停止して打ち上げる。必要なら spec-inspector を随時挟む。
