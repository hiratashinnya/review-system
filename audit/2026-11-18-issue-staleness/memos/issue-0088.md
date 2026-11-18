# Issue #88「scheduled のデフォルトを current_phase に（『空のみ許可』撤廃）— #85 レビュー派生」

- URL: https://github.com/hiratashinnya/review-system/issues/88
- 状態: closed（2026-11-18取得）
- 本文: 1008文字/ 21行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: #85
- PR参照: #85
- 主見出し: ## 背景 | ## 決定（オーナー承認） | ## やること | ## サブタスク（別判断・独断禁止） | ## 波及・注意
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- 現状は全著作資産が `scheduled` を**常に空文字**に固定し、**reconciliation-validator が SPEC の非空を ROLLBACK**（`reconciliation-validator.md:79`）・**spec-author が明示禁止**（`spec-author.md:85`）。これは「scheduled=いつ処置するかの計画」というオーナー意図と正面衝突（無計画がデフォルトになっている）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
