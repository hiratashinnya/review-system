# Issue #723「refactor(harness): 実害判定基準をSSoT化しレビューア・finding-triagerへ同一基準を供給する」

- URL: https://github.com/hiratashinnya/review-system/issues/723
- 状態: closed（2026-11-18取得）
- 本文: 3682文字/ 53行。全文: `../raw/issues-2026-11.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #691, #369, #511, #375, #523, #513, #614, #562
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状・根拠 | ## 提案方針 / Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
-    - `harm: real` の類型：正しさ、退行、fail-close/権限境界、正本・履歴の破損、契約違反、秘密・コスト、誤読、名称と実体の不一致、トレーサビリティ断絶、正本の分岐、暗黙の前提、観測不能、再現性の欠如。
- - **#691（open）**：自動仕分け・`finding-triager` 導入の tracking。本Issueはその**判定基準の共通化と配布契約**のみを担当し、triager実装は #691 の分割成果と重複させない。triager実装時には本IssueのSSoTを必須参照。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
