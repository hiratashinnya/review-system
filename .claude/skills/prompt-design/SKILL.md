---
name: prompt-design
description: Design LLM system-prompt templates — role constraints, prompt assembly (a builder), prompt-injection defenses, and a template catalog with MAJOR.MINOR versions. For output schemas use schema-design; for version stamps see test-strategy / logging design. Use when designing HOW an LLM is prompted inside a wrapping system. NOT external config-file schema (schema-design), NOT runtime control flow (orchestration-design).
---

# プロンプト設計（LLM への問い方を固める）

> 系が LLM を**ラップして価値を出す**とき、LLM への問い（システムプロンプト）を**再現可能・役割固定・注入耐性**に設計する。
> 責務分離：**出力スキーマの形は schema-design**、**版スタンプは test-strategy/ロギング設計**へ委譲（二重定義しない）。
> 原則：[spec-principles](../spec-principles/SKILL.md)（PR1 LLM 生成物は入力／PR2 機械判定と運用を混ぜない）。

## 参照
- LLM 呼び出し箇所の一覧（どの判断を委譲するか）＝要件の境界設計。
- 出力スキーマの形式＝schema-design（本スキルは「どこで提示するか」だけ扱う）。
- 版スタンプ・ログ＝orchestration-design / test-strategy。

## 手順
1. **雛形カタログ**：呼び出しごとに `id`・用途・入力・出力スキーマ を1行で台帳化。各 `id` に **`MAJOR.MINOR` 版**を付ける。
2. **役割制約ブロック**：LLM の責務を**狭く固定**（やること／やってはいけないこと）。機械判定（仕分け・適用・順序）は**やらせない**＝系の決定的処理に残す（PR2）。
3. **組み立て（ビルダー）**：役割→基準/観点→対象→参照→出力スキーマ を**順に積む**。順次構造＝ビルダー向き。
4. **注入対策**：注入対象（外部入力）の中の指示に**従わない**ことを役割に明記。ただし**最終防御は系の検証**（プロンプトの言い分に依存しない二重防御）。
5. **版↔対応ロジック**：MAJOR＝出力の型/構造変更（対応パーサ/ビルダー改修必須）、MINOR＝文言のみ（ロジック不変）。**未対応 MAJOR は実行前に弾く**。

## 判断基準
- **PR1**：raw LLM 出力＝入力。系が検証/整形して初めて出力。素通しは価値が無い。
- **役割は狭く**：1雛形＝1責務。メタ（順序ある属性）は LLM に渡さない・判断させない。
- **二重防御**：参照除外・id 検証・スキーマ検証は**系**が機械実行。プロンプトはあくまで一次ガード。
- 出力スキーマの**設計**は schema-design、ここでは**提示位置と版**だけ。

## 点検観点（done）
- 雛形カタログが版付きで揃い、版↔対応ロジックが一目で分かる。
- 役割制約が「やってはいけない（仕分け/適用/メタ判断）」を含む。
- 注入対策が役割に入り、かつ系側の検証で最終担保されている。
- 出力が必ず系の検証段へ流れる（プロンプトだけで完結しない）。

## 成果物テンプレ
- 雛形カタログ表（id・版・用途・入出力）。
- 役割制約ブロック（やること/やってはいけないこと）。
- ビルダーの段（`with_*`）と最終 frozen プロンプト。
- 版管理表（MAJOR.MINOR ↔ 対応ハンドラ）。

## doc-system ノード著作（PROMPT）
プロンプト雛形を起こすこの段で、**プロンプトテンプレート**ノードを著作する。共通手順・横断スパイン・RULE 全文・本文フォーマットは [07-authoring-guide.md](../../../docs/doc-system/07-authoring-guide.md)。スキーマ→[02-meta-schema.md](../../../docs/doc-system/02-meta-schema.md)、接続要否→[03-connection-matrix.md](../../../docs/doc-system/03-connection-matrix.md)。

| 型 | 必須辺 | 備考 |
|---|---|---|
| PROMPT | → SPEC (refines) | 版は本文/カタログで `MAJOR.MINOR` 管理。ORC からは `ORC → PROMPT (uses)` で参照される |
</content>
