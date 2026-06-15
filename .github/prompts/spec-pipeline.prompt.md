---
description: 'Orchestrate the full spec-design pipeline: align → I/O ledger → spec-inspector → structured-analysis → value-trace → MVP scope. Run only when explicitly invoked.'
agent: agent
---

# 仕様設計パイプライン（オーケストレータ）

要件から MVP スコープまでを順に回す。

原則：spec-principles（PR7 矛盾は停止・PR10 認識合わせ先行）。

## 手順（順に・各段でチェックポイント）

1. `/align` — 段取りと確定パラメータ。
2. I/O 台帳＋イベントリスト＋カバレッジ。
3. **spec-inspector** エージェント — 点検（gap/矛盾）。矛盾は止めて確認。
4. **structured-analysis** エージェント — コンテキスト→DFD→単一責務→状態。
5. `/value-trace` — イベント総点検（遮断検出）。
6. `/mvp-scope` — 価値ベースの線引き。

各段の後に成果物を確認し、矛盾（PR7）が出たら停止して打ち上げる。必要なら spec-inspector を随時挟む。
