# Issue #706「gitgate integrate-base を PR base 取り込みの責務に絞り、過剰なロール・保護ファイル・テスト制約を撤廃する」

- URL: https://github.com/hiratashinnya/review-system/issues/706
- 状態: closed（2026-11-18取得）
- 本文: 4895文字/ 78行。全文: `../raw/issues-2026-10.jsonl`
- AC: 9件（未チェック: 9）
- Issue参照: #594, #600, #629, #640, #704, #682
- PR参照: #600, #640, #682
- 主見出し: ## 目的 | ## 問題・根拠 | ## オーナー決定：採用する設計原則 | ### A. GitGate が担う範囲 | ### B. 撤廃する GitGate 本体の制約 | ### C. ロール権限・ワークフローとの責務分離 | ## 実装スコープ | ## Acceptance criteria | ## 非目標・要件追加の禁止 | ## Related
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- `gitgate integrate-base` / `integrate-base-continue` / `integrate-base-abort` を、**OPEN PR の base を当該 PR の head ブランチに取り込み、必要なコンフリクトを解消する**ための汎用的な操作として使えるようにする。
- 1. **実行者の過剰限定**：`gitgate/base_authority.py` は Claude の running dispatch / `issue-fixer`、または Copilot 固有の登録済み認可を前提とする。主文脈・`general-purpose` 等による、Issue-pipeline 外の正常な取り込みを阻害する。`agent-command-gate.sh` にも `issue-fixer` 限定の verb allowli
- - **OPEN PR の base→その PR の head ブランチ**の取り込み専用 verb を維持する。任意ブランチ間の汎用 merge verb にはしない。
- - **テスト成功を `integrate-base-continue` の前提としない。** 固定 unittest、`--test-module`、ゼロ件拒否等の強制を撤去する。必要なテスト・品質保証は呼び出し元ワークフロー／CI の責務。
- - [ ] OPEN PR の head checkout で、PR base を head に取り込める。正常、conflict 解消→確定、no-change、abort を実 Git で検証する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
