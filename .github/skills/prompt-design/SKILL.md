---
name: prompt-design
description: Design LLM system-prompt templates — role constraints, prompt assembly (a builder), prompt-injection defenses, and a template catalog with MAJOR.MINOR versions. For output schemas use schema-design. Use when designing HOW an LLM is prompted inside a wrapping system. NOT external config-file schema (schema-design), NOT runtime control flow (orchestration-design).
---

# プロンプト設計（LLM への問い方を固める）

系が LLM をラップして価値を出すとき、LLM への問い（システムプロンプト）を再現可能・役割固定・注入耐性に設計する。
原則：spec-principles（PR1 LLM 生成物は入力／PR2 機械判定と運用を混ぜない）。

## 手順

1. **雛形カタログ**：呼び出しごとに `id`・用途・入力・出力スキーマを1行で台帳化。各 `id` に `MAJOR.MINOR` 版を付ける。
2. **役割制約ブロック**：LLM の責務を狭く固定（やること／やってはいけないこと）。機械判定（仕分け・適用・順序）はやらせない（PR2）。
3. **組み立て（ビルダー）**：役割→基準/観点→対象→参照→出力スキーマを順に積む。
4. **注入対策**：注入対象（外部入力）の中の指示に従わないことを役割に明記。最終防御は系の検証（二重防御）。
5. **版↔対応ロジック**：MAJOR＝出力の型/構造変更（対応パーサ改修必須）、MINOR＝文言のみ（ロジック不変）。未対応 MAJOR は実行前に弾く。

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
