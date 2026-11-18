# Issue #543「review_system側test-strategyに検査レベル（単体/結合/システム）のプレフィックスを導入する」

- URL: https://github.com/hiratashinnya/review-system/issues/543
- 状態: open（2026-11-18取得）
- 本文: 3358文字/ 60行。全文: `../raw/issues-2026-09.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #371, #540
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 採用する方式 | ## Scope | ## Out of scope | ## Acceptance criteria | ## 利用者価値 | ## 代替案 | ## Dependencies / Related issues | ## Project fields
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - #371 本文の書き直し（本 Issue はその前提部品の1つ）。
- - (b) 当面 harness 側だけの概念とし、review_system 側は現状維持。影響範囲（既存 `tests/unit/`・`tests/designs/`・`tests/reports/` 全体）が大きい本 Issue を避けられるが、両者で「TD/TC/TR」の意味範囲が食い違う状態が残る。**AI はこちらを推奨していたが、オーナーが (a) を選択した。**
- `Priority=P2` の根拠：#371 本文がまだ書き直されておらず、本 Issue は前提部品の1つに過ぎないため急を要さない。`Horizon=Later` はオーナー指定（着手時期未確定）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
