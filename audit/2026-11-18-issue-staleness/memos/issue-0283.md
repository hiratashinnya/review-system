# Issue #283「FND の深刻度語彙・本文必須項目・docs/doc-system の状態表現不一致を解消する(#263 アイテム2)」

- URL: https://github.com/hiratashinnya/review-system/issues/283
- 状態: open（2026-11-18取得）
- 本文: 3525文字/ 83行。全文: `../raw/issues-2026-07b.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #263, #261, #253, #256
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 1. 深刻度語彙の三者不一致 | ### 2. FND本文の必須項目検査RULE新設可否 | ### 3. docs/doc-system の4文書がFNDの状態表現・本文項目でv2に未追随 | ### 4. Q「深刻度判定基準の遡及適用」 | ## Scope | ## Out of scope | ## オーナー判断が必要な論点 | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - FND `fnd-深刻度の語彙が-05-verification.md・v2-テンプレート・実コーパスで三者不一致`（`doc-system-v2/nodes/04-verification/fnd/open/`・WARNING）
- - Q `深刻度の判定基準是正を既存-fnd-全件へ遡及適用するか`（`doc-system-v2/nodes/04-verification/q/open/`）
- 2026-07-26 のオーナー指示による深刻度判定基準の是正（機械検出可能性ではなく実害で判定）を、既著作の FND 131件（open 14・resolved 117）へ遡及適用するかの論点。
- - ③ 限定遡及（open FND 14件＋処置未完了resolvedのみ再判定）
- いずれも各FND/Q本文に詳細な実測・選択肢・根拠・推奨が記載済み（`doc-system-v2/nodes/04-verification/fnd/open/` および `q/open/` 配下）。処置要否・実施方針の最終決定はオーナーが行う（AI は「対応不要」の結論を出さない）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
