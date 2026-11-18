# Issue #426「worktree解放時にブランチのローカル参照が消し忘れられ、後続issue-fixerのadopt-branchが必ず詰まる（2回目の再現）」

- URL: https://github.com/hiratashinnya/review-system/issues/426
- 状態: closed（2026-11-18取得）
- 本文: 2917文字/ 55行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #423, #354, #425
- PR参照: #425
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 影響 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## Project fields（提案・要オーナー確認）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - `gitgate/adopt.py::adopt_branch`のstage 4は「ローカルに同名ブランチが存在しないこと」を前提条件としており、この前提が崩れると**stage 5（実際のcheckout）に到達せず、是正対象PRのファイルを一切取得できない**。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
