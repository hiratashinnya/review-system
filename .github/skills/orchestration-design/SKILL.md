---
name: orchestration-design
description: Design the RUNTIME control flow — a swimlane flowchart (lanes = actors/layers), staged outcomes (a Result type) with fail-close paths, execution-order invariants, plus log-channel separation and version stamping. Use when turning a settled module architecture into an end-to-end execution design. NOT value-path inspection (use value-trace), NOT logical DFD decomposition (use structured-analysis).
---

# オーケストレーション設計（制御フロー・fail-close・ログ/版）

モジュール構成（architecture-design）を、端から端の実行として固める。
表現はスイムレーン付フローチャート（分岐/繰返し/失敗経路を見せる）。
原則：spec-principles（PR6 価値経路を遮断しない／PR2 機構＝fail-close）。

## 手順

1. **レーンを決める**：外部アクタ＋層（コア/外部サービス/永続）をレーンに。
2. **段を直列に並べる**：各段は `Result`（成功/失敗）を返す。失敗は下流を走らせない＝fail-close。
3. **実行順序の不変条件**を明文化：検証→…→副作用 の順を型で強制。
4. **良性 no-op と異常を分ける**：続けて無害なものは fail-open（空結果）、疑わしきは fail-close＋明示通知。
5. **ログ/版の章**：チャネル分離（制御／診断／永続ログ）と版スタンプ（実行・入力・モデル・雛形・設定の版）。版は `MAJOR.MINOR`（MAJOR＝構造/型→ロジック改修、MINOR＝内容のみ）。
6. **疑似コード**で段の直列と分岐（`match outcome`）を示し、副作用の到達条件を可視化。

## 点検観点（done）

- 1枚のスイムレーンで端から端が追える。失敗経路が各段から出口へ繋がる。
- 副作用段が上流成功を前提にしている（型で担保）。
- 版スタンプの素材（実行/設定/モデル/雛形版）が揃い、同一入力×同一版で再現を説明できる。

## 成果物テンプレ

- スイムレーン flowchart（mermaid `subgraph` レーン）。
- 実行順序の不変条件リスト（番号付き）。
- `run_*()` 疑似コード（`match` で成功/失敗を漏れなく分岐）。
- ログ3チャネル表＋版スタンプ定義。
