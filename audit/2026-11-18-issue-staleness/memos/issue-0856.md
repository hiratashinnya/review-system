# Issue #856「improvement(review): Issue-pipeline 1a/1bのPlanReview観点を実例監査し、根拠・工程責務・収束性を改善する」

- URL: https://github.com/hiratashinnya/review-system/issues/856
- 状態: open（2026-11-18取得）
- 本文: 3228文字/ 45行。全文: `../raw/issues-2026-11.jsonl`
- AC: 7件（未チェック: 6）
- Issue参照: #691, #784, #832, #830, #655, #662, #694, #783, #785, #801, #371, #723, #370
- PR参照: なし
- 主見出し: ## 目的・利用者価値 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## 対象 harness | ## Project / metadata
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - `.ai/skills/review-harm/SKILL.md` は harm を real/none とし、迷った場合に real 側へ倒す。#830 で到達経路・前提脅威の記載が追加されたが、評価/棄却候補の独立判定は #832（未完了）。
- 1. #655 を含む複数の 1a/1b 実レビューを、review artifact/Karte/issue・PR コメント/差分・決定記録が確認できる範囲で監査する。各 finding の元の基準、証拠、到達経路、前提脅威、当時の入力・承認、是正、再指摘を対照する。証拠欠落は欠落として記録する。
- - Related: #371「作成工程の分離」（完了）、#723「実害判定基準のSSoT化」（完了）、#830「到達経路・前提脅威の根拠欄」（完了）、#832「triagerの独立根拠評価」、#691「レビュー指摘自動仕分け」、#784「トリアージ工程結線」、#370「merge後欠陥混入率の観測」

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
