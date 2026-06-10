---
name: orchestration-design
description: Design the RUNTIME control flow — a swimlane flowchart (lanes = actors/layers), staged outcomes (a Result type) with fail-close paths, execution-order invariants, plus log-channel separation and version stamping. Use when turning a settled module architecture into an end-to-end execution design. This is control-flow design, NOT value-path inspection (use value-trace) and NOT logical DFD decomposition (use structured-analysis).
---

# オーケストレーション設計（制御フロー・fail-close・ログ/版）

> モジュール構成（architecture-design）を、**端から端の実行**として固める。誰が何の順で動き、失敗でどう倒れ、何を記録するか。
> 表現は**スイムレーン付フローチャート**（分岐/繰返し/失敗経路を見せる）。シーケンス図は使わない。
> 原則：[spec-principles](../spec-principles/SKILL.md)（PR6 価値経路を遮断しない／PR2 機構＝fail-close）。

## 参照
- 物理アーキテクチャ＝architecture-design（モジュール・ポート・IF）。
- 失敗の型（`Result`/`StageOutcome`）＝domain-model。
- 安定化策（fail-close・トランザクション・版スタンプ）＝要件（あれば S# 一覧）。

## 手順
1. **レーンを決める**：外部アクタ＋層（コア/外部サービス/永続）を `subgraph` レーンに。
2. **段を直列に並べる**：各段は `Result`（成功/失敗）を返す。**失敗は下流を走らせない**＝横断的に出口へ伝播（fail-close）。
3. **実行順序の不変条件**を明文化：検証→…→副作用 の順を**型で**強制（副作用段は上流成功時だけ走る＝半端を残さない）。
4. **良性 no-op** と **異常**を分ける：続けて無害なものは fail-open（空結果）、疑わしきは fail-close＋明示通知。
5. **ログ/版の章**を足す：チャネル分離（制御／診断／永続ログ）と**版スタンプ**（実行・入力・モデル・雛形・設定の版を串刺し）。**版は `MAJOR.MINOR`**（MAJOR＝構造/型→対応ロジック改修、MINOR＝内容のみ）。
6. **疑似コード**で段の直列と分岐（`match outcome`）を示し、副作用の到達条件を可視化。

## 判断基準
- **PR6**：どのイベントも入力→価値（出力）まで連続。失敗経路も「黙って空」にしない（明示通知）。
- **fail-close は横断経路**（特定プロセス内の正常フローでなく、全段に効く error 経路）。
- 外部（LLM 等）出力が**必ず検証段を通る**：制御フロー上、検証を飛ばす経路を作らない。
- ログ：制御チャネルを診断で汚さない（追従が壊れる）。版スタンプは再現性の証跡。

## 点検観点（done）
- 1枚のスイムレーンで端から端が追える。失敗経路が各段から出口へ繋がる。
- 副作用段が上流成功を前提にしている（型で担保）。
- 版スタンプの素材（実行/設定/モデル/雛形版）が揃い、同一入力×同一版で再現を説明できる。
- 段境界がログに出る（各段の開始/終了/失敗）。

## 成果物テンプレ
- スイムレーン flowchart（mermaid `subgraph` レーン）。
- 実行順序の不変条件リスト（番号付き）。
- `run_*()` 疑似コード（`match` で成功/失敗を漏れなく分岐）。
- ログ3チャネル表＋版スタンプ定義（`MAJOR.MINOR`・版↔対応ロジック対応）。

## doc-system ノード著作（ORC）
制御フローを起こすこの段で、**オーケストレーション段**ノードを著作する。共通手順・横断スパイン・RULE 全文・本文フォーマットは [07-authoring-guide.md](../../../docs/doc-system/07-authoring-guide.md)。スキーマ→[02-meta-schema.md](../../../docs/doc-system/02-meta-schema.md)、接続要否→[03-connection-matrix.md](../../../docs/doc-system/03-connection-matrix.md)。

| 型 | 必須辺 |
|---|---|
| ORC | → P (refines)、→ PROMPT (uses) 任意 |

> 辺方向に注意：`PROMPT → ORC` は誤り。正は **`ORC → PROMPT (uses)`**。
</content>
