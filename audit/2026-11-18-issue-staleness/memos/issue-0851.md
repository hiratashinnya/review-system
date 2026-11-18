# Issue #851「issue-pipeline の層表と bloom-model-tier の閾値表・各 agent の frontmatter が食い違い、Codex 切替規範の下限を測る基準が定まらない」

- URL: https://github.com/hiratashinnya/review-system/issues/851
- 状態: open（2026-11-18取得）
- 本文: 3416文字/ 69行。全文: `../raw/issues-2026-11.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #847, #829, #626, #801, #321
- PR参照: #847
- 主見出し: ## 目的・背景 | ## 対象 harness | ## 現状と根拠 | ## 利用者価値・選択肢・互換性 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - issue-fixer の層は frontmatter と `.ai/rationale/issue-fixer.md`（「閾値表より sonnet + effort: high」）から転記された。現在の閾値表は Lv4 を中位＋大とする。
- - Parent／blocked-by／blocking：なし。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
